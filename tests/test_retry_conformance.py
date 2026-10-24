from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from formal_verification_lab.retry_conformance import (
    InputError, analyze_lifecycle, check_model_step, inspect_resume, parse_lifecycle,
)


def jsonl(values) -> bytes:
    return b"".join((json.dumps(value) + "\n").encode() for value in values)


def event(seq, kind, order="SYNTHETIC_ORDER", **extra):
    return {"seq": seq, "type": kind, "at": "2026-01-01T00:00:00Z",
            "payload": {"order_id": order, **extra}}


def state(phase="FAILED", reconciled=True):
    return {"phase": phase, "authorized": True, "bound": True, "fresh": True,
            "reconciled": reconciled, "effect_count": 0, "effect_authorized": False,
            "receipt_observed": False, "reported_success": False}


@pytest.fixture
def lifecycle():
    return jsonl([event(1, "stage.failed", stage_index=0, session_id="SYNTHETIC_PREVIOUS"),
                  event(2, "order.failed"), event(3, "order.requeued")])


@pytest.fixture
def resume():
    previous_raw = jsonl([{"type": "thread.started", "thread_id": "SYNTHETIC_THREAD"}, {"type": "turn.completed"}])
    resumed_raw = jsonl([{"type": "thread.started", "thread_id": "SYNTHETIC_THREAD"}, {"type": "turn.completed"}])
    previous = {"session_id": "SYNTHETIC_PREVIOUS", "order_id": "SYNTHETIC_ORDER", "stage_index": "0"}
    resumed = {"session_id": "SYNTHETIC_RESUMED", "order_id": "SYNTHETIC_ORDER", "stage_index": "0",
               "retry_count": 1, "resume_session_id": "SYNTHETIC_PREVIOUS", "resume_thread_id": "SYNTHETIC_THREAD",
               "resume_source_sha256": hashlib.sha256(previous_raw).hexdigest()}
    attempts = [{"attempt_id": "SYNTHETIC_A0", "session_id": "SYNTHETIC_PREVIOUS", "status": "failed", "exit_code": None},
                {"attempt_id": "SYNTHETIC_A1", "session_id": "SYNTHETIC_RESUMED", "status": "completed", "exit_code": None}]
    snapshot = {"state": {"orders": {"SYNTHETIC_ORDER": {"status": "active", "stages": [
        {"status": "review", "attempts": attempts}]}}},
                "effect_ledger": [{"effect_id": "SYNTHETIC_DISPATCH", "status": "pending", "attempts": 0,
                                   "effect": {"type": "dispatch", "payload": {"order_id": "SYNTHETIC_ORDER", "stage_index": 0,
                                                                             "attempt_id": "SYNTHETIC_A1"}}}]}
    return previous, resumed, previous_raw, resumed_raw, snapshot


def test_observed_lifecycle_prefix_retains_mapping_and_source_without_effect_proof(lifecycle):
    parsed = parse_lifecycle(lifecycle)
    assert [item.kind for item in parsed] == ["stage.failed", "order.failed", "order.requeued"]
    assert parsed[0].stage == 0 and parsed[0].line == 1
    assert parsed[0].sha256 == hashlib.sha256(lifecycle.splitlines(keepends=True)[0]).hexdigest()
    result = analyze_lifecycle(lifecycle)
    assert result["source_sha256"] == hashlib.sha256(lifecycle).hexdigest()
    assert result["coverage"] == "BEST_EFFORT_NOT_COMPLETE_PROOF"
    assert result["sequence_gaps"] == []
    assert result["requeues"] == [{"order_id": "SYNTHETIC_ORDER", "requeue_seq": 3,
                                    "observed_prefix": "OBSERVED_ORDERED_PREFIX", "stage_failed_seq": 1,
                                    "order_failed_seq": 2, "candidate_action": "retry", "model_conformance": "UNKNOWN",
                                    "missing": ["operation pre-phase", "ordered no-effect reconciliation", "matching complete effect scope"],
                                    "new_attempt_started": None}]
    assert result["events"][0]["mapping"] == {"candidate_action": "markFailed", "domain": "worker", "status": "UNKNOWN"}
    assert result["events"][1]["mapping"]["candidate_action"] is None
    assert result["events"][2]["mapping"]["candidate_action"] == "retry"
    assert "reconcileNoEffect" not in json.dumps(result)


