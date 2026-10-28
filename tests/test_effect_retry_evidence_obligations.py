from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from formal_verification_lab.bundles import MAX_PART_BYTES, load_selection
from formal_verification_lab.kernel import evaluate


PROPERTIES = ("FVL-LEGAL", "FVL-RETRY", "FVL-POST-BIND", "FVL-NO-DUPLICATE")


@pytest.fixture
def retry_record() -> dict:
    return {
        "provenance": "synthetic",
        "operation": {
            "kind": "RETRY", "operation_id": "SYNTHETIC_OPERATION",
            "session_id": "SYNTHETIC_SESSION", "idempotency_key": "SYNTHETIC_KEY",
            "from_state": "FAILED", "to_state": "CLAIMED",
            "prior_attempt_seq": 10, "action_seq": 30,
        },
        "provider": {
            "operation_id": "SYNTHETIC_OPERATION", "idempotency_key": "SYNTHETIC_KEY",
            "observed_seq": 20, "reconciled": True, "effect_count": 0, "complete": True,
        },
    }


def statuses(result: dict) -> dict:
    return {item["property_id"]: item["status"] for item in result["findings"]}


def test_explicit_synthetic_no_effect_retry_passes_only_selected_properties(retry_record: dict) -> None:
    result = evaluate(retry_record, PROPERTIES)

    assert result["verdict"] == "BOUNDED_PASS"
    assert statuses(result) == {
        "FVL-LEGAL": "BOUNDED_PASS", "FVL-RETRY": "BOUNDED_PASS",
        "FVL-POST-BIND": "BOUNDED_PASS", "FVL-NO-DUPLICATE": "BOUNDED_PASS",
    }
    assert result["claim_level"] == "SYNTHETIC_CONFORMANCE"
    assert result["scope"] == "SELECTED_PROPERTIES"
    assert result["production_acceptance"] == "NOT_RUN"
    assert result["authorizes_production_effect"] is False
    assert result["authorizes_landing"] is False


@pytest.mark.parametrize("count,duplicate", [(1, "BOUNDED_PASS"), (2, "COUNTEREXAMPLE")])
def test_bound_positive_effect_contradicts_no_effect_retry(retry_record: dict, count: int, duplicate: str) -> None:
    retry_record["provider"]["effect_count"] = count

    result = evaluate(retry_record, PROPERTIES)

    assert result["verdict"] == "COUNTEREXAMPLE"
    assert statuses(result) == {
        "FVL-LEGAL": "BOUNDED_PASS", "FVL-RETRY": "COUNTEREXAMPLE",
        "FVL-POST-BIND": "BOUNDED_PASS", "FVL-NO-DUPLICATE": duplicate,
    }
    assert retry_record["provider"]["effect_count"] == count


def test_bound_duplicate_lower_bound_needs_no_complete_absence_claim(retry_record: dict) -> None:
    retry_record["provider"].update(effect_count=2, complete=False)

    result = evaluate(retry_record, ["FVL-RETRY", "FVL-NO-DUPLICATE"])

    assert statuses(result) == {"FVL-RETRY": "COUNTEREXAMPLE", "FVL-NO-DUPLICATE": "COUNTEREXAMPLE"}
    assert retry_record["provider"]["complete"] is False


@pytest.mark.parametrize("field,value", [
    ("operation_id", "SYNTHETIC_OTHER_OPERATION"),
    ("idempotency_key", "SYNTHETIC_OTHER_KEY"),
    ("observed_seq", 5), ("observed_seq", 35),
])
def test_wrong_proposed_subject_key_or_order_is_a_scoped_counterexample(retry_record: dict, field: str, value) -> None:
    retry_record["provider"][field] = value

    result = evaluate(retry_record, ["FVL-RETRY", "FVL-POST-BIND"])

    assert statuses(result) == {"FVL-RETRY": "COUNTEREXAMPLE", "FVL-POST-BIND": "COUNTEREXAMPLE"}
    assert retry_record["provider"][field] == value


