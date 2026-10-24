from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing receipt: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"receipt is not an object: {path}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_input_manifests(root: Path) -> None:
    manifest = read_json(root / "input-manifest.json")
    expected = manifest.get("digests")
    require(manifest.get("schema") == "fvl.p3-input-manifest.v1", "input manifest schema is invalid")
    require(isinstance(expected, dict), "input manifest digests are invalid")
    for result_path in sorted((root / "runs").glob("*/result.json")):
        result = read_json(result_path)
        require(
            result.get("input_digests_before") == expected,
            f"input manifest mismatch before execution: {result_path}",
        )
        require(
            result.get("input_digests_after") == expected,
            f"input manifest mismatch after execution: {result_path}",
        )


def validate_source_readback(source: dict[str, Any], manifest: dict[str, Any]) -> None:
    require(
        source.get("schema") == "fvl.current-source-readback.v2",
        "source readback schema is invalid",
    )
    require(source.get("mismatches") == [], "current source readback has mismatches")
    provenance = source.get("historical_provenance")
    require(isinstance(provenance, dict), "historical provenance record is missing")
    require(
        provenance.get("status") == "HISTORICAL_NOT_REVERIFIED",
        "historical provenance status is invalid",
    )
    require(provenance.get("manifest_files") == 188, "historical source manifest count changed")
    require(
        source.get("duplicate_absence")
        == ["scripts/p3/models/canary.qnt", "scripts/p3/models/operation.qnt"],
        "duplicate model absence is not verified",
    )
    require(
        source.get("repository_imports")
        == {
            "scripts/p3/models/induction.qnt": "specs/operation.qnt",
            "scripts/p3/models/reachability.qnt": "specs/operation.qnt",
        },
        "repository model imports are not verified",
    )
    expected = manifest.get("digests")
    source_paths = manifest.get("source_inputs")
    observed = source.get("current_inputs")
    require(isinstance(expected, dict), "input manifest digests are invalid")
    require(
        isinstance(source_paths, list) and all(isinstance(path, str) for path in source_paths),
        "source input list is invalid",
    )
    require(isinstance(observed, dict), "current source digests are invalid")
    require(
        set(observed) == set(source_paths),
        "current source input set differs from invocation manifest",
    )
    for path in source_paths:
        require(
            observed.get(path) == expected.get(path),
            f"current source digest differs from invocation manifest: {path}",
        )


def validate_run(root: Path, name: str, exit_code: int, status: str) -> tuple[dict[str, Any], str]:
    run = read_json(root / "runs" / name / "result.json")
    result = read_json(root / "artifacts" / name / "quint-result.json")
    require(run["exit_code"] == exit_code and not run["timed_out"], f"unexpected process result: {name}")
    require(run["inputs_unchanged"], f"input changed during execution: {name}")
    require(result.get("stage") == "verifying" and result.get("status") == status, f"unexpected checker result: {name}")
    require(result.get("errors") == [], f"checker errors present: {name}")
    logs = list((root / "artifacts" / name).glob("_apalache-out/server/*/detailed.log"))
    require(len(logs) == 1, f"expected one backend log: {name}")
    log = logs[0].read_text(encoding="utf-8")
    require("APALACHE version: 0.56.1 | build: 70cdaf4" in log, f"wrong Apalache version: {name}")
    return run, log


def states(root: Path, name: str) -> list[dict[str, Any]]:
    trace = read_json(root / "artifacts" / name / "trace.itf.json")
    value = trace.get("states")
    require(isinstance(value, list), f"missing ITF states: {name}")
    return value


def effect_count(state: dict[str, Any]) -> int:
    return int(state["effectCount"]["#bigint"])


