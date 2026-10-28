from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Any

if __package__:
    from .validate import validate, validate_source_readback
    from .verify_sources import current_input_paths, verify
else:
    from validate import validate, validate_source_readback
    from verify_sources import current_input_paths, verify


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = Path(__file__).resolve().parent
APALACHE_SHA256 = "91125e5a3646b9c9d3a7d921d3323f321fac5071909f72b3960c66ff2f998ee1"


@dataclass(frozen=True)
class Query:
    name: str
    model: Path
    harness: Path
    module: str
    flags: tuple[str, ...]


@dataclass(frozen=True)
class PortSelection:
    status: str
    endpoint: str | None
    diagnostic: str | None = None


QUERIES = (
    Query(
        "bounded",
        ROOT / "specs/operation.qnt",
        ROOT / "specs/operation.qnt",
        "OperationProtocol",
        ("--invariant=safety", "--max-steps=12"),
    ),
    Query(
        "canary",
        ROOT / "specs/canary.qnt",
        ROOT / "specs/canary.qnt",
        "UnsafeCanary",
        ("--invariant=unauthorizedEffectIsImpossible", "--max-steps=2"),
    ),
    Query(
        "terminal",
        SCRIPT_ROOT / "models/reachability.qnt",
        SCRIPT_ROOT / "models/reachability.qnt",
        "P3Reachability",
        ("--invariant=terminalUnreachable", "--max-steps=12"),
    ),
    Query(
        "reconciliation",
        SCRIPT_ROOT / "models/reachability.qnt",
        SCRIPT_ROOT / "models/reachability.qnt",
        "P3Reachability",
        ("--invariant=reconciliationUnreachable", "--max-steps=12"),
    ),
    Query(
        "typed-inductive",
        SCRIPT_ROOT / "models/induction.qnt",
        SCRIPT_ROOT / "models/induction.qnt",
        "P3Induction",
        ("--inductive-invariant=IndInv", "--invariant=safety"),
    ),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_files(toolchain: Path) -> tuple[Path, ...]:
    return current_input_paths(ROOT) + (
        toolchain / "node_modules/@informalsystems/quint/package.json",
        toolchain / "apalache-0.56.1.tgz",
    )


def input_digests(paths: tuple[Path, ...]) -> dict[str, str]:
    return {str(path): digest(path) for path in paths}


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def select_server_endpoint(host: str = "127.0.0.1") -> PortSelection:
    probe: socket.socket | None = None
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind((host, 0))
        port = probe.getsockname()[1]
    except OSError as exc:
        return PortSelection(
            status="NOT_AVAILABLE",
            endpoint=None,
            diagnostic=f"{exc.__class__.__name__}: {exc}",
        )
    finally:
        if probe is not None:
            probe.close()
    return PortSelection(status="AVAILABLE", endpoint=f"{host}:{port}")


def run_command(
    name: str,
    command: list[str],
    cwd: Path,
    evidence: Path,
    inputs: tuple[Path, ...],
    env: dict[str, str],
    input_roles: dict[str, tuple[Path, ...]],
    input_manifest: dict[str, str],
) -> None:
    run_dir = evidence / "runs" / name
    artifact_dir = evidence / "artifacts" / name
    run_dir.mkdir(parents=True, exist_ok=False)
    artifact_dir.mkdir(parents=True, exist_ok=False)
    before = input_digests(inputs)
    command_record = {
        "argv": command,
        "cwd": str(cwd),
        "timeout_seconds": 180,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "input_digests_before": before,
        "input_manifest": input_manifest,
        "input_digests_by_role": {role: input_digests(paths) for role, paths in input_roles.items()},
        "scope": "P3 independent Lab only; no Soodles Native execution",
    }
    write_json(run_dir / "command.json", command_record)
    started = time.monotonic()
    timed_out = False
    process_error: str | None = None
    exit_code = 127
    with (run_dir / "stdout.txt").open("wb") as stdout, (run_dir / "stderr.txt").open("wb") as stderr:
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            try:
                exit_code = process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    exit_code = process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    exit_code = process.wait()
        except OSError as exc:
            process_error = str(exc)
            stderr.write(process_error.encode("utf-8"))
    after = input_digests(inputs)
    result = {
        **command_record,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "process_error": process_error,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "input_digests_after": after,
        "inputs_unchanged": before == after,
        "inputs_match_manifest_before": before == input_manifest,
        "inputs_match_manifest_after": after == input_manifest,
    }
    write_json(run_dir / "result.json", result)


def toolchain_check(toolchain: Path) -> None:
    package = json.loads((toolchain / "node_modules/@informalsystems/quint/package.json").read_text(encoding="utf-8"))
    if package.get("version") != "0.32.0":
        raise ValueError(f"unexpected Quint version: {package.get('version')}")
    archive = toolchain / "apalache-0.56.1.tgz"
    if digest(archive) != APALACHE_SHA256:
        raise ValueError("Apalache release digest mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--toolchain", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--tag", default="p3")
    args = parser.parse_args()
    toolchain = args.toolchain.resolve()
    evidence = (args.evidence_dir / args.tag).resolve()
    if evidence.exists():
        raise SystemExit(f"evidence directory already exists: {evidence}")
    toolchain_check(toolchain)
    evidence.mkdir(parents=True)
    inputs = input_files(toolchain)
    input_manifest = input_digests(inputs)
    manifest_record = {
        "schema": "fvl.p3-input-manifest.v1",
        "digests": input_manifest,
        "source_inputs": [str(path) for path in current_input_paths(ROOT)],
    }
    write_json(evidence / "input-manifest.json", manifest_record)
    source_result = verify(ROOT)
    write_json(evidence / "source-readback.json", source_result)
    try:
        validate_source_readback(source_result, manifest_record)
    except ValueError as exc:
        raise SystemExit(f"source verification failed: {exc}") from exc
    quint = str(toolchain / "node_modules/.bin/quint")
    env = {**os.environ, "QUINT_HOME": str(toolchain / "quint-home")}
    typechecks = (("safe", ROOT / "specs/operation.qnt"), ("canary", ROOT / "specs/canary.qnt"))
    for name, spec in typechecks:
        run_command(
            f"typecheck-{name}",
            [quint, "typecheck", str(spec)],
            evidence / "artifacts" / f"typecheck-{name}",
            evidence,
            inputs,
            env,
            {
                "model": (spec,),
                "runner": (SCRIPT_ROOT / "run.py",),
                "validator": (SCRIPT_ROOT / "validate.py",),
            },
            input_manifest,
        )
    for query in QUERIES:
        port = select_server_endpoint()
        if port.endpoint is None:
            input_digests_at_refusal = input_digests(inputs)
            write_json(
                evidence / "checker-capability.json",
                {
                    "schema": "fvl.p3-capability.v1",
                    "status": "NOT_RUN",
                    "reason": "LOCAL_PORT_UNAVAILABLE",
                    "diagnostic": port.diagnostic,
                    "server_endpoint": None,
                    "fixed_port_fallback": False,
                    "query": query.name,
                    "model": str(query.model),
                    "harness": str(query.harness),
                    "runner": str(SCRIPT_ROOT / "run.py"),
                    "validator": str(SCRIPT_ROOT / "validate.py"),
                    "input_digests": input_manifest,
                    "input_digests_at_refusal": input_digests_at_refusal,
                    "inputs_match_manifest": input_digests_at_refusal == input_manifest,
                    "input_digests_by_role": {
                        "model": input_digests((query.model,)),
                        "harness": input_digests((query.harness,)),
                        "runner": input_digests((SCRIPT_ROOT / "run.py",)),
                        "validator": input_digests((SCRIPT_ROOT / "validate.py",)),
                    },
                },
            )
            print(
                json.dumps(
                    {"status": "NOT_RUN", "reason": "LOCAL_PORT_UNAVAILABLE", "evidence": str(evidence)},
                    indent=2,
                )
            )
            return 2
        artifact_dir = evidence / "artifacts" / query.name
        command = [
            "env",
            f"QUINT_HOME={toolchain / 'quint-home'}",
            quint,
            "verify",
            str(query.model),
            f"--main={query.module}",
            "--backend=apalache",
            "--apalache-version=0.56.1",
            f"--server-endpoint={port.endpoint}",
            "--verbosity=3",
            "--out=quint-result.json",
            "--out-itf=trace.itf.json",
            *query.flags,
        ]
        run_command(
            query.name,
            command,
            artifact_dir,
            evidence,
            inputs,
            env,
            {
                "model": (query.model,),
                "harness": (query.harness,),
                "runner": (SCRIPT_ROOT / "run.py",),
                "validator": (SCRIPT_ROOT / "validate.py",),
            },
            input_manifest,
        )
    try:
        result = validate(evidence)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        write_json(evidence / "evidence-validation.json", {"status": "NOT_VERIFIED", "error": str(exc)})
        print(json.dumps({"status": "NOT_VERIFIED", "evidence": str(evidence), "error": str(exc)}, indent=2))
        return 1
    write_json(evidence / "evidence-validation.json", result)
    print(json.dumps({"status": "VERIFIED", "evidence": str(evidence), "result": result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
