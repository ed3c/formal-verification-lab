from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from formal_verification_lab.blind_outcome import (
    ContractError, OutcomeError, PacketError, build_primary_packet, canonical_bytes, validate,
)


@pytest.fixture
def contract() -> dict:
    return {"schema": 1, "artifact_keys": ["schema", "answers"],
            "answer_keys": ["id", "value", "evidence"],
            "evidence_ids": [f"G{i}" for i in range(1, 9)],
            "cases": {"SYNTHETIC": ["integer", "boolean", ["MATCH", "DRIFT"], "boolean",
                                     ["UNKNOWN", "COMPLETE", "INCOMPLETE"], "boolean",
                                     ["UNKNOWN", "COMPLETE", "INCOMPLETE"], "boolean"]}}


@pytest.fixture
def artifact() -> dict:
    values = [1, True, "MATCH", False, "UNKNOWN", False, "UNKNOWN", False]
    return {"schema": 1, "answers": [{"id": f"Q{i}", "value": value, "evidence": f"G{i}"}
                                     for i, value in enumerate(values, 1)]}


def cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", "-m", "formal_verification_lab.blind_outcome", *args],
                          cwd=Path(__file__).parents[1], capture_output=True, timeout=10, check=False)


def test_valid_shape_retains_exact_typed_values_without_a_truth_score(contract: dict, artifact: dict) -> None:
    result = validate("SYNTHETIC", json.dumps(artifact).encode(), contract)
    assert result == artifact
    assert set(result) == {"schema", "answers"}
    assert type(result["answers"][0]["value"]) is int
    assert type(result["answers"][1]["value"]) is bool


def test_format_valid_wrong_success_and_wrong_evidence_are_not_cleaned(contract: dict, artifact: dict) -> None:
    artifact["answers"][6]["value"] = "COMPLETE"
    artifact["answers"][6]["evidence"] = "G1"
    assert validate("SYNTHETIC", json.dumps(artifact).encode(), contract) == artifact
    assert artifact["answers"][6] == {"id": "Q7", "value": "COMPLETE", "evidence": "G1"}


def test_unknown_and_incomplete_remain_different(contract: dict, artifact: dict) -> None:
    unknown = validate("SYNTHETIC", json.dumps(artifact).encode(), contract)
    artifact["answers"][6]["value"] = "INCOMPLETE"
    incomplete = validate("SYNTHETIC", json.dumps(artifact).encode(), contract)
    assert unknown["answers"][6]["value"] == "UNKNOWN"
    assert incomplete["answers"][6]["value"] == "INCOMPLETE"
    assert unknown != incomplete


@pytest.mark.parametrize("field, value", [("schema", True), ("schema", 1.0), ("integer", True), ("integer", 1.0),
                                           ("integer", -1), ("integer", 513), ("boolean", 1), ("boolean", "true")])
def test_schema_integer_and_boolean_confusion_is_rejected(contract: dict, artifact: dict, field: str, value) -> None:
    if field == "schema":
        artifact["schema"] = value
    else:
        artifact["answers"][0 if field == "integer" else 1]["value"] = value
    with pytest.raises(OutcomeError):
        validate("SYNTHETIC", json.dumps(artifact).encode(), contract)


@pytest.mark.parametrize("value", [0, 512])
def test_integer_endpoints_are_retained(contract: dict, artifact: dict, value: int) -> None:
    artifact["answers"][0]["value"] = value
    assert validate("SYNTHETIC", json.dumps(artifact).encode(), contract)["answers"][0]["value"] == value


def test_duplicate_json_keys_are_rejected(contract: dict, artifact: dict) -> None:
    raw = json.dumps(artifact).encode().replace(b'"schema": 1', b'"schema": 1, "schema": 1', 1)
    with pytest.raises(OutcomeError, match="DUPLICATE_KEY"):
        validate("SYNTHETIC", raw, contract)


def test_duplicate_question_ids_are_rejected(contract: dict, artifact: dict) -> None:
    artifact["answers"][1]["id"] = "Q1"
    with pytest.raises(OutcomeError, match="DUPLICATE_ID"):
        validate("SYNTHETIC", json.dumps(artifact).encode(), contract)


