from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("source-manifest.json")
REMOVED_DUPLICATES = {
    Path("scripts/p3/models/canary.qnt"),
    Path("scripts/p3/models/operation.qnt"),
}
CURRENT_INPUTS = (
    Path("specs/operation.qnt"),
    Path("specs/canary.qnt"),
    Path("scripts/p3/source-manifest.json"),
    Path("scripts/p3/models/induction.qnt"),
    Path("scripts/p3/models/reachability.qnt"),
    Path("scripts/check_models.sh"),
    Path("scripts/p3/run.py"),
    Path("scripts/p3/validate.py"),
    Path("scripts/p3/verify_sources.py"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_input_paths(root: Path = ROOT) -> tuple[Path, ...]:
    return tuple(root / relative for relative in CURRENT_INPUTS)


def verify_removed_duplicates(root: Path) -> tuple[list[str], list[str]]:
    mismatches: list[str] = []
    absent: list[str] = []
    for relative in sorted(REMOVED_DUPLICATES):
        path = root / relative
        if path.exists() or path.is_symlink():
            mismatches.append(f"{relative}: duplicate model must be absent")
        else:
            absent.append(str(relative))
    return mismatches, absent


def verify(root: Path = ROOT) -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mismatches, removed_duplicates = verify_removed_duplicates(root)
    current_inputs: dict[str, str] = {}
    for relative in CURRENT_INPUTS:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            mismatches.append(f"{relative}: missing")
            continue
        current_inputs[str(path)] = sha256(path)

    imports: dict[str, str] = {}
    for harness in (Path("scripts/p3/models/induction.qnt"), Path("scripts/p3/models/reachability.qnt")):
        harness_path = root / harness
        if not harness_path.is_file() or harness_path.is_symlink():
            continue
        text = harness_path.read_text(encoding="utf-8")
        expected = 'import OperationProtocol.* from "../../../specs/operation"'
        if text.count(expected) != 1:
            mismatches.append(f"{harness}: must import repository operation.qnt")
        else:
            imports[str(harness)] = "specs/operation.qnt"

    integration_path = root / "scripts/check_models.sh"
    integration = integration_path.read_text(encoding="utf-8") if integration_path.is_file() else ""
    if "scripts/p3/run.py" not in integration:
        mismatches.append("scripts/check_models.sh: P3 runner invocation missing")

    return {
        "schema": "fvl.current-source-readback.v2",
        "historical_provenance": {
            "status": "HISTORICAL_NOT_REVERIFIED",
            "source_ref": manifest["ref"],
            "manifest_files": len(manifest["files"]),
            "manifest_sha256": sha256(MANIFEST),
        },
        "current_inputs": current_inputs,
        "duplicate_absence": removed_duplicates,
        "repository_imports": imports,
        "mismatches": mismatches,
        "claim": "current public checker inputs only; historical manifest retained as provenance",
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--lab", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.lab.resolve())
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if not result["mismatches"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
