from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from formal_verification_lab.bundles import BundleError, discover, load_selection
from formal_verification_lab.cli import main
from formal_verification_lab.kernel import evaluate


def write(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def finding(result: dict, name: str) -> dict:
    return next(item for item in result["findings"] if item["property_id"] == name)


def test_workspace_discovery_needs_no_manifest_and_does_not_join_evidence(tmp_path: Path) -> None:
    write(tmp_path / "repository" / "operation.json", {"private_example": "synthetic"})
    write(tmp_path / "capture.json", {"status": "unknown"})
    write(tmp_path / ".git" / "ignored.json", {})

    result = discover(tmp_path)

    assert [item["path"] for item in result["files"]] == ["capture.json", "repository/operation.json"]
    assert result["evaluated"] is False
    assert result["truncated"] is False
    assert "synthetic" not in json.dumps(result)


def test_discovery_reports_explicit_bounds_and_does_not_follow_links(tmp_path: Path) -> None:
    write(tmp_path / "a.json", {})
    write(tmp_path / "b.json", {})
    write(tmp_path / "deep" / "c.json", {})
    (tmp_path / "linked.json").symlink_to(tmp_path / "a.json")

    bounded = discover(tmp_path, max_files=1)
    assert bounded["truncated"] is True
    assert len(bounded["files"]) == 1
    assert bounded["files"][0]["path"] in {"a.json", "b.json", "deep/c.json"}
    shallow = discover(tmp_path, max_depth=0)
    assert shallow["depth_limited"] is True
    assert shallow["skipped_symlinks"] == ["linked.json"]
    assert [item["path"] for item in shallow["files"]] == ["a.json", "b.json"]


def test_selected_transition_can_pass_while_grant_and_identity_are_unknown(tmp_path: Path) -> None:
    path = write(tmp_path / "selected.json", {"kind": "PUBLISH", "from_state": "CLAIMED", "to_state": "EXECUTING"})
    record = load_selection(tmp_path, [("operation", "selected.json")])

    partial = evaluate(record)
    scoped = evaluate(record, properties=["FVL-LEGAL"])

    assert partial["verdict"] == "UNKNOWN"
    assert finding(partial, "FVL-LEGAL")["status"] == "BOUNDED_PASS"
    assert finding(partial, "FVL-AUTH")["status"] == "UNKNOWN"
    assert scoped["verdict"] == "BOUNDED_PASS"
    assert scoped["requested_properties"] == ["FVL-LEGAL"]
    assert scoped["operation_id"] is None
    assert scoped["source_refs"]["operation"] == {"path": "selected.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    assert scoped["authorizes_production_effect"] is False


def test_partial_observation_detects_a_known_illegal_transition_without_fake_identity() -> None:
    result = evaluate({"operation": {"kind": "PUBLISH", "from_state": "PREPARED", "to_state": "TERMINAL"}}, ["FVL-LEGAL"])
    assert result["verdict"] == "COUNTEREXAMPLE"
    assert result["operation_id"] is None


def test_missing_native_mapping_remains_unknown_instead_of_a_schema_counterexample() -> None:
    result = evaluate({"operation": {"owner_status": "completed", "session_id": "synthetic-native-session"}})
    assert result["verdict"] == "UNKNOWN"
    assert finding(result, "FVL-SCHEMA")["status"] == "UNKNOWN"
    assert "action_seq" not in result


def test_omitted_selection_is_not_evidence_of_an_unsupported_success() -> None:
    operation = {"kind": "PUBLISH", "from_state": "CLAIMED", "to_state": "EXECUTING", "reports_success": True}
    result = evaluate({"operation": operation}, ["FVL-NO-FALSE-SUCCESS"])
    assert result["verdict"] == "UNKNOWN"


def test_unbound_readback_count_is_an_observation_not_a_duplicate_proof() -> None:
    result = evaluate({"provider": {"effect_count": 2, "complete": False}}, ["FVL-NO-DUPLICATE"])
    assert result["verdict"] == "UNKNOWN"
    assert result["observations"] == {"provider_effect_count": 2}


def test_selected_unavailable_property_does_not_vacuously_pass() -> None:
    result = evaluate({"operation": {"kind": "PUBLISH"}}, ["FVL-CHECKPOINT"])
    assert result["verdict"] == "UNKNOWN"
    with pytest.raises(ValueError, match="Select known"):
        evaluate({}, [])


def test_selection_rejects_duplicate_roles_escape_and_symlinks(tmp_path: Path) -> None:
    write(tmp_path / "part.json", {})
    (tmp_path / "linked.json").symlink_to(tmp_path / "part.json")
    with pytest.raises(BundleError, match="Duplicate selected"):
        load_selection(tmp_path, [("operation", "part.json"), ("operation", "part.json")])
    with pytest.raises(BundleError, match="inside"):
        load_selection(tmp_path, [("operation", "../part.json")])
    with pytest.raises(BundleError, match="symlink"):
        load_selection(tmp_path, [("operation", "linked.json")])


def test_cli_discovers_then_evaluates_only_the_explicit_selection(tmp_path: Path, capsys) -> None:
    write(tmp_path / "transition.json", {"kind": "ADVANCE", "from_state": "PREPARED", "to_state": "CLAIMED"})
    assert main(["discover", str(tmp_path)]) == 0
    inventory = json.loads(capsys.readouterr().out)
    assert [item["path"] for item in inventory["files"]] == ["transition.json"]
    assert main(["evaluate", str(tmp_path), "--select", "operation=transition.json", "--property", "FVL-LEGAL"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["verdict"] == "BOUNDED_PASS"
    assert result["selected_parts"] == ["operation"]
    assert main(["evaluate", str(tmp_path), "--select", "operation=transition.json", "--select", "operation=transition.json"]) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "UNKNOWN"


@pytest.mark.parametrize("authorized,expected", [(True, "BOUNDED_PASS"), (False, "COUNTEREXAMPLE"), (None, "UNKNOWN")])
def test_scoped_grant_check_keeps_the_actual_subject_scope_and_order_requirements(authorized, expected) -> None:
    result = evaluate({
        "operation": {"kind": "PUBLISH", "operation_id": "synthetic-op", "session_id": "synthetic-session", "action_seq": 5},
        "authority": {"operation_id": "synthetic-op", "session_id": "synthetic-session", "authorized": authorized,
                      "allowed_kinds": ["PUBLISH"], "epoch": 1, "seq": 4},
    }, ["FVL-AUTH"])
    assert result["verdict"] == expected
    assert result["authorizes_production_effect"] is False


def test_frozen_bundle_cannot_disable_digest_validation_with_null(tmp_path: Path) -> None:
    import shutil
    from formal_verification_lab.bundles import load_bundle
    source = Path(__file__).parents[1] / "fixtures/cases/publish_valid"
    shutil.copytree(source, tmp_path / "case")
    manifest = json.loads((tmp_path / "case/manifest.json").read_text())
    manifest["files"]["operation"]["sha256"] = None
    (tmp_path / "case/manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(BundleError, match="Invalid entry digest"):
        load_bundle(tmp_path / "case")


@pytest.mark.parametrize("property_id", ["FVL-IDEMPOTENCY", "FVL-NO-DUPLICATE", "FVL-EFFECT-RECEIPT", "FVL-TERMINAL"])
def test_effect_property_does_not_accept_a_foreign_operation_readback(property_id: str) -> None:
    from formal_verification_lab.bundles import load_bundle
    name = "terminal_valid" if property_id == "FVL-TERMINAL" else "publish_valid"
    record = load_bundle(Path(__file__).parents[1] / "fixtures/cases" / name)
    record["provider"]["operation_id"] = "different-synthetic-operation"
    assert evaluate(record, [property_id])["verdict"] != "BOUNDED_PASS"


@pytest.mark.parametrize("property_id", ["FVL-IDEMPOTENCY", "FVL-NO-DUPLICATE"])
def test_bound_duplicate_effect_is_counterexample_even_with_incomplete_ledger(property_id: str) -> None:
    from formal_verification_lab.bundles import load_bundle
    record = load_bundle(Path(__file__).parents[1] / "fixtures/cases/publish_valid")
    assert evaluate(record, [property_id])["verdict"] == "BOUNDED_PASS"
    record["provider"]["complete"] = False
    assert evaluate(record, [property_id])["verdict"] == "UNKNOWN"
    record["provider"]["effect_count"] = 2
    assert evaluate(record, [property_id])["verdict"] == "COUNTEREXAMPLE"


@pytest.mark.parametrize("change,value,expected", [
    (None, None, "BOUNDED_PASS"), ("operation_id", "foreign-operation", "COUNTEREXAMPLE"),
    ("idempotency_key", "foreign-key", "COUNTEREXAMPLE"), ("observed_seq", 13, "COUNTEREXAMPLE"),
    ("complete", False, "UNKNOWN"), ("effect_count", None, "UNKNOWN"),
])
def test_retry_checks_its_own_subject_key_order_and_complete_no_effect_scope(change, value, expected) -> None:
    from formal_verification_lab.bundles import load_bundle
    record = load_bundle(Path(__file__).parents[1] / "fixtures/cases/retry_reconciled")
    if change is not None:
        record["provider"][change] = value
    assert evaluate(record, ["FVL-RETRY"])["verdict"] == expected


@pytest.mark.parametrize("property_id", ["FVL-FRESH", "FVL-CHECKPOINT"])
def test_source_evidence_binding_is_required_inside_selected_property(property_id: str) -> None:
    from formal_verification_lab.bundles import load_bundle
    name = "resume_checkpoint" if property_id == "FVL-CHECKPOINT" else "publish_valid"
    record = load_bundle(Path(__file__).parents[1] / "fixtures/cases" / name)
    assert evaluate(record, [property_id])["verdict"] == "BOUNDED_PASS"
    record["evidence"]["session_id"] = "foreign-session"
    assert evaluate(record, [property_id])["verdict"] != "BOUNDED_PASS"


@pytest.mark.parametrize("part,missing", [("evidence", "digest"), ("authority", "session_id")])
def test_selected_freshness_missing_binding_data_is_unknown(part: str, missing: str) -> None:
    from formal_verification_lab.bundles import load_bundle
    record = load_bundle(Path(__file__).parents[1] / "fixtures/cases/publish_valid")
    del record[part][missing]
    assert evaluate(record, ["FVL-FRESH"])["verdict"] == "UNKNOWN"


def test_retry_missing_prior_order_is_unknown() -> None:
    from formal_verification_lab.bundles import load_bundle
    record = load_bundle(Path(__file__).parents[1] / "fixtures/cases/retry_reconciled")
    del record["operation"]["prior_attempt_seq"]
    assert evaluate(record, ["FVL-RETRY"])["verdict"] == "UNKNOWN"



def test_discovery_entry_budget_includes_nonmatching_files(tmp_path: Path) -> None:
    for index in range(5):
        (tmp_path / f"file{index}.txt").write_text("synthetic", encoding="utf-8")
    result = discover(tmp_path, pattern="*.json", max_entries=2)
    assert result["files"] == []
    assert result["scanned_entries"] == 2
    assert result["truncated"] is True
    assert result["truncation_reason"] == "MAX_ENTRIES"



def test_malformed_selected_part_does_not_block_an_independent_property(tmp_path: Path) -> None:
    write(tmp_path / "operation.json", {"kind": "ADVANCE", "from_state": "PREPARED", "to_state": "CLAIMED"})
    (tmp_path / "authority.json").write_text("not JSON", encoding="utf-8")
    record = load_selection(tmp_path, [("operation", "operation.json"), ("authority", "authority.json")])
    assert evaluate(record, ["FVL-LEGAL"])["verdict"] == "BOUNDED_PASS"
    result = evaluate(record, ["FVL-AUTH"])
    assert result["verdict"] == "UNKNOWN"
    assert result["selection_errors"][0]["role"] == "authority"
    assert "error" in result["selection_errors"][0]


def test_missing_selected_part_retains_a_named_unknown(tmp_path: Path) -> None:
    record = load_selection(tmp_path, [("provider", "absent.json")])
    result = evaluate(record, ["FVL-NO-DUPLICATE"])
    assert result["verdict"] == "UNKNOWN"
    assert result["requested_parts"] == ["provider"]
    assert result["selection_errors"][0]["path"] == "absent.json"


@pytest.mark.parametrize("grant_seq,expected", [(None, "UNKNOWN"), (50, "COUNTEREXAMPLE")])
def test_selected_freshness_needs_grant_order_not_just_a_matching_epoch(grant_seq, expected) -> None:
    from formal_verification_lab.bundles import load_bundle
    record = load_bundle(Path(__file__).parents[1] / "fixtures/cases/publish_valid")
    record["authority"]["seq"] = grant_seq
    assert evaluate(record, ["FVL-FRESH"])["verdict"] == expected