@pytest.mark.parametrize("literal", [b"NaN", b"Infinity", b"-Infinity", b"1e9999"])
def test_nonfinite_numbers_are_rejected(contract: dict, artifact: dict, literal: bytes) -> None:
    raw = json.dumps(artifact).encode().replace(b'"value": 1', b'"value": ' + literal, 1)
    with pytest.raises(OutcomeError, match="NON_FINITE"):
        validate("SYNTHETIC", raw, contract)


@pytest.mark.parametrize("mutation", ["method", "path", "narrative", "answer_method", "answer_path", "free_value", "path_value", "path_evidence"])
def test_method_paths_and_unclosed_text_are_rejected(contract: dict, artifact: dict, mutation: str) -> None:
    if mutation in {"method", "path", "narrative"}:
        artifact[mutation] = "SYNTHETIC_METHOD"
    elif mutation in {"answer_method", "answer_path"}:
        artifact["answers"][0][mutation] = "/synthetic/source"
    elif mutation == "path_evidence":
        artifact["answers"][0]["evidence"] = "/synthetic/source"
    else:
        artifact["answers"][4]["value"] = "/synthetic/source" if mutation == "path_value" else "SYNTHETIC free narrative"
    with pytest.raises(OutcomeError):
        validate("SYNTHETIC", json.dumps(artifact).encode(), contract)


def test_neutral_packet_has_only_fixed_shape_and_canonical_order(contract: dict, artifact: dict) -> None:
    artifact["answers"].reverse()
    entries = [(f"R{i:02}", "SYNTHETIC", json.dumps(artifact).encode()) for i in range(8, 0, -1)]
    packet = build_primary_packet(entries, contract)
    assert set(packet) == {"schema", "rows"}
    assert [row["label"] for row in packet["rows"]] == [f"R{i:02}" for i in range(1, 9)]
    for row in packet["rows"]:
        assert set(row) == {"label", "case", "outcome"}
        assert row["case"] == "SYNTHETIC"
        assert set(row["outcome"]) == {"status", "artifact"}
        assert row["outcome"]["status"] == "VALID_OUTPUT"
        assert [item["id"] for item in row["outcome"]["artifact"]["answers"]] == [f"Q{i}" for i in range(1, 9)]
    assert canonical_bytes(packet) == canonical_bytes(build_primary_packet(list(reversed(entries)), contract))


@pytest.mark.parametrize("mutation", ["short", "duplicate", "foreign_label", "metadata", "list_entry", "metadata_object"])
def test_packet_refuses_missing_labels_and_metadata_entries(contract: dict, artifact: dict, mutation: str) -> None:
    raw = json.dumps(artifact).encode()
    entries = [(f"R{i:02}", "SYNTHETIC", raw) for i in range(1, 9)]
    if mutation == "short":
        entries.pop()
    elif mutation == "duplicate":
        entries[1] = entries[0]
    elif mutation == "foreign_label":
        entries[0] = ("SYNTHETIC_METHOD", "SYNTHETIC", raw)
    elif mutation == "metadata":
        entries[0] = (*entries[0], {"method": "SYNTHETIC_METHOD"})
    elif mutation == "list_entry":
        entries[0] = list(entries[0])
    else:
        entries[0] = {"label": "R01", "case": "SYNTHETIC", "raw": raw, "method": "SYNTHETIC_METHOD"}
    with pytest.raises(PacketError):
        build_primary_packet(entries, contract)


def test_canonicalization_only_changes_format_and_key_or_question_order(contract: dict, artifact: dict) -> None:
    shuffled = {"answers": list(reversed(artifact["answers"])), "schema": 1}
    first = canonical_bytes(validate("SYNTHETIC", json.dumps(artifact, indent=4).encode(), contract))
    second = canonical_bytes(validate("SYNTHETIC", json.dumps(shuffled, separators=(",", ":")).encode(), contract))
    assert first == second
    assert first.endswith(b"\n") and not first.endswith(b"\n\n")
    assert json.loads(first) == artifact


def test_unknown_case_does_not_become_invalid_output(contract: dict, artifact: dict) -> None:
    with pytest.raises(ContractError, match="unknown case"):
        build_primary_packet([("R01", "SYNTHETIC_UNKNOWN", json.dumps(artifact).encode())] + [
            (f"R{i:02}", "SYNTHETIC", json.dumps(artifact).encode()) for i in range(2, 9)], contract)


