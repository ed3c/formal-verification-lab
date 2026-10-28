from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import p4
import p4_readback


@pytest.fixture
def selected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Synthetic receipts exercise readback; they are not solver evidence."""
    source, evidence = tmp_path / "source", tmp_path / "evidence"
    for relative in set(p4_readback.ORACLE_FILES) | {
        str(path.relative_to(p4.ROOT)) for path in p4.INPUTS
    }:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p4.ROOT / relative, target)
    recorded = p4.input_digests()
    p4.write_json(evidence / "input-manifest.json", {"schema": "fvl.p4-inputs.v1", "digests": recorded})
    environment = {
        "python": "fixture", "python_executable": "fixture", "platform": "fixture",
        "expected": {}, "observed": {}, "missing": [], "mismatches": [],
    }
    p4.write_json(evidence / "versions.json", environment)
    original_loader = p4_readback.original_runner

    def load_runner():
        runner = original_loader()
        monkeypatch.setattr(runner, "package_versions", lambda: environment)
        return runner

    monkeypatch.setattr(p4_readback, "original_runner", load_runner)
    outputs = {
        "crosshair": "Confirmed over all paths.\nConfirmed over all paths.\n",
        "canary": "postcondition return False\nunchecked_effect(False) (which returns True)\n",
        "hypothesis": "2 passed\n",
        "controls": json.dumps(p4.literal_controls()),
    }
    results = {}
    for name, output in outputs.items():
        result = {
            "cwd": str(p4.ROOT), "exit_code": 1 if name == "canary" else 0,
            "timed_out": False, "process_error": None, "inputs_unchanged": True,
            "input_digests_before": recorded, "input_digests_after": recorded,
        }
        results[name] = result
        run = evidence / "runs" / name
        p4.write_json(run / "result.json", result)
        (run / "stdout.txt").write_text(output)
        (run / "stderr.txt").write_text("")
    p4.write_json(evidence / "summary.json", p4.validate_results(evidence, results))
    return source, evidence


def test_reuse_is_read_only_and_starts_no_checker(selected, monkeypatch):
    source, evidence = selected
    before = {p: p.read_bytes() for p in evidence.rglob("*") if p.is_file()}
    original_run = p4_readback.subprocess.run
    calls = []

    def read_only_git(command, **kwargs):
        assert command[:2] == ["git", "show"]
        calls.append(command)
        return original_run(command, **kwargs)

    monkeypatch.setattr(p4_readback.subprocess, "run", read_only_git)
    result = p4_readback.inspect(evidence, source)
    assert result["status"] == "REUSE"
    assert result["fresh_execution"] is False
    assert result["authorizes_acceptance"] is False
    assert calls
    assert before == {p: p.read_bytes() for p in evidence.rglob("*") if p.is_file()}


def test_source_change_invalidates_without_importing_candidate(selected):
    source, evidence = selected
    target = source / "src/formal_verification_lab/contracts.py"
    original = target.read_bytes()
    target.write_text("raise RuntimeError('candidate must not execute during readback')\n")
    result = p4_readback.inspect(evidence, source)
    assert result["status"] == "SOURCE_CHANGED"
    assert result["changed_sources"] == ["src/formal_verification_lab/contracts.py"]
    target.write_bytes(original)
    assert p4_readback.inspect(evidence, source)["status"] == "REUSE"


def test_oracle_change_requires_review_even_with_changed_source(selected):
    source, evidence = selected
    (source / "src/formal_verification_lab/formal_contracts.py").write_text("# weakened Oracle\n")
    (source / "src/formal_verification_lab/contracts.py").write_text("# drift\n")
    result = p4_readback.inspect(evidence, source)
    assert result["status"] == "ORACLE_REVIEW_REQUIRED"
    assert result["solver_runs"] == 0


@pytest.mark.parametrize("defect", ["missing_input", "run_binding", "false_summary", "missing_canary"])
def test_invalid_evidence_cannot_reuse(selected, defect):
    source, evidence = selected
    if defect == "missing_input":
        path = evidence / "input-manifest.json"
        value = json.loads(path.read_text())
        value["digests"].pop(next(iter(value["digests"])))
    elif defect == "run_binding":
        path = evidence / "runs/controls/result.json"
        value = json.loads(path.read_text())
        value["input_digests_after"] = {}
    elif defect == "false_summary":
        path, value = evidence / "summary.json", {"status": "BOUNDED_PASS"}
    else:
        path, value = evidence / "runs/canary/stdout.txt", "not a counterexample"
    path.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        p4_readback.inspect(evidence, source)


def test_environment_drift_retains_review_gap(selected):
    source, evidence = selected
    path = evidence / "versions.json"
    value = json.loads(path.read_text())
    value["python"] = "older"
    path.write_text(json.dumps(value))
    result = p4_readback.inspect(evidence, source)
    assert result["status"] == "ENVIRONMENT_REVIEW_REQUIRED"
    assert result["environment_changes"] == ["python"]
