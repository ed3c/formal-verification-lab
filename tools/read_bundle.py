"""Read declared local JSON selections without granting effect authority."""
from __future__ import annotations

import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
from dataclasses import dataclass
from typing import Any


class InputError(ValueError):
    pass


@dataclass(frozen=True)
class FileSpec:
    id: str
    path: Path
    sha256: str


@dataclass(frozen=True)
class Selector:
    id: str
    file: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class Bundle:
    files: tuple[FileSpec, ...]
    selectors: tuple[Selector, ...]
    max_output_bytes: int


def _invalid_constant(value: str) -> None:
    raise ValueError("Non-finite JSON number")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite JSON number")
    return number


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _json(payload: bytes) -> Any:
    value = json.loads(payload.decode("utf-8"), parse_constant=_invalid_constant,
                       parse_float=_finite_float, object_pairs_hook=_unique_object)
    json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    return value


def _shape(value: Any, keys: set[str], location: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise InputError(location + " has invalid fields")


def _identifier(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise InputError(location + " must be a nonempty string")
    return value


def _path(value: Any, location: str) -> Path:
    if (not isinstance(value, str) or not value.startswith("/") or "\x00" in value
            or value.startswith("//") or os.path.normpath(value) != value):
        raise InputError(location + " must be absolute and resolved")
    return Path(value)


def _open(path: Path, directory: bool = False) -> int:
    parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        parts = path.parts[1:]
        for index, part in enumerate(parts):
            info = os.stat(part, dir_fd=parent, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                raise InputError("Symlink path denied")
            is_directory = directory or index < len(parts) - 1
            if not is_directory and not stat.S_ISREG(info.st_mode):
                raise OSError(errno.EACCES, "Not a regular file")
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if is_directory:
                flags |= os.O_DIRECTORY
            child = os.open(part, flags, dir_fd=parent)
            os.close(parent)
            parent = child
        if not directory and not stat.S_ISREG(os.fstat(parent).st_mode):
            raise OSError(errno.EACCES, "Not a regular file")
        result = parent
        parent = None
        return result
    finally:
        if parent is not None:
            os.close(parent)


def _check_path(path: Path, directory: bool = False) -> None:
    try:
        descriptor = _open(path, directory)
    except OSError:
        return
    os.close(descriptor)


def parse_bundle(value: Any) -> Bundle:
    _shape(value, {"schema", "root", "files", "selectors", "max_output_bytes"}, "bundle")
    if type(value["schema"]) is not int or value["schema"] != 1:
        raise InputError("schema must be 1")
    limit = value["max_output_bytes"]
    if type(limit) is not int or not 1 <= limit <= 65536:
        raise InputError("max_output_bytes must be an integer in 1..65536")
    root = _path(value["root"], "root")
    if not isinstance(value["files"], list) or not isinstance(value["selectors"], list):
        raise InputError("files and selectors must be arrays")
    files = []
    file_ids = set()
    for entry in value["files"]:
        _shape(entry, {"id", "path", "sha256"}, "file")
        identifier = _identifier(entry["id"], "file id")
        if identifier in file_ids:
            raise InputError("Duplicate file id")
        file_ids.add(identifier)
        path = _path(entry["path"], "file path")
        if root != path and root not in path.parents:
            raise InputError("File path escapes root")
        digest = entry["sha256"]
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise InputError("file sha256 must be 64 lowercase hex characters")
        files.append(FileSpec(identifier, path, digest))
    selectors = []
    selector_ids = set()
    for entry in value["selectors"]:
        _shape(entry, {"id", "file", "pointer"}, "selector")
        identifier = _identifier(entry["id"], "selector id")
        if identifier in selector_ids:
            raise InputError("Duplicate selector id")
        selector_ids.add(identifier)
        file_id = _identifier(entry["file"], "selector file")
        if file_id not in file_ids:
            raise InputError("selector file must reference an existing file id")
        pointer = entry["pointer"]
        if (not isinstance(pointer, str) or (pointer and not pointer.startswith("/"))
                or re.search(r"~(?![01])", pointer)):
            raise InputError("Invalid RFC6901 pointer")
        tokens = tuple(token.replace("~1", "/").replace("~0", "~")
                       for token in pointer.split("/")[1:])
        selectors.append(Selector(identifier, file_id, tokens))
    _check_path(root, directory=True)
    for entry in files:
        _check_path(entry.path)
    return Bundle(tuple(files), tuple(selectors), limit)


def read_bundle(bundle: Bundle) -> dict[str, Any]:
    ledger = []
    documents = {}
    for entry in bundle.files:
        record = {"id": entry.id, "status": "UNREADABLE", "bytes": None,
                  "sha256": None, "lines": None}
        try:
            with os.fdopen(_open(entry.path), "rb") as source:
                payload = source.read()
        except FileNotFoundError:
            record["status"] = "MISSING"
        except OSError:
            record["status"] = "UNREADABLE"
        else:
            digest = hashlib.sha256(payload).hexdigest()
            record.update(status="MATCH" if digest == entry.sha256 else "DRIFT",
                          bytes=len(payload), sha256=digest, lines=len(payload.splitlines()))
            if record["status"] == "MATCH":
                try:
                    documents[entry.id] = ("VALUE", _json(payload))
                except (ValueError, UnicodeError, RecursionError):
                    documents[entry.id] = ("INVALID_JSON", None)
        ledger.append(record)
    values = []
    for selector in bundle.selectors:
        status, value = documents.get(selector.file, ("UNAVAILABLE", None))
        if status == "VALUE":
            for token in selector.tokens:
                if isinstance(value, dict) and token in value:
                    value = value[token]
                elif (isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", token)
                      and len(token) <= len(str(len(value))) and int(token) < len(value)):
                    value = value[int(token)]
                else:
                    status = "MISSING"
                    break
        result = {"id": selector.id, "status": status}
        if status == "VALUE":
            result["value"] = value
        values.append(result)
    return {"schema": 1, "files": ledger, "values": values}


def main(argv: list[str] = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 1:
            raise InputError("Usage: python3 tools/read_bundle.py BUNDLE.json")
        try:
            with open(args[0], "rb") as source:
                value = _json(source.read())
        except OSError:
            raise InputError("Cannot read input bundle") from None
        except (ValueError, UnicodeError, RecursionError):
            raise InputError("Input bundle is not valid UTF-8 JSON") from None
        bundle = parse_bundle(value)
        response = read_bundle(bundle)
        output = (json.dumps(response, ensure_ascii=False, allow_nan=False,
                             separators=(",", ":")) + "\n").encode("utf-8")
        if len(output) > bundle.max_output_bytes:
            raise InputError("OUTPUT_TOO_LARGE")
    except InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
