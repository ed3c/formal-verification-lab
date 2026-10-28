"""Read-only evidence discovery and selection; hashes establish byte consistency."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

PARTS = ("operation", "authority", "evidence", "preflight", "provider")
MAX_PART_BYTES = 256_000


class BundleError(ValueError):
    pass


class SelectionPathError(BundleError):
    pass


def _directory(folder: str | Path) -> Path:
    path = Path(folder)
    if path.is_symlink():
        raise BundleError("Symlink directories denied")
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise BundleError("Evidence root must be a real directory")
    return root


def _part(root: Path, name: str, expected_digest: str | None = None) -> tuple[Any, dict[str, str]]:
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise SelectionPathError("Only paths inside the selected evidence root are allowed")
    path = root
    for component in relative.parts:
        path = path / component
        if path.is_symlink():
            raise SelectionPathError("Selected evidence symlink denied")
    if not path.is_file():
        raise BundleError("Missing selected evidence file: " + name)
    if path.stat().st_size > MAX_PART_BYTES:
        raise BundleError("Oversized bundle part")
    with path.open("rb") as source:
        payload = source.read(MAX_PART_BYTES + 1)
    if len(payload) > MAX_PART_BYTES:
        raise BundleError("Oversized bundle part")
    actual = hashlib.sha256(payload).hexdigest()
    if expected_digest is not None and actual != expected_digest:
        raise BundleError("Bundle part hash mismatch: " + name)
    value = json.loads(payload)
    if value is not None and not isinstance(value, dict):
        raise BundleError("Part must be an object or null")
    return value, {"path": relative.as_posix(), "sha256": actual}


def load_selection(folder: str | Path, selections: Iterable[tuple[str, str]]) -> dict[str, Any]:
    """Load explicitly selected normalized parts without requiring a full bundle."""
    root = _directory(folder)
    data: dict[str, Any] = {"provenance": "selected_offline", "source_refs": {}, "selection_errors": []}
    requested = set()
    for part, name in selections:
        if part not in PARTS:
            raise BundleError("Unknown evidence role: " + part)
        if part in requested:
            raise BundleError("Duplicate selected evidence role: " + part)
        requested.add(part)
        try:
            data[part], data["source_refs"][part] = _part(root, name)
        except SelectionPathError:
            raise
        except (OSError, ValueError) as error:
            data["selection_errors"].append({"role": part, "path": name, "error": str(error)})
    if not requested:
        raise BundleError("Select at least one evidence part")
    data["requested_parts"] = [part for part in PARTS if part in requested]
    data["selected_parts"] = [part for part in PARTS if part in data["source_refs"]]
    data["missing_parts"] = [part for part in PARTS if part not in data["source_refs"]]
    return data


def load_bundle(folder: str | Path) -> dict[str, Any]:
    root = _directory(folder)
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink():
        raise BundleError("Symlink manifests denied")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise BundleError("Manifest must be an object")
    if manifest.get("schema") != "fvl.bundle.v1" or manifest.get("provenance") not in ("synthetic", "owner_export"):
        raise BundleError("Unrecognized manifest schema/provenance")
    entries = manifest.get("files")
    if not isinstance(entries, dict) or set(entries) != set(PARTS):
        raise BundleError("Exactly five inputs must be declared in a v1 bundle; use explicit selection for partial evidence")
    data: dict[str, Any] = {"provenance": manifest["provenance"], "source_refs": {}}
    for part in PARTS:
        entry = entries[part]
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise BundleError("Invalid entry")
        name = entry["path"]
        if not isinstance(name, str) or name != part + ".json":
            raise BundleError("Only canonical local data file names are allowed")
        digest = entry["sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise BundleError("Invalid entry digest")
        data[part], data["source_refs"][part] = _part(root, name, digest)
    return data


def discover(folder: str | Path, pattern: str = "*.json", max_depth: int = 4,
             max_files: int = 200, max_entries: int = 10_000) -> dict[str, Any]:
    """Find local candidates within explicit depth, entry and matching-file bounds."""
    root = _directory(folder)
    if not pattern or "/" in pattern or "\\" in pattern:
        raise BundleError("Discovery pattern must match a file name")
    if not 0 <= max_depth <= 64 or not 1 <= max_files <= 10_000 or not 1 <= max_entries <= 100_000:
        raise BundleError("Discovery bounds must be depth 0..64, files 1..10000 and entries 1..100000")
    files: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    skipped_links: list[str] = []
    pending = [(root, 0)]
    scanned_entries = 0
    depth_limited = False
    truncation = None
    while pending and truncation is None:
        here, depth = pending.pop()
        children = []
        try:
            with os.scandir(here) as entries:
                for entry in entries:
                    if scanned_entries == max_entries:
                        truncation = "MAX_ENTRIES"
                        break
                    scanned_entries += 1
                    path = Path(entry.path)
                    relative = path.relative_to(root).as_posix()
                    try:
                        if entry.is_symlink():
                            skipped_links.append(relative)
                        elif entry.is_dir(follow_symlinks=False):
                            if entry.name not in {".git", ".venv", "node_modules", "__pycache__"}:
                                if depth == max_depth:
                                    depth_limited = True
                                else:
                                    children.append((path, depth + 1))
                        elif entry.is_file(follow_symlinks=False) and fnmatch.fnmatchcase(entry.name, pattern):
                            if len(files) == max_files:
                                truncation = "MAX_MATCHES"
                                break
                            files.append({"path": relative, "bytes": entry.stat(follow_symlinks=False).st_size,
                                          "role_hint": path.stem if path.stem in PARTS else None})
                    except OSError as error:
                        errors.append({"path": relative, "error": str(error)})
        except OSError as error:
            errors.append({"path": str(here), "error": str(error)})
        pending.extend(sorted(children, reverse=True))
    return {"schema": "fvl.discovery.v1", "status": "OBSERVED", "root": str(root),
            "repository_marker_present": (root / ".git").exists(), "pattern": pattern,
            "max_depth": max_depth, "max_files": max_files, "max_entries": max_entries,
            "scanned_entries": scanned_entries, "files": sorted(files, key=lambda item: item["path"]),
            "truncated": truncation is not None, "truncation_reason": truncation, "depth_limited": depth_limited,
            "skipped_symlinks": sorted(skipped_links), "scan_errors": errors,
            "evaluated": False, "authorizes_production_effect": False}