@pytest.mark.parametrize("complete", [False, None])
def test_zero_count_without_complete_scope_cannot_prove_no_effect(retry_record: dict, complete) -> None:
    if complete is None:
        del retry_record["provider"]["complete"]
    else:
        retry_record["provider"]["complete"] = complete

    result = evaluate(retry_record, PROPERTIES)

    assert result["verdict"] == "UNKNOWN"
    assert statuses(result) == {
        "FVL-LEGAL": "BOUNDED_PASS", "FVL-RETRY": "UNKNOWN",
        "FVL-POST-BIND": "BOUNDED_PASS", "FVL-NO-DUPLICATE": "UNKNOWN",
    }


@pytest.mark.parametrize("part,field", [
    ("operation", "operation_id"), ("operation", "idempotency_key"),
    ("operation", "prior_attempt_seq"), ("provider", "operation_id"),
    ("provider", "idempotency_key"), ("provider", "observed_seq"),
])
def test_missing_binding_fact_limits_dependent_checks_only(retry_record: dict, part: str, field: str) -> None:
    del retry_record[part][field]
    before = deepcopy(retry_record)

    result = evaluate(retry_record, PROPERTIES)

    assert statuses(result) == {
        "FVL-LEGAL": "BOUNDED_PASS", "FVL-RETRY": "UNKNOWN",
        "FVL-POST-BIND": "UNKNOWN", "FVL-NO-DUPLICATE": "UNKNOWN",
    }
    assert retry_record == before


@pytest.mark.parametrize("raw_provider", [
    {"effect_ledger": [{"effect_id": "SYNTHETIC_DISPATCH", "status": "pending", "attempts": 0,
                        "effect": {"type": "dispatch", "payload": {"order_id": "SYNTHETIC_ORDER", "stage_index": 0}}}]},
    {"status": "UNKNOWN", "effects": [], "gaps": [{"code": "SYNTHETIC_CAPTURE_GAP"}]},
    {"exit_code": 0, "drained": True, "owned_group_absent": True,
     "complete_tool_process_capture": None, "mcp_tools_inventory": None},
    {"id": "SYNTHETIC_CONTROL", "action": "requeue", "status": "ok"},
    {"argv": ["git", "push", "origin", "HEAD:refs/heads/SYNTHETIC"], "exit_code": 1,
     "stderr": "remote: error: GH007: private email protection\n",
     "endpoint_before": "SYNTHETIC_REMOTE_HEAD", "endpoint_after": "SYNTHETIC_REMOTE_HEAD",
     "first_local_head": "SYNTHETIC_CANDIDATE_A", "second_local_head": "SYNTHETIC_CANDIDATE_B"},
], ids=["pending-declarative-dispatch", "unknown-empty-capture", "native-exit-with-missing-coverage",
        "control-ack", "non-porcelain-rejection-and-endpoint"])
def test_raw_process_or_workflow_shapes_never_become_provider_no_effect(retry_record: dict, raw_provider: dict) -> None:
    retry_record["provider"] = deepcopy(raw_provider)
    before = deepcopy(retry_record)

    result = evaluate(retry_record, PROPERTIES)

    assert result["verdict"] == "UNKNOWN"
    assert statuses(result) == {
        "FVL-LEGAL": "BOUNDED_PASS", "FVL-RETRY": "UNKNOWN",
        "FVL-POST-BIND": "UNKNOWN", "FVL-NO-DUPLICATE": "UNKNOWN",
    }
    assert result["observations"] == {"provider_effect_count": None}
    assert retry_record == before
    assert "effect_count" not in retry_record["provider"]
    assert "reconciled" not in retry_record["provider"]
    assert "complete" not in retry_record["provider"]


def test_worker_order_and_stage_do_not_supply_an_operation_or_key() -> None:
    record = {
        "provenance": "synthetic",
        "operation": {"order_id": "SYNTHETIC_ORDER", "stage_index": 0, "status": "pending"},
        "provider": {"effects": [], "status": "UNKNOWN"},
    }
    before = deepcopy(record)

    result = evaluate(record, PROPERTIES)

    assert result["operation_id"] is None
    assert statuses(result) == dict.fromkeys(PROPERTIES, "UNKNOWN")
    assert record == before