def test_actual_validate_cli_retains_a_valid_wrong_value(contract: dict, artifact: dict, tmp_path: Path) -> None:
    artifact["answers"][6]["value"] = "COMPLETE"
    contract_path = tmp_path / "synthetic-contract.json"
    input_path = tmp_path / "synthetic-outcome.json"
    contract_path.write_text(json.dumps(contract))
    input_path.write_text(json.dumps(artifact))
    result = cli("validate", "--contract", str(contract_path), "--case", "SYNTHETIC", "--input", str(input_path))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == artifact
    assert set(json.loads(result.stdout)) == {"schema", "answers"}


def test_actual_packet_cli_preserves_invalid_raw_and_keeps_ledger_away_from_primary(contract: dict, artifact: dict, tmp_path: Path) -> None:
    contract_path = tmp_path / "synthetic-contract.json"
    contract_path.write_text(json.dumps(contract))
    manifest_path = tmp_path / "synthetic-manifest.json"
    invalid = b'{"schema":1,"method":"SYNTHETIC_METHOD","narrative":"SYNTHETIC_NOTE"}\n'
    valid = json.dumps(artifact).encode()
    entries = []
    for i in range(1, 9):
        name = f"synthetic-{i}.json"
        (tmp_path / name).write_bytes(invalid if i == 1 else valid)
        entries.append({"label": f"R{i:02}", "case": "SYNTHETIC", "path": name})
    manifest_path.write_text(json.dumps({"schema": 1, "entries": entries}))
    output = tmp_path / "packet"
    result = cli("packet", "--contract", str(contract_path), "--manifest", str(manifest_path), "--output", str(output))
    assert result.returncode == 0, result.stderr
    primary_bytes = (output / "primary.json").read_bytes()
    primary = json.loads(primary_bytes)
    assert primary["rows"][0] == {"label": "R01", "case": "SYNTHETIC", "outcome": {"status": "INVALID_OUTPUT", "artifact": None}}
    assert b"SYNTHETIC_METHOD" not in primary_bytes and b"SYNTHETIC_NOTE" not in primary_bytes
    assert b"validation" not in primary_bytes and b"source" not in primary_bytes and b"sha256" not in primary_bytes
    assert (output / "raw/R01.bin").read_bytes() == invalid
    assert (output / "raw/R02.bin").read_bytes() == valid
    assert (output / "raw/R01.bin").stat().st_mode & 0o777 == 0o600
    ledger = json.loads((output / "ledger.json").read_bytes())["entries"]
    assert ledger[0]["sha256"] == hashlib.sha256(invalid).hexdigest()
    assert ledger[0]["bytes"] == len(invalid)
    assert ledger[0]["validation"]["status"] == "INVALID_OUTPUT"
    assert ledger[1]["validation"] == {"status": "VALID_OUTPUT", "scoring": "NOT_SCORED"}
    before = {str(p.relative_to(output)): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    repeated = cli("packet", "--contract", str(contract_path), "--manifest", str(manifest_path), "--output", str(output))
    assert repeated.returncode == 2
    assert {str(p.relative_to(output)): p.read_bytes() for p in output.rglob("*") if p.is_file()} == before


def test_packet_cli_rejects_manifest_metadata_without_creating_output(contract: dict, artifact: dict, tmp_path: Path) -> None:
    contract_path = tmp_path / "synthetic-contract.json"
    contract_path.write_text(json.dumps(contract))
    source = tmp_path / "synthetic.json"
    source.write_text(json.dumps(artifact))
    entries = [{"label": f"R{i:02}", "case": "SYNTHETIC", "path": str(source)} for i in range(1, 9)]
    entries[0]["method"] = "SYNTHETIC_METHOD"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema": 1, "entries": entries}))
    output = tmp_path / "not-created"
    result = cli("packet", "--contract", str(contract_path), "--manifest", str(manifest), "--output", str(output))
    assert result.returncode == 2
    assert b"requires only label/case/path" in result.stderr
    assert not output.exists()