def validate(root: Path) -> dict[str, Any]:
    validate_input_manifests(root)
    source = read_json(root / "source-readback.json")
    manifest = read_json(root / "input-manifest.json")
    validate_source_readback(source, manifest)

    for name in ("safe", "canary"):
        run = read_json(root / "runs" / f"typecheck-{name}" / "result.json")
        require(run["exit_code"] == 0 and not run["timed_out"], f"typecheck failed: {name}")
        require(run["inputs_unchanged"], f"typecheck input changed: {name}")

    bounded, bounded_log = validate_run(root, "bounded", 0, "ok")
    require("--max-steps=12" in bounded["argv"] and "--invariant=safety" in bounded["argv"], "bounded bound or invariant missing")
    require("State 12: Checking" in bounded_log and bounded_log.count("The outcome is: NoError") == 1, "bounded log is incomplete")

    canary, _ = validate_run(root, "canary", 1, "violation")
    require("--max-steps=2" in canary["argv"], "canary bound missing")
    canary_states = states(root, "canary")
    require(len(canary_states) == 2, "canary trace length is not two states")
    require(
        canary_states[0]["authorized"] is False
        and canary_states[0]["effected"] is False
        and canary_states[1]["authorized"] is False
        and canary_states[1]["effected"] is True,
        "canary trace does not show an unauthorized effect",
    )

    witnesses: dict[str, dict[str, Any]] = {}
    for name, target in (("terminal", "TERMINAL"), ("reconciliation", "RECONCILING")):
        receipt, _ = validate_run(root, name, 1, "violation")
        require("--max-steps=12" in receipt["argv"], f"reachability bound missing: {name}")
        reach_states = [state["s"] for state in states(root, name)]
        require(reach_states[0]["phase"] == "PREPARED" and reach_states[-1]["phase"] == target, f"wrong reachability target: {name}")
        require(len(reach_states) == 7, f"wrong witness length: {name}")
        for state in reach_states:
            count = effect_count(state)
            require(0 <= count <= 1, f"unsafe effect count in {name}")
            require(count == 0 or state["effectAuthorized"], f"unauthorized effect in {name}")
            require(
                not state["reportedSuccess"]
                or (state["phase"] == "TERMINAL" and state["receiptObserved"] and count == 1),
                f"unsupported success in {name}",
            )
        if name == "terminal":
            require(reach_states[-1]["reportedSuccess"] and reach_states[-1]["receiptObserved"] and effect_count(reach_states[-1]) == 1, "terminal witness is incomplete")
        else:
            require(reach_states[-2]["phase"] == "UNKNOWN" and reach_states[-2]["reconciled"], "reconciliation witness is incomplete")
            require(not reach_states[-1]["reconciled"] and effect_count(reach_states[-1]) == 0, "reconciliation witness has an effect")
        witnesses[name] = {"transitions": len(reach_states) - 1, "phases": [state["phase"] for state in reach_states]}

    _, induction_log = validate_run(root, "typed-inductive", 0, "ok")
    require(induction_log.count("The outcome is: NoError") == 3, "TypeOK obligations are incomplete")
    require(induction_log.count("Set the initialization predicate to q::init\n") == 1, "init obligation missing")
    require(induction_log.count("Set the initialization predicate to q::inductiveInv\n") == 2, "inductive obligations missing")
    require("Set an invariant to q::inv" in induction_log, "implication obligation missing")

    return {
        "schema": "fvl.p3-evidence.v1",
        "candidate_bounded_safety": {"status": "BOUNDED_PASS", "max_steps": 12},
        "unsafe_canary": {"status": "COUNTEREXAMPLE", "max_steps": 2, "witness_transitions": 1},
        "reachability": witnesses,
        "typed_induction": {
            "status": "PASS",
            "obligations": ["init => IndInv", "IndInv /\\ step => IndInv'", "IndInv => safety"],
        },
        "limits": [
            "candidate abstract model only",
            "no Quint-Python equivalence proof",
            "no liveness proof",
            "no Soodles Native or external authorization claim",
        ],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(args.evidence_dir.resolve())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "NOT_VERIFIED", "error": str(exc)}, indent=2))
        return 1
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    (args.evidence_dir / "evidence-validation.json").write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
