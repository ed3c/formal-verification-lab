from __future__ import annotations

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts/p3"))
import run
import validate
import verify_sources


class _AllowedSocket:
    def bind(self, address: tuple[str, int]) -> None:
        assert address == ("127.0.0.1", 0)

    def getsockname(self) -> tuple[str, int]:
        return ("127.0.0.1", 49152)

    def close(self) -> None:
        return None


class _DeniedSocket:
    def bind(self, address: tuple[str, int]) -> None:
        raise PermissionError(13, "operation not permitted")

    def close(self) -> None:
        return None


def test_select_server_endpoint_uses_a_fresh_ephemeral_port(monkeypatch) -> None:
    monkeypatch.setattr(run.socket, "socket", lambda *args: _AllowedSocket())

    selection = run.select_server_endpoint()

    assert selection.status == "AVAILABLE"
    assert selection.endpoint == "127.0.0.1:49152"
    assert selection.endpoint != "127.0.0.1:8822"


def test_select_server_endpoint_reports_permission_denial(monkeypatch) -> None:
    monkeypatch.setattr(run.socket, "socket", lambda *args: _DeniedSocket())

    selection = run.select_server_endpoint()

    assert selection.status == "NOT_AVAILABLE"
    assert selection.endpoint is None
    assert selection.diagnostic == "PermissionError: [Errno 13] operation not permitted"


def test_input_manifest_rejects_source_change_between_command_records(tmp_path: Path) -> None:
    model = tmp_path / "model.qnt"
    model.write_text("stable", encoding="utf-8")
    common = run.input_digests((model,))
    (tmp_path / "input-manifest.json").write_text(
        json.dumps({"schema": "fvl.p3-input-manifest.v1", "digests": common}),
        encoding="utf-8",
    )
    first = tmp_path / "runs" / "first"
    second = tmp_path / "runs" / "second"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / "result.json").write_text(
        json.dumps({"input_digests_before": common, "input_digests_after": common}),
        encoding="utf-8",
    )
    model.write_text("changed", encoding="utf-8")
    changed = run.input_digests((model,))
    (second / "result.json").write_text(
        json.dumps({"input_digests_before": changed, "input_digests_after": changed}),
        encoding="utf-8",
    )

    try:
        validate.validate_input_manifests(tmp_path)
    except ValueError as exc:
        assert "input manifest mismatch before execution" in str(exc)
    else:
        raise AssertionError("source drift between command records was accepted")


def test_removed_duplicate_symlink_is_not_reported_as_absent(tmp_path: Path) -> None:
    operation = tmp_path / "scripts/p3/models/operation.qnt"
    operation.parent.mkdir(parents=True)
    target = tmp_path / "target.qnt"
    target.write_text("duplicate", encoding="utf-8")
    operation.symlink_to(target)
    canary = tmp_path / "scripts/p3/models/canary.qnt"
    canary.symlink_to(target)

    mismatches, absent = verify_sources.verify_removed_duplicates(tmp_path)

    assert "scripts/p3/models/operation.qnt: duplicate model must be absent" in mismatches
    assert "scripts/p3/models/operation.qnt" not in absent
    assert "scripts/p3/models/canary.qnt: duplicate model must be absent" in mismatches
    assert "scripts/p3/models/canary.qnt" not in absent


def test_current_source_readback_rejects_digest_drift() -> None:
    source = verify_sources.verify()
    current = source["current_inputs"]
    manifest = {
        "schema": "fvl.p3-input-manifest.v1",
        "digests": dict(current),
        "source_inputs": list(current),
    }
    changed = {**source, "current_inputs": {**current, next(iter(current)): "0" * 64}}

    try:
        validate.validate_source_readback(changed, manifest)
    except ValueError as exc:
        assert "current source digest differs" in str(exc)
    else:
        raise AssertionError("current source drift was accepted")


def test_removed_duplicate_regular_file_is_rejected(tmp_path: Path) -> None:
    duplicate = tmp_path / "scripts/p3/models/operation.qnt"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text("duplicate", encoding="utf-8")

    mismatches, absent = verify_sources.verify_removed_duplicates(tmp_path)

    assert "scripts/p3/models/operation.qnt: duplicate model must be absent" in mismatches
    assert "scripts/p3/models/operation.qnt" not in absent


def test_p3_queries_retain_bounds_canary_reachability_and_induction() -> None:
    queries = {query.name: query for query in run.QUERIES}

    assert queries["bounded"].flags == ("--invariant=safety", "--max-steps=12")
    assert queries["canary"].flags == (
        "--invariant=unauthorizedEffectIsImpossible",
        "--max-steps=2",
    )
    assert queries["terminal"].flags == (
        "--invariant=terminalUnreachable",
        "--max-steps=12",
    )
    assert queries["reconciliation"].flags == (
        "--invariant=reconciliationUnreachable",
        "--max-steps=12",
    )
    assert queries["typed-inductive"].flags == (
        "--inductive-invariant=IndInv",
        "--invariant=safety",
    )