def test_cli_partial_selection_preserves_raw_evidence_and_independent_legality(tmp_path: Path, retry_record: dict) -> None:
    operation_path = tmp_path / "synthetic-operation.json"
    provider_path = tmp_path / "synthetic-provider.json"
    operation_path.write_text(json.dumps(retry_record["operation"]), encoding="utf-8")
    provider_path.write_text(json.dumps({"status": "UNKNOWN", "effects": []}), encoding="utf-8")
    before = {path.name: path.read_bytes() for path in (operation_path, provider_path)}
    selected = load_selection(tmp_path, [("operation", operation_path.name), ("provider", provider_path.name)])

    assert statuses(evaluate(selected, PROPERTIES)) == {
        "FVL-LEGAL": "BOUNDED_PASS", "FVL-RETRY": "UNKNOWN",
        "FVL-POST-BIND": "UNKNOWN", "FVL-NO-DUPLICATE": "UNKNOWN",
    }
    argv = [sys.executable, "-B", "-m", "formal_verification_lab.cli", "evaluate", str(tmp_path),
            "--select", "operation=" + operation_path.name, "--select", "provider=" + provider_path.name]
    for property_id in PROPERTIES:
        argv.extend(["--property", property_id])
    actual = subprocess.run(argv, cwd=Path(__file__).parents[1], capture_output=True, timeout=10, check=False)

    assert actual.returncode == 0, actual.stderr
    result = json.loads(actual.stdout)
    assert result["verdict"] == "UNKNOWN"
    assert statuses(result) == {
        "FVL-LEGAL": "BOUNDED_PASS", "FVL-RETRY": "UNKNOWN",
        "FVL-POST-BIND": "UNKNOWN", "FVL-NO-DUPLICATE": "UNKNOWN",
    }
    assert result["claim_level"] == "UNAUTHENTICATED_OFFLINE_READBACK"
    assert result["selected_parts"] == ["operation", "provider"]
    assert result["missing_parts"] == ["authority", "evidence", "preflight"]
    assert result["source_refs"] == {
        "operation": {"path": operation_path.name, "sha256": hashlib.sha256(before[operation_path.name]).hexdigest()},
        "provider": {"path": provider_path.name, "sha256": hashlib.sha256(before[provider_path.name]).hexdigest()},
    }
    assert result["authorizes_production_effect"] is False
    assert {path.name: path.read_bytes() for path in (operation_path, provider_path)} == before


def test_cli_oversized_provider_preserves_selection_error_and_independent_legality(tmp_path: Path, retry_record: dict) -> None:
    operation_path = tmp_path / "synthetic-operation.json"
    provider_path = tmp_path / "synthetic-provider.json"
    operation_path.write_text(json.dumps(retry_record["operation"]), encoding="utf-8")
    provider_path.write_bytes(b'{"SYNTHETIC_PADDING":"' + b"x" * MAX_PART_BYTES + b'"}\n')
    before = {path.name: path.read_bytes() for path in (operation_path, provider_path)}
    argv = [sys.executable, "-B", "-m", "formal_verification_lab.cli", "evaluate", str(tmp_path),
            "--select", "operation=" + operation_path.name, "--select", "provider=" + provider_path.name]
    for property_id in PROPERTIES:
        argv.extend(["--property", property_id])

    actual = subprocess.run(argv, cwd=Path(__file__).parents[1], capture_output=True, timeout=10, check=False)

    assert actual.returncode == 0, actual.stderr
    result = json.loads(actual.stdout)
    assert result["verdict"] == "UNKNOWN"
    assert statuses(result) == {
        "FVL-LEGAL": "BOUNDED_PASS", "FVL-RETRY": "UNKNOWN",
        "FVL-POST-BIND": "UNKNOWN", "FVL-NO-DUPLICATE": "UNKNOWN",
    }
    assert result["requested_parts"] == ["operation", "provider"]
    assert result["selected_parts"] == ["operation"]
    assert result["missing_parts"] == ["authority", "evidence", "preflight", "provider"]
    assert result["source_refs"] == {
        "operation": {"path": operation_path.name, "sha256": hashlib.sha256(before[operation_path.name]).hexdigest()},
    }
    assert result["selection_errors"] == [
        {"role": "provider", "path": provider_path.name, "error": "Oversized bundle part"},
    ]
    assert result["observations"] == {}
    assert result["authorizes_production_effect"] is False
    assert {path.name: path.read_bytes() for path in (operation_path, provider_path)} == before