@pytest.mark.parametrize("values", [[], [event(1, "order.requeued")],
                                    [event(1, "stage.failed", order="SYNTHETIC_OTHER"), event(2, "order.failed"), event(3, "order.requeued")],
                                    [event(1, "stage.failed"), event(2, "order.requeued"), event(3, "order.failed")]])
def test_absent_or_incomparable_prefix_is_unknown_not_a_counterexample(values):
    result = analyze_lifecycle(jsonl(values))
    assert all(item["observed_prefix"] == "UNKNOWN" for item in result["requeues"])
    assert result["full_native_refinement"] == "NOT_ESTABLISHED"


def test_sequence_gaps_and_unknown_event_family_are_not_discarded():
    result = analyze_lifecycle(jsonl([event(8, "stage_failed"), event(12, "SYNTHETIC_UNMAPPED"), event(13, "order.requeued")]))
    assert result["first_seq"] == 8 and result["last_seq"] == 13
    assert result["sequence_gaps"] == [{"from": 9, "to": 11}]
    assert [item["kind"] for item in result["events"]] == ["stage_failed", "SYNTHETIC_UNMAPPED", "order.requeued"]
    assert result["events"][0]["mapping"]["domain"] == "unmapped"
    assert result["requeues"][0]["observed_prefix"] == "UNKNOWN"


@pytest.mark.parametrize("seqs", [[1, 1], [2, 1], [0], [True], [1.0]])
def test_invalid_sequence_values_fail_explicitly(seqs):
    with pytest.raises(InputError, match="seq"):
        parse_lifecycle(jsonl([event(seq, "order.requeued") for seq in seqs]))


@pytest.mark.parametrize("raw", [b"not-json\n", b"\xff\n", b"[]\n", b"\n", b'{"seq":1,"seq":2}\n',
                                  b'{"seq":NaN}\n', b'{"seq":1e999}\n'])
def test_malformed_jsonl_never_becomes_a_partial_success(raw):
    with pytest.raises(InputError):
        analyze_lifecycle(raw)


@pytest.mark.parametrize("change", [{"payload": []}, {"payload": {"order_id": ""}},
                                     {"payload": {"order_id": "SYNTHETIC_ORDER", "stage_index": True}},
                                     {"payload": {"order_id": "SYNTHETIC_ORDER", "stage_index": "0"}}, {"at": None}])
def test_lifecycle_boundary_shapes_are_explicit(change):
    value = event(1, "stage.failed")
    value.update(change)
    with pytest.raises(InputError):
        analyze_lifecycle(jsonl([value]))


def test_decoder_integer_limit_is_a_named_input_error(tmp_path):
    raw = b'{"seq":' + b'9' * 5000 + b'}\n'
    with pytest.raises(InputError, match="invalid UTF-8 JSON"):
        analyze_lifecycle(raw)
    path = tmp_path / "SYNTHETIC-large-integer.jsonl"
    path.write_bytes(raw)
    result = cli("--events", str(path))
    assert result.returncode == 2 and result.stdout == b""
    assert b"InputError: invalid UTF-8 JSON" in result.stderr
    assert b"Traceback" not in result.stderr
    assert path.read_bytes() == raw


def test_read_bound_refuses_without_truncation(lifecycle):
    with pytest.raises(InputError, match="no truncation"):
        analyze_lifecycle(lifecycle, max_events=2)
    with pytest.raises(InputError, match="positive integer"):
        analyze_lifecycle(lifecycle, max_events=True)


