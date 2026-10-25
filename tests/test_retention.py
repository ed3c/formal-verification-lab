from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from formal_verification_lab.cli import main
from formal_verification_lab.retention import evaluate_retention


def write(root: Path, name: str, value: dict) -> dict[str, str]:
    raw = json.dumps(value, sort_keys=True).encode()
    (root / name).write_bytes(raw)
    return {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}


def study(root: Path, *, candidate_detects: bool = True) -> dict:
    context = write(root, "context.json", {"entrypoint": "synthetic public CLI", "input_recipe": "same valid packet"})
    valid = write(root, "valid.json", {"effects": []})
    fault = write(root, "fault.json", {"effects": ["unexpected effect"]})
    contract = write(root, "contract.json", {"basis": "requirement", "source": "synthetic requirement:1",
                                            "statement": "Selected read-only review emits no effects."})
    tests = []
    observations = []
    for name in ("original", "remaining"):
        tests.append({"id": name, "source": write(root, name + ".source.json", {"test": name}), "context": context})
        for case, value in (("valid", valid), ("unexpected-effects", fault)):
            detects = case != "valid" and (name == "original" or candidate_detects)
            trace = {"test": name, "scenario": case, "input_sha256": value["sha256"],
                     "test_source_sha256": tests[-1]["source"]["sha256"],
                     "context_sha256": context["sha256"], "outcome": "assertion_failed" if detects else "passed",
                     "phase": "body" if detects else "complete"}
            observations.append({"test": name, "scenario": case,
                                 "ref": write(root, name + "." + case + ".json", trace)})
    return {"schema": "fvl.retention.v1", "scope": "Synthetic finite public-response projection only",
            "contracts": [{"id": "no-effects", "ref": contract}], "tests": tests,
            "scenarios": [{"id": "valid", "kind": "valid", "input": valid},
                          {"id": "unexpected-effects", "kind": "fault", "contract": "no-effects", "input": fault}],
            "observations": observations, "baseline": ["original", "remaining"], "candidate": ["remaining"]}


def evaluate(root: Path, packet: dict) -> dict:
    write(root, "study.json", packet)
    return evaluate_retention(root, "study.json")


def test_replacement_preserves_declared_guard_without_granting_retention_or_runtime_authority(tmp_path: Path) -> None:
    result = evaluate(tmp_path, study(tmp_path))
    assert result["verdict"] == "BOUNDED_PASS"
    assert result["findings"] == [{"property_id": "FVL-RETENTION-COVERAGE", "scenario": "unexpected-effects",
                                    "contract": "no-effects", "status": "BOUNDED_PASS",
                                    "witnesses": {"baseline": ["original", "remaining"], "candidate": ["remaining"]}}]
    assert result["retention_decision"] == "SESSION_REQUIRED"
    assert result["oracle_review"] == "SESSION_REQUIRED"
    assert result["model_checker"] == "NOT_RUN"
    assert result["authorizes_landing"] is False
    assert result["authorizes_production_effect"] is False


def test_missing_guard_is_a_named_canary_not_a_successful_schema(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "study.json", study(tmp_path, candidate_detects=False))
    assert main(["retention", str(tmp_path), "--study", "study.json", "--fail-on-counterexample"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["verdict"] == "COUNTEREXAMPLE"
    assert result["findings"][0]["scenario"] == "unexpected-effects"
    assert result["findings"][0]["witnesses"] == {"baseline": ["original"], "candidate": []}


@pytest.mark.parametrize("fault", ["missing_trace", "drift", "setup", "timeout", "context", "empty_context", "rebound_source", "implementation_oracle"])
def test_incomplete_or_noncomparable_evidence_cannot_establish_coverage(tmp_path: Path, fault: str) -> None:
    packet = study(tmp_path)
    observation = packet["observations"][-1]
    if fault == "missing_trace":
        (tmp_path / observation["ref"]["path"]).unlink()
    elif fault == "drift":
        (tmp_path / observation["ref"]["path"]).write_text("{}")
    elif fault in ("setup", "timeout"):
        trace = json.loads((tmp_path / observation["ref"]["path"]).read_text())
        trace.update(outcome="assertion_failed" if fault == "setup" else "timeout", phase="setup")
        observation["ref"] = write(tmp_path, observation["ref"]["path"], trace)
    elif fault in ("context", "empty_context"):
        context = {} if fault == "empty_context" else {"entrypoint": "different root/entrypoint", "input_recipe": "same valid packet"}
        for test in packet["tests"] if fault == "empty_context" else packet["tests"][1:]:
            test["context"] = write(tmp_path, "other-context.json", context)
        for row in packet["observations"]:
            if fault == "empty_context" or row["test"] == "remaining":
                trace = json.loads((tmp_path / row["ref"]["path"]).read_text())
                trace["context_sha256"] = packet["tests"][1]["context"]["sha256"]
                row["ref"] = write(tmp_path, row["ref"]["path"], trace)
    elif fault == "rebound_source":
        packet["tests"][1]["source"] = write(tmp_path, "remaining.source.json", {"test": "remaining", "revision": "changed"})
    else:
        packet["contracts"][0]["ref"] = write(tmp_path, "contract.json", {
            "basis": "implementation", "statement": "Current code happens to return an empty list.", "source": "code.py:1"})
    assert evaluate(tmp_path, packet)["verdict"] == "UNKNOWN"


def test_always_rejecting_control_is_not_a_valid_detector(tmp_path: Path) -> None:
    packet = study(tmp_path)
    row = packet["observations"][2]
    trace = json.loads((tmp_path / row["ref"]["path"]).read_text())
    trace.update(outcome="assertion_failed", phase="body")
    row["ref"] = write(tmp_path, row["ref"]["path"], trace)
    result = evaluate(tmp_path, packet)
    assert result["verdict"] == "COUNTEREXAMPLE"
    assert result["findings"][0] == {"property_id": "FVL-RETENTION-POSITIVE", "test": "remaining", "status": "COUNTEREXAMPLE"}
    assert result["findings"][1]["witnesses"]["candidate"] == []


def test_empty_fault_universe_cannot_pass_vacuously(tmp_path: Path) -> None:
    packet = study(tmp_path)
    packet["scenarios"] = packet["scenarios"][:1]
    packet["observations"] = [row for row in packet["observations"] if row["scenario"] == "valid"]
    assert evaluate(tmp_path, packet)["verdict"] == "UNKNOWN"


@pytest.mark.parametrize("field", ["contract", "test", "scenario"])
@pytest.mark.parametrize("identity", [[], {}])
def test_malformed_identity_returns_diagnostic_unknown(tmp_path: Path, capsys: pytest.CaptureFixture[str], field: str, identity: object) -> None:
    packet = study(tmp_path)
    if field == "contract":
        packet["scenarios"][1][field] = identity
    else:
        packet["observations"][0][field] = identity
    write(tmp_path, "study.json", packet)
    assert main(["retention", str(tmp_path), "--study", "study.json"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "UNKNOWN"


@pytest.mark.parametrize("escaped", [False, True])
def test_selected_path_boundary_is_preserved(tmp_path: Path, capsys: pytest.CaptureFixture[str], escaped: bool) -> None:
    packet = study(tmp_path)
    if escaped:
        packet["tests"][0]["source"]["path"] = "../outside.json"
    else:
        (tmp_path / "linked.json").symlink_to(tmp_path / "original.source.json")
        packet["tests"][0]["source"]["path"] = "linked.json"
    write(tmp_path, "study.json", packet)
    assert main(["retention", str(tmp_path), "--study", "study.json"]) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "UNKNOWN"
