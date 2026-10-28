"""Read the applicability of selected historical P4 evidence without running checks."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
SYNC_COMMIT = "72646cf797fa2a4f82f7b88f57dd7c5d0b309119"
# Bind the reviewed bytes without requiring history in shallow checkouts.
ORACLE_DIGESTS = {
    "docs/ACCEPTANCE.md": "44cfcce0faa22cfea5656357f3fb1e607a7a3b9710dddc4a6800a7cc589751eb",
    "src/formal_verification_lab/formal_contracts.py": "cc2f7c63e52a01451cf01fbdf4f69be78e9c25864ccc4047f0a2d317ac07fcb7",
    "tests/test_properties.py": "0a90c90a2ad984c3ac1f4f72b77ced480d6fcb5537137e67b211bef195906bfc",
    "scripts/p4.py": "c2cdd3fd08aad9d4f2f37bf8f6aa8d08d204862ba5ec92321df02bceb4e81ae0",
    "scripts/p4_canary.py": "4bb73921114e9cec7bde4a6a4adbe916e4dd6925587a3ba36a2f4c2af014ab93",
}
RUNS = ("crosshair", "canary", "hypothesis", "controls")


class ReadbackError(RuntimeError):
    pass


def digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ReadbackError(f"missing or linked input: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    digest(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReadbackError(f"expected JSON object: {path}")
    return value


def original_runner():
    path = ROOT / "scripts/p4.py"
    if digest(path) != ORACLE_DIGESTS["scripts/p4.py"]:
        raise ReadbackError("the readback's original P4 validator needs source review")
    spec = importlib.util.spec_from_file_location("p4_original", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect(evidence: Path, source: Path) -> dict:
    evidence, source = evidence.resolve(), source.resolve()
    result = {
        "sync_commit": SYNC_COMMIT,
        "evidence": str(evidence),
        "source": str(source),
        "fresh_execution": False,
        "solver_runs": 0,
        "authorizes_acceptance": False,
        "limits": [
            "historical pure-predicate evidence only, not a fresh PASS",
            "version metadata is not complete environment or executable attestation",
            "selected evidence custody and independent contract meaning need Session review",
        ],
    }
    changed_oracles = [p for p, expected in ORACLE_DIGESTS.items() if digest(source / p) != expected]
    if changed_oracles:
        return {**result, "status": "ORACLE_REVIEW_REQUIRED", "changed_oracles": changed_oracles}

    runner = original_runner()
    manifest = read_json(evidence / "input-manifest.json")
    if manifest.get("schema") != "fvl.p4-inputs.v1":
        raise ReadbackError("unsupported P4 input manifest")
    results = {name: read_json(evidence / "runs" / name / "result.json") for name in RUNS}
    origin = Path(results["crosshair"]["cwd"])
    if not origin.is_absolute():
        raise ReadbackError("P4 receipt cwd must be absolute")
    expected_paths = {str(origin / p.relative_to(ROOT)) for p in runner.INPUTS}
    recorded = manifest["digests"]
    if not isinstance(recorded, dict) or set(recorded) != expected_paths:
        raise ReadbackError("P4 receipt does not bind the complete original input set")
    for name, run in results.items():
        if (run.get("cwd") != str(origin)
                or run.get("input_digests_before") != recorded
                or run.get("input_digests_after") != recorded):
            raise ReadbackError(f"inconsistent original source binding: {name}")
    summary = runner.validate_results(evidence, results)
    if read_json(evidence / "summary.json") != summary:
        raise ReadbackError("saved summary disagrees with original P4 results")
    changed_sources = [
        str(p.relative_to(ROOT)) for p in runner.INPUTS
        if digest(source / p.relative_to(ROOT)) != recorded[str(origin / p.relative_to(ROOT))]
    ]
    if changed_sources:
        return {**result, "status": "SOURCE_CHANGED", "changed_sources": changed_sources,
                "original_summary": summary}
    previous, current = read_json(evidence / "versions.json"), runner.package_versions()
    fields = ("python", "python_executable", "platform", "expected", "observed", "missing", "mismatches")
    environment_changes = [field for field in fields if previous.get(field) != current[field]]
    if current["missing"] or current["mismatches"] or environment_changes:
        return {**result, "status": "ENVIRONMENT_REVIEW_REQUIRED",
                "environment_changes": environment_changes, "current_environment": current}
    return {**result, "status": "REUSE", "original_summary": summary,
            "source_inputs_matched": len(expected_paths),
            "receipt_sha256": digest(evidence / "summary.json")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--source", type=Path, default=ROOT,
                        help="selected source root; defaults to this Lab checkout")
    args = parser.parse_args()
    try:
        result = inspect(args.evidence, args.source)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        result = {"status": "EVIDENCE_REVIEW_REQUIRED", "error": str(exc),
                  "fresh_execution": False, "solver_runs": 0, "authorizes_acceptance": False}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "REUSE" else 2


if __name__ == "__main__":
    sys.exit(main())