def test_literal_retry_steps_match_existing_model_and_preserve_observed_values():
    before, after = state(), state("CLAIMED", False)
    saved = deepcopy(before), deepcopy(after)
    result = check_model_step("retry", before, after)
    assert result["status"] == "BOUNDED_PASS"
    assert result["named_successors"] == [after]
    assert (before, after) == saved
    assert result["global_reachability"] == "NOT_ESTABLISHED"
    unknown = check_model_step("retry", state("UNKNOWN"), state("RECONCILING", False))
    assert unknown["status"] == "BOUNDED_PASS"


def test_disabled_retry_and_wrong_after_state_are_counterexamples():
    disabled = check_model_step("retry", state(reconciled=False), state("CLAIMED", False))
    assert disabled["status"] == "COUNTEREXAMPLE"
    assert disabled["diagnostic"] == "action disabled in observed before state"
    wrong = check_model_step("retry", state(), state("RECONCILING", False))
    assert wrong["status"] == "COUNTEREXAMPLE"
    assert wrong["after"]["phase"] == "RECONCILING"


def test_mark_failed_alias_does_not_invent_executing_to_failed_edge():
    good = check_model_step("markFailed", state("CLAIMED", False), state("FAILED", False))
    assert good["python_action"] == "fail" and good["status"] == "BOUNDED_PASS"
    bad = check_model_step("markFailed", state("EXECUTING", False), state("FAILED", False))
    assert bad["status"] == "COUNTEREXAMPLE"
    assert bad["named_successors"] == []


def test_partial_observations_do_not_receive_state_defaults():
    result = check_model_step("retry", {"phase": "FAILED"}, None)
    assert result["status"] == "UNKNOWN"
    assert "before.reconciled" in result["missing"] and "after.effect_count" in result["missing"]
    assert result["before"] == {"phase": "FAILED"} and result["after"] is None
    assert check_model_step("SYNTHETIC_UNKNOWN", state(), state("CLAIMED", False))["status"] == "UNKNOWN"
    assert check_model_step("retry", state("RUNNING"), state("CLAIMED", False))["status"] == "UNKNOWN"


@pytest.mark.parametrize("field,value", [("effect_count", True), ("authorized", 1), ("phase", 1), ("reconciled", None)])
def test_operation_model_types_keep_bool_and_int_distinct(field, value):
    before = state()
    before[field] = value
    with pytest.raises(InputError, match="wrong type"):
        check_model_step("retry", before, state("CLAIMED", False))


def test_shared_native_thread_requires_explicit_resume_bindings_and_retains_snapshot(resume):
    result = inspect_resume(*resume)
    assert result["status"] == "BOUNDED_PASS"
    assert result["checks"] == {"predecessor_session": True, "order": True, "stage": True,
                                 "source_sha256": True, "prior_thread": True, "current_thread": True, "retry_count": True}
    assert result["stage_encoding"] == {"previous_raw": "0", "resumed_raw": "0", "previous_normalized": 0,
                                         "resumed_normalized": 0, "conversion": "explicit_spawn_decimal_to_integer"}
    assert result["snapshot"]["status"] == "OBSERVED_ATTEMPT_BINDING"
    assert result["snapshot"]["distinct_attempt_ids"] is True
    assert [item["attempt_id"] for item in result["snapshot"]["attempts"]] == ["SYNTHETIC_A0", "SYNTHETIC_A1"]
    assert [item["exit_code"] for item in result["snapshot"]["attempts"]] == [None, None]
    assert result["snapshot"]["dispatch_effects"][0]["status"] == "pending"
    assert result["previous_native"]["terminals"] == [{"line": 2, "type": "turn.completed"}]
    assert result["resumed_native"]["terminals"] == [{"line": 2, "type": "turn.completed"}]
    assert result["operation_retry_conformance"] == "UNKNOWN"
    assert result["process_exit"] == "UNKNOWN"


