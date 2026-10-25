from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from formal_verification_lab.cli import main
from formal_verification_lab.mapping import measure_mapping


def write(root: Path, name: str, value: dict) -> dict:
    raw = json.dumps(value).encode()
    (root / name).write_bytes(raw)
    return {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}


def study(root: Path, expected: list[dict], observed: list[dict]) -> dict:
    packet = {"schema": "fvl.mapping.v1", "scope": "Literal synthetic locations only", "revision": "synthetic-1",
              "expected_origin": "Independent literal requirement: a at source.py line3, b at line9",
              "expected": write(root, "expected.json", {"rows": expected}),
              "observed": write(root, "observed.json", {"rows": observed})}
    write(root, "study.json", packet)
    return packet


def test_wrong_location_is_both_false_positive_and_recall_miss_and_unknown_never_disappears(tmp_path: Path) -> None:
    study(tmp_path, [{"id": "a", "path": "source.py", "line": 3}, {"id": "b", "path": "source.py", "line": 9},
                     {"id": "c", "path": "source.py", "line": 12}, {"id": "d", "path": "source.py", "line": 18}],
          [{"id": "a", "path": "source.py", "line": 3}, {"id": "b", "path": "source.py", "line": 8},
           {"id": "c", "status": "unknown"}, {"id": "extra", "path": "source.py", "line": 99}])
    result = measure_mapping(tmp_path, "study.json")
    assert (result["tp"], result["fp"], result["fn"]) == (1, 2, 3)
    assert result["precision"] == 1 / 3
    assert result["recall"] == 0.25
    assert result["coverage"] == 0.5
    assert result["unknown"] == ["c"] and result["missing"] == ["d"]
    assert result["wrong"] == ["b"] and result["extra"] == ["extra"]
    assert result["target_met_supplied_population"] is False


@pytest.mark.parametrize("misses,met", [(0, True), (1, False), (2, False)])
def test_strict_threshold_and_abstention_does_not_game_precision(tmp_path: Path, misses: int, met: bool) -> None:
    expected = [{"id": str(i), "path": "literal.py", "line": i + 1} for i in range(100)]
    observed = [row if i >= misses else {"id": row["id"], "status": "unknown"} for i, row in enumerate(expected)]
    study(tmp_path, expected, observed)
    result = measure_mapping(tmp_path, "study.json")
    assert result["precision"] == 1
    assert result["target_met_supplied_population"] is met
    assert result["fn"] == misses


def test_empty_population_is_not_vacuous_pass_and_query_success_is_not_target_pass(tmp_path: Path, capsys) -> None:
    study(tmp_path, [], [])
    assert main(["mapping", str(tmp_path), "--study", "study.json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["precision"] is None and result["recall"] is None
    assert result["target_met_supplied_population"] is False
    assert result["ground_truth_review"] == "SESSION_REQUIRED"
    assert result["retention_value"] == result["native_conformance"] == "NOT_EVALUATED"


@pytest.mark.parametrize("fault", ["duplicate", "duplicate_part", "bool_line", "unknown_truth", "drift", "escape"])
def test_invalid_or_drifted_mapping_is_refused(tmp_path: Path, capsys, fault: str) -> None:
    row = {"id": "a", "path": "source.py", "line": 3}
    packet = study(tmp_path, [row], [row])
    if fault == "duplicate":
        packet["observed"] = write(tmp_path, "observed.json", {"rows": [row, row]})
    elif fault == "duplicate_part":
        packet["observed"] = [packet["observed"], packet["observed"]]
    elif fault == "bool_line":
        packet["observed"] = write(tmp_path, "observed.json", {"rows": [{**row, "line": True}]})
    elif fault == "unknown_truth":
        packet["expected"] = write(tmp_path, "expected.json", {"rows": [{"id": "a", "status": "unknown"}]})
    elif fault == "drift":
        (tmp_path / "observed.json").write_text("{}")
    else:
        packet["observed"]["path"] = "../observed.json"
    write(tmp_path, "study.json", packet)
    assert main(["mapping", str(tmp_path), "--study", "study.json"]) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "UNKNOWN"
