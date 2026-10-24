from __future__ import annotations

import argparse
import datetime as dt
import hashlib
from importlib import metadata
import itertools
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
from typing import Any, Callable, Iterable


ROOT = Path(__file__).resolve().parent.parent
INPUTS = (
    ROOT / "src/formal_verification_lab/contracts.py",
    ROOT / "src/formal_verification_lab/formal_contracts.py",
    ROOT / "tests/test_properties.py",
    ROOT / "scripts/p4.py",
    ROOT / "scripts/p4_canary.py",
    ROOT / "requirements-verification.lock.txt",
    ROOT / "verification-downloads.json",
)


class P4Error(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_digests() -> dict[str, str]:
    missing = [str(path) for path in INPUTS if not path.is_file() or path.is_symlink()]
    if missing:
        raise P4Error(f"missing or linked P4 input: {missing}")
    return {str(path): sha256(path) for path in INPUTS}


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def locked_packages() -> dict[str, str]:
    packages: dict[str, str] = {}
    for line in (ROOT / "requirements-verification.lock.txt").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        name, separator, version = line.partition("==")
        if not separator or not name or not version:
            raise P4Error(f"invalid pinned requirement: {line}")
        packages[name] = version
    return packages


def package_versions() -> dict[str, Any]:
    expected = locked_packages()
    observed: dict[str, str] = {}
    missing: list[str] = []
    mismatches: list[str] = []
    for name, version in expected.items():
        try:
            actual = metadata.version(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
            continue
        observed[name] = actual
        if actual != version:
            mismatches.append(f"{name}: expected {version}, observed {actual}")
    return {
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "expected": expected,
        "observed": observed,
        "missing": missing,
        "mismatches": mismatches,
    }


def observe(
    function: Callable[..., bool], cases: Iterable[tuple[object, ...]], accepted: tuple[object, ...]
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    results: list[dict[str, Any]] = []
    failure: dict[str, Any] | None = None
    for arguments in cases:
        expected = arguments == accepted
        actual = function(*arguments)
        result = {"input": arguments, "expected": expected, "actual": actual}
        results.append(result)
        if actual is not expected and failure is None:
            failure = result
    return results, failure


def literal_controls() -> dict[str, Any]:
    from formal_verification_lab.contracts import eligible_effect, receipt_supported

    effect_cases = list(itertools.product([False, True], repeat=5))
    receipt_cases = list(itertools.product([-2, -1, 0, 1, 2, 10], [False, True], [False, True]))
    effects, effect_failure = observe(
        eligible_effect, effect_cases, (True, True, True, True, False)
    )
    receipts, receipt_failure = observe(
        receipt_supported, receipt_cases, (1, True, True)
    )
    _, false_canary = observe(
        lambda *arguments: False, effect_cases, (True, True, True, True, False)
    )
    expected_canary = {
        "input": (True, True, True, True, False),
        "expected": True,
        "actual": False,
    }
    if effect_failure is not None:
        raise P4Error(f"effect literal oracle mismatch: {effect_failure}")
    if receipt_failure is not None:
        raise P4Error(f"receipt literal oracle mismatch: {receipt_failure}")
    if false_canary != expected_canary:
        raise P4Error(f"always-False canary did not expose vacuity: {false_canary}")
    if len(effects) != 32 or len(receipts) != 24:
        raise P4Error(f"literal case count mismatch: effects={len(effects)} receipts={len(receipts)}")
    return {
        "effect_cases": effects,
        "receipt_cases": receipts,
        "always_false_canary_counterexample": false_canary,
        "scope": "pure predicates and fixed literal oracle only; no authorization authenticity",
    }


def run_command(
    name: str,
    command: list[str],
    timeout_seconds: int,
    evidence: Path,
    inputs: dict[str, str],
    env: dict[str, str],
) -> dict[str, Any]:
    run_dir = evidence / "runs" / name
    run_dir.mkdir(parents=True, exist_ok=False)
    command_record = {
        "argv": command,
        "cwd": str(ROOT),
        "timeout_seconds": timeout_seconds,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "input_digests_before": input_digests(),
        "limits": {
            "crosshair_per_condition_seconds": 10,
            "crosshair_per_path_seconds": 5,
            "hypothesis_seed": "20261024",
        },
        "scope": "P4 pure Lab contracts only; no Soodles Native execution",
    }
    if command_record["input_digests_before"] != inputs:
        raise P4Error(f"inputs changed before run: {name}")
    write_json(run_dir / "command.json", command_record)
    started = time.monotonic()
    timed_out = False
    process_error: str | None = None
    exit_code: int | None = None
    with (run_dir / "stdout.txt").open("wb") as stdout, (run_dir / "stderr.txt").open("wb") as stderr:
        try:
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=env,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            try:
                exit_code = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    exit_code = process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    exit_code = process.wait()
        except OSError as exc:
            process_error = f"{exc.__class__.__name__}: {exc}"
            stderr.write(process_error.encode("utf-8"))
    after = input_digests()
    result = {
        **command_record,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "process_error": process_error,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "input_digests_after": after,
        "inputs_unchanged": after == inputs,
    }
    write_json(run_dir / "result.json", result)
    return result


def output(evidence: Path, name: str) -> str:
    return "\n".join(
        (evidence / "runs" / name / filename).read_text(encoding="utf-8", errors="replace")
        for filename in ("stdout.txt", "stderr.txt")
    )


def require_process(result: dict[str, Any], expected_exit: int, name: str) -> None:
    if result.get("exit_code") != expected_exit:
        raise P4Error(f"unexpected exit for {name}: {result.get('exit_code')}")
    if result.get("timed_out") or result.get("process_error"):
        raise P4Error(f"process did not complete normally: {name}")
    if not result.get("inputs_unchanged"):
        raise P4Error(f"inputs changed during run: {name}")


def validate_results(evidence: Path, results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    require_process(results["crosshair"], 0, "crosshair")
    crosshair_output = output(evidence, "crosshair")
    if crosshair_output.count("Confirmed over all paths.") != 2:
        raise P4Error("CrossHair did not confirm exactly two conditions")

    require_process(results["canary"], 1, "canary")
    canary_output = output(evidence, "canary")
    for expected in (
        "postcondition return False",
        "unchecked_effect(False) (which returns True)",
    ):
        if expected not in canary_output:
            raise P4Error(f"unsafe canary diagnostic is missing: {expected}")

    require_process(results["hypothesis"], 0, "hypothesis")
    hypothesis_output = output(evidence, "hypothesis")
    if re.search(r"\b2 passed\b", hypothesis_output) is None:
        raise P4Error("Hypothesis sampling did not report exactly two passing properties")
    if any(word in hypothesis_output.lower() for word in ("skipped", "xfailed", "xpassed")):
        raise P4Error("Hypothesis sampling contains a hidden non-pass result")

    require_process(results["controls"], 0, "controls")
    controls = json.loads((evidence / "runs/controls/stdout.txt").read_text(encoding="utf-8"))
    if len(controls.get("effect_cases", [])) != 32 or len(controls.get("receipt_cases", [])) != 24:
        raise P4Error("literal control output has the wrong case count")
    expected_canary = {
        "input": [True, True, True, True, False],
        "expected": True,
        "actual": False,
    }
    if controls.get("always_false_canary_counterexample") != expected_canary:
        raise P4Error("literal always-False canary counterexample is missing")

    return {
        "schema": "fvl.p4-evidence.v1",
        "status": "BOUNDED_PASS",
        "crosshair": {"confirmed_conditions": 2, "per_condition_seconds": 10, "per_path_seconds": 5},
        "unsafe_canary": {"status": "COUNTEREXAMPLE", "call": "unchecked_effect(False)", "returned": True},
        "hypothesis": {"status": "PASS", "properties": 2, "seed": "20261024"},
        "literal_controls": {"effect_cases": 32, "receipt_cases": 24, "always_false_canary": "COUNTEREXAMPLE"},
        "limits": [
            "pure necessary-condition predicates only",
            "no authorization authenticity or complete provider ledger claim",
            "no Native Soodles refinement or production acceptance",
        ],
    }


def run(evidence: Path) -> int:
    evidence = evidence.resolve()
    try:
        evidence.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise P4Error("evidence directory must be outside the repository")
    if evidence.exists():
        raise P4Error(f"evidence directory already exists: {evidence}")
    evidence.mkdir(parents=True)
    inputs = input_digests()
    write_json(evidence / "input-manifest.json", {"schema": "fvl.p4-inputs.v1", "digests": inputs})
    versions = package_versions()
    write_json(evidence / "versions.json", versions)
    if versions["missing"] or versions["mismatches"]:
        summary = {
            "schema": "fvl.p4-evidence.v1",
            "status": "NOT_RUN",
            "reason": "PINNED_ENVIRONMENT_UNAVAILABLE",
            "missing": versions["missing"],
            "mismatches": versions["mismatches"],
        }
        write_json(evidence / "summary.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 2

    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "HYPOTHESIS_STORAGE_DIRECTORY": str(evidence / "hypothesis"),
    }
    results = {
        "crosshair": run_command(
            "crosshair",
            [
                sys.executable,
                "-m",
                "crosshair",
                "check",
                str(ROOT / "src/formal_verification_lab/formal_contracts.py"),
                "--analysis_kind=icontract",
                "--report_all",
                "--per_condition_timeout=10",
                "--per_path_timeout=5",
            ],
            90,
            evidence,
            inputs,
            env,
        ),
        "canary": run_command(
            "canary",
            [
                sys.executable,
                "-m",
                "crosshair",
                "check",
                str(ROOT / "scripts/p4_canary.py"),
                "--analysis_kind=icontract",
                "--report_all",
                "--report_verbose",
                "--per_condition_timeout=10",
            ],
            60,
            evidence,
            inputs,
            env,
        ),
        "hypothesis": run_command(
            "hypothesis",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "--hypothesis-seed=20261024",
                "tests/test_properties.py",
            ],
            90,
            evidence,
            inputs,
            env,
        ),
        "controls": run_command(
            "controls",
            [sys.executable, str(ROOT / "scripts/p4.py"), "--controls-only"],
            30,
            evidence,
            inputs,
            env,
        ),
    }
    summary = validate_results(evidence, results)
    write_json(evidence / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--controls-only", action="store_true")
    args = parser.parse_args()
    if args.controls_only:
        if args.evidence_dir is not None:
            parser.error("--controls-only does not accept --evidence-dir")
        try:
            controls = literal_controls()
        except (OSError, P4Error) as exc:
            print(json.dumps({"status": "NOT_VERIFIED", "error": str(exc)}, indent=2))
            return 1
        print(json.dumps(controls, indent=2))
        return 0
    if args.evidence_dir is None:
        parser.error("--evidence-dir is required")
    try:
        return run(args.evidence_dir)
    except (OSError, P4Error, json.JSONDecodeError) as exc:
        error = {"schema": "fvl.p4-evidence.v1", "status": "NOT_VERIFIED", "error": str(exc)}
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