@pytest.mark.parametrize("key,value,check", [("resume_session_id", "SYNTHETIC_WRONG", "predecessor_session"),
                                             ("resume_source_sha256", "SYNTHETIC_WRONG", "source_sha256"),
                                             ("resume_thread_id", "SYNTHETIC_WRONG", "prior_thread"),
                                             ("order_id", "SYNTHETIC_WRONG", "order"), ("stage_index", "1", "stage")])
def test_resume_contradictions_are_retained(resume, key, value, check):
    previous, resumed, prior_raw, current_raw, snapshot = resume
    resumed[key] = value
    result = inspect_resume(previous, resumed, prior_raw, current_raw, snapshot)
    assert result["status"] == "COUNTEREXAMPLE"
    assert result["checks"][check] is False
    assert resumed[key] == value


def test_missing_resume_fields_and_ambiguous_attempts_are_unknown(resume):
    previous, resumed, prior_raw, current_raw, snapshot = resume
    del resumed["resume_source_sha256"]
    result = inspect_resume(previous, resumed, prior_raw, current_raw)
    assert result["status"] == "UNKNOWN" and result["checks"]["source_sha256"] is None
    attempts = snapshot["state"]["orders"]["SYNTHETIC_ORDER"]["stages"][0]["attempts"]
    attempts.append(dict(attempts[0]))
    result = inspect_resume(previous, resumed, prior_raw, current_raw, snapshot)
    assert result["snapshot"]["status"] == "UNKNOWN"
    assert result["snapshot"]["ambiguities"] == [{"role": "previous", "matches": 2}]
    assert result["snapshot"]["distinct_attempt_ids"] is None


def test_missing_attempt_ids_are_not_invented_from_sessions(resume):
    previous, resumed, prior_raw, current_raw, snapshot = resume
    for item in snapshot["state"]["orders"]["SYNTHETIC_ORDER"]["stages"][0]["attempts"]:
        del item["attempt_id"]
    result = inspect_resume(previous, resumed, prior_raw, current_raw, snapshot)
    assert result["snapshot"]["distinct_attempt_ids"] is None
    assert [item["attempt_id"] for item in result["snapshot"]["attempts"]] == [None, None]


@pytest.mark.parametrize("stage", [True, "00", "-1", "1.0", -1, []])
def test_spawn_stage_encodings_are_explicit(resume, stage):
    previous, resumed, prior_raw, current_raw, snapshot = resume
    resumed["stage_index"] = stage
    with pytest.raises(InputError, match="stage_index"):
        inspect_resume(previous, resumed, prior_raw, current_raw, snapshot)


@pytest.mark.parametrize("stage", [False, True, 0.0, "0", -1])
def test_selected_snapshot_dispatch_stage_requires_integer_identity(resume, stage):
    previous, resumed, prior_raw, current_raw, snapshot = resume
    snapshot["effect_ledger"][0]["effect"]["payload"]["stage_index"] = stage
    with pytest.raises(InputError, match="snapshot dispatch stage_index"):
        inspect_resume(previous, resumed, prior_raw, current_raw, snapshot)


def test_missing_snapshot_dispatch_stage_remains_an_explicit_unknown(resume):
    previous, resumed, prior_raw, current_raw, snapshot = resume
    del snapshot["effect_ledger"][0]["effect"]["payload"]["stage_index"]
    result = inspect_resume(previous, resumed, prior_raw, current_raw, snapshot)
    assert result["snapshot"]["dispatch_effects"] == []
    assert result["snapshot"]["dispatch_ambiguities"] == [
        {"effect_id": "SYNTHETIC_DISPATCH", "stage_index": None, "reason": "stage_index unavailable"}]
    assert "stage_index" not in snapshot["effect_ledger"][0]["effect"]["payload"]
    assert result["operation_retry_conformance"] == "UNKNOWN"


def test_spawn_decimal_encoding_has_no_added_ten_digit_limit(resume):
    previous, resumed, prior_raw, current_raw, _ = resume
    previous["stage_index"] = 12345678901
    resumed["stage_index"] = "12345678901"
    result = inspect_resume(previous, resumed, prior_raw, current_raw)
    assert result["checks"]["stage"] is True
    assert result["stage_encoding"]["previous_raw"] == 12345678901
    assert result["stage_encoding"]["resumed_raw"] == "12345678901"
    assert result["stage_encoding"]["resumed_normalized"] == 12345678901


