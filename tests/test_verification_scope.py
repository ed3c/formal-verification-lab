from __future__ import annotations

import json
import ast
from pathlib import Path
import subprocess
import sys

import pytest


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import p4


def test_p4_literal_controls_have_exact_non_vacuous_case_counts() -> None:
    controls = p4.literal_controls()

    assert len(controls["effect_cases"]) == 32
    assert len(controls["receipt_cases"]) == 24
    assert controls["always_false_canary_counterexample"] == {
        "input": (True, True, True, True, False),
        "expected": True,
        "actual": False,
    }


def test_p4_result_rejects_a_non_counterexample_canary(tmp_path: Path) -> None:
    for name in ("crosshair", "canary", "hypothesis", "controls"):
        run_dir = tmp_path / "runs" / name
        run_dir.mkdir(parents=True)
        (run_dir / "stdout.txt").write_text("", encoding="utf-8")
        (run_dir / "stderr.txt").write_text("", encoding="utf-8")
    (tmp_path / "runs/crosshair/stdout.txt").write_text(
        "Confirmed over all paths.\nConfirmed over all paths.\n", encoding="utf-8"
    )
    (tmp_path / "runs/hypothesis/stdout.txt").write_text("2 passed\n", encoding="utf-8")
    (tmp_path / "runs/controls/stdout.txt").write_text(
        json.dumps(
            {
                "effect_cases": [{}] * 32,
                "receipt_cases": [{}] * 24,
                "always_false_canary_counterexample": {
                    "input": [True, True, True, True, False],
                    "expected": True,
                    "actual": False,
                },
            }
        ),
        encoding="utf-8",
    )
    results = {
        name: {
            "exit_code": 1 if name == "canary" else 0,
            "timed_out": False,
            "process_error": None,
            "inputs_unchanged": True,
        }
        for name in ("crosshair", "canary", "hypothesis", "controls")
    }

    with pytest.raises(p4.P4Error, match="unsafe canary diagnostic is missing"):
        p4.validate_results(tmp_path, results)


def test_p4_runner_targets_only_the_pure_contract_module() -> None:
    source = (p4.ROOT / "scripts/p4.py").read_text(encoding="utf-8")

    assert '"src/formal_verification_lab/formal_contracts.py"' in source
    assert "formal_verification_lab/kernel.py" not in source
    assert "import requests" not in source
    assert "import urllib" not in source
    assert "import socket" not in source
    assert not any(isinstance(node, ast.Assert) for node in ast.walk(ast.parse(source)))


def test_p4_missing_pinned_environment_is_diagnostic_not_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        p4,
        "package_versions",
        lambda: {
            "python": "3.13.1",
            "python_executable": sys.executable,
            "platform": "test",
            "expected": {"crosshair-tool": "0.0.112"},
            "observed": {},
            "missing": ["crosshair-tool"],
            "mismatches": [],
        },
    )
    evidence = tmp_path / "p4-not-run"

    assert p4.run(evidence) == 2
    summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "NOT_RUN"
    assert summary["reason"] == "PINNED_ENVIRONMENT_UNAVAILABLE"


def test_p4_cli_rejects_existing_evidence_without_changing_files(tmp_path: Path) -> None:
    evidence = tmp_path / "existing-evidence"
    evidence.mkdir()
    (evidence / "summary.json").write_bytes(b'{"status":"BOUNDED_PASS"}\n')
    (evidence / "sentinel.bin").write_bytes(b"original evidence\x00\xff")
    before = {path.name: path.read_bytes() for path in evidence.iterdir()}

    result = subprocess.run(
        [sys.executable, str(p4.ROOT / "scripts/p4.py"), "--evidence-dir", str(evidence)],
        cwd=p4.ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 1
    error = json.loads(result.stdout)
    assert error["status"] == "NOT_VERIFIED"
    assert error["error"] == f"evidence directory already exists: {evidence}"
    assert {path.name: path.read_bytes() for path in evidence.iterdir()} == before