def test_spawn_decimal_decoder_limit_is_named_without_changing_the_language_limit(resume):
    previous, resumed, prior_raw, current_raw, _ = resume
    resumed["stage_index"] = "9" * 5000
    with pytest.raises(InputError, match="integer decoder limit"):
        inspect_resume(previous, resumed, prior_raw, current_raw)


def test_cli_refuses_boolean_snapshot_dispatch_stage_without_partial_output(tmp_path, lifecycle, resume):
    previous, resumed, prior_raw, current_raw, snapshot = resume
    snapshot["effect_ledger"][0]["effect"]["payload"]["stage_index"] = False
    values = {"events": lifecycle, "previous-spawn": json.dumps(previous).encode(), "resumed-spawn": json.dumps(resumed).encode(),
              "previous-raw": prior_raw, "resumed-raw": current_raw, "snapshot": json.dumps(snapshot).encode()}
    arguments = []
    for name, raw in values.items():
        path = tmp_path / (name + ".synthetic")
        path.write_bytes(raw)
        arguments.extend(["--" + name, str(path)])
    result = cli(*arguments)
    assert result.returncode == 2 and result.stdout == b""
    assert b"InputError: snapshot dispatch stage_index" in result.stderr
    assert b"Traceback" not in result.stderr
    for name, raw in values.items():
        assert (tmp_path / (name + ".synthetic")).read_bytes() == raw


def cli(*args):
    return subprocess.run([sys.executable, "-B", "-m", "formal_verification_lab.retry_conformance", *args],
                          cwd=Path(__file__).parents[1], capture_output=True, check=False, timeout=10)


def test_real_cli_reads_selected_synthetic_files_and_does_not_change_them(tmp_path, lifecycle, resume):
    previous, resumed, prior_raw, current_raw, snapshot = resume
    values = {"events": lifecycle, "previous-spawn": json.dumps(previous).encode(), "resumed-spawn": json.dumps(resumed).encode(),
              "previous-raw": prior_raw, "resumed-raw": current_raw, "snapshot": json.dumps(snapshot).encode(),
              "model-steps": json.dumps({"schema": 1, "steps": [{"action": "retry", "before": state(), "after": state("CLAIMED", False)}]}).encode()}
    arguments = []
    for name, raw in values.items():
        path = tmp_path / (name + ".synthetic")
        path.write_bytes(raw)
        arguments.extend(["--" + name, str(path)])
    result = cli(*arguments)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["lifecycle"]["requeues"][0]["observed_prefix"] == "OBSERVED_ORDERED_PREFIX"
    assert observed["resume"]["status"] == "BOUNDED_PASS"
    assert observed["local_model_steps"][0]["status"] == "BOUNDED_PASS"
    assert observed["native_model_conformance"] == "UNKNOWN"
    assert len(observed["sources"]) == 7
    for name, raw in values.items():
        assert (tmp_path / (name + ".synthetic")).read_bytes() == raw
        assert next(item for item in observed["sources"] if item["role"] == name.replace("-", "_"))["sha256"] == hashlib.sha256(raw).hexdigest()


def test_cli_partial_sources_do_not_block_lifecycle_and_invalid_input_has_no_stdout(tmp_path, lifecycle):
    path = tmp_path / "SYNTHETIC-events.jsonl"
    path.write_bytes(lifecycle)
    result = cli("--events", str(path))
    assert result.returncode == 0
    observed = json.loads(result.stdout)
    assert observed["resume"]["status"] == "UNKNOWN"
    path.write_bytes(b'{"seq":true}\n')
    invalid = cli("--events", str(path))
    assert invalid.returncode == 2 and invalid.stdout == b""
    assert b"InputError" in invalid.stderr
