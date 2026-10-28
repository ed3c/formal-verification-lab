from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import read_bundle


SCRIPT = Path(read_bundle.__file__).resolve()


class ReadBundleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / "data"
        self.root.mkdir()
        self.manifest = self.base / "bundle.json"
        self.bundle = {"schema": 1, "root": str(self.root), "files": [],
                       "selectors": [], "max_output_bytes": 16384}

    def file(self, identifier, name, payload):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        self.bundle["files"].append({"id": identifier, "path": str(path),
                                     "sha256": hashlib.sha256(payload).hexdigest()})
        return path

    def selector(self, identifier, file_id, pointer):
        self.bundle["selectors"].append({"id": identifier, "file": file_id, "pointer": pointer})

    def run_cli(self, bundle=None):
        self.manifest.write_text(json.dumps(self.bundle if bundle is None else bundle), encoding="utf-8")
        return subprocess.run([sys.executable, str(SCRIPT), str(self.manifest)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)

    def success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b"")
        self.assertTrue(result.stdout.endswith(b"\n"))
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertLessEqual(len(result.stdout), self.bundle["max_output_bytes"])
        return json.loads(result.stdout)

    def input_error(self, bundle, diagnostic):
        result = self.run_cli(bundle)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertIn(diagnostic, result.stderr.decode("utf-8"))
        self.assertNotIn(b"Traceback", result.stderr)
        return result

    def test_literal_ledger_values_and_read_only_sources(self):
        payload = b'{"item":{"status":"ready"},"n":null}\r\n'
        path = self.file("F1", "part.json", payload)
        self.selector("S1", "F1", "/item/status")
        self.selector("S2", "F1", "/n")
        self.selector("S3", "F1", "/item")
        path.chmod(0o444)
        before = path.stat()
        result = self.success(self.run_cli())
        self.assertEqual(result, {
            "schema": 1,
            "files": [{"id": "F1", "status": "MATCH", "bytes": 38,
                       "sha256": "8fbcac838057a88a9111549170b0f0353d420b2f38214527a9d32631bea3ea67",
                       "lines": 1}],
            "values": [{"id": "S1", "status": "VALUE", "value": "ready"},
                       {"id": "S2", "status": "VALUE", "value": None},
                       {"id": "S3", "status": "VALUE", "value": {"status": "ready"}}],
        })
        after = path.stat()
        self.assertEqual(path.read_bytes(), payload)
        self.assertEqual((before.st_ino, before.st_size, before.st_mode, before.st_mtime_ns),
                         (after.st_ino, after.st_size, after.st_mode, after.st_mtime_ns))
        self.assertEqual(json.loads(self.manifest.read_bytes()), self.bundle)

    def test_partial_missing_file_preserves_value_and_null_metadata(self):
        self.file("good", "good.json", b'{"ok":true}')
        missing = self.file("absent", "gone.json", b'{}')
        missing.unlink()
        self.selector("missing", "absent", "")
        self.selector("present", "good", "/ok")
        result = self.success(self.run_cli())
        self.assertEqual(result["files"][1], {"id": "absent", "status": "MISSING",
                                             "bytes": None, "sha256": None, "lines": None})
        self.assertEqual(result["values"], [{"id": "missing", "status": "UNAVAILABLE"},
                                             {"id": "present", "status": "VALUE", "value": True}])

    def test_drift_keeps_actual_digest_and_does_not_parse(self):
        path = self.file("F1", "drift.json", b'{}')
        path.write_bytes(b'not JSON\nsecond line')
        self.selector("S1", "F1", "")
        bundle = read_bundle.parse_bundle(self.bundle)
        with mock.patch.object(read_bundle, "_json", side_effect=AssertionError("DRIFT parsed")):
            observed = read_bundle.read_bundle(bundle)
        result = self.success(self.run_cli())
        self.assertEqual(observed, result)
        self.assertEqual(result["files"], [{"id": "F1", "status": "DRIFT", "bytes": 20,
                                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                           "lines": 2}])
        self.assertNotEqual(result["files"][0]["sha256"], self.bundle["files"][0]["sha256"])
        self.assertEqual(result["values"], [{"id": "S1", "status": "UNAVAILABLE"}])

    def test_pointer_escapes_arrays_and_independent_missing_values(self):
        self.file("F1", "keys.json", b'{"a/b":{"~key":[false,{"~1":"yes"}]},"":7,"01":"key"}')
        pointers = ["/a~1b/~0key/1/~01", "/a~1b/~0key/0", "/", "/01", "",
                    "/a~1b/~0key/01", "/a~1b/~0key/-", "/a~1b/~0key/2",
                    "/absent", "/a~1b/~0key/0/child", "/a~1b/~0key/" + "9" * 5000]
        for index, pointer in enumerate(pointers):
            self.selector(str(index), "F1", pointer)
        values = self.success(self.run_cli())["values"]
        self.assertEqual(values[:4], [{"id": "0", "status": "VALUE", "value": "yes"},
                                      {"id": "1", "status": "VALUE", "value": False},
                                      {"id": "2", "status": "VALUE", "value": 7},
                                      {"id": "3", "status": "VALUE", "value": "key"}])
        self.assertEqual(values[4], {"id": "4", "status": "VALUE",
                                      "value": {"a/b": {"~key": [False, {"~1": "yes"}]}, "": 7, "01": "key"}})
        self.assertEqual(values[5:], [{"id": str(index), "status": "MISSING"} for index in range(5, 11)])

    def test_invalid_json_keeps_match_and_other_success(self):
        self.file("bad", "bad.json", b'{"instruction":"SYNTHETIC_SECRET",broken')
        self.file("good", "good.json", b'[1,2]')
        self.selector("bad1", "bad", "")
        self.selector("good", "good", "")
        self.selector("bad2", "bad", "/instruction")
        result = self.success(self.run_cli())
        self.assertEqual([item["status"] for item in result["files"]], ["MATCH", "MATCH"])
        self.assertEqual(result["values"], [{"id": "bad1", "status": "INVALID_JSON"},
                                             {"id": "good", "status": "VALUE", "value": [1, 2]},
                                             {"id": "bad2", "status": "INVALID_JSON"}])

    def test_nonstandard_json_is_invalid(self):
        for payload in [b'NaN', b'Infinity', b'-Infinity', b'1e400', b'"\xff"',
                        b'"\\ud800"', b'{"x":1,"x":2}']:
            with self.subTest(payload=payload):
                self.bundle["files"] = []
                self.bundle["selectors"] = []
                self.file("F1", "invalid.json", payload)
                self.selector("S1", "F1", "")
                result = self.success(self.run_cli())
                self.assertEqual(result["values"], [{"id": "S1", "status": "INVALID_JSON"}])

    def test_lines_use_bytes_splitlines_with_or_without_final_newline(self):
        for index, payload in enumerate([b'', b'{}', b'{}\n', b'\r\n{}\r\n\r\n', b'\n\n']):
            self.file(str(index), str(index) + ".json", payload)
        result = self.success(self.run_cli())
        self.assertEqual([item["lines"] for item in result["files"]], [0, 1, 1, 3, 2])

    def test_unreadable_file_does_not_erase_other_values(self):
        self.file("F1", "good.json", b'42')
        path = self.file("F2", "denied.json", b'{}')
        self.selector("S1", "F1", "")
        self.selector("S2", "F2", "")
        bundle = read_bundle.parse_bundle(self.bundle)
        original = read_bundle._open

        def denied(candidate, directory=False):
            if candidate == path:
                raise PermissionError("Synthetic denial")
            return original(candidate, directory)

        with mock.patch.object(read_bundle, "_open", side_effect=denied):
            result = read_bundle.read_bundle(bundle)
        self.assertEqual(result["files"][1], {"id": "F2", "status": "UNREADABLE", "bytes": None,
                                             "sha256": None, "lines": None})
        self.assertEqual(result["values"], [{"id": "S1", "status": "VALUE", "value": 42},
                                             {"id": "S2", "status": "UNAVAILABLE"}])

    def test_directory_and_fifo_are_unreadable_without_blocking(self):
        path = self.file("F1", "directory", b'{}')
        path.unlink()
        path.mkdir()
        fifo = self.root / "fifo"
        os.mkfifo(fifo)
        self.bundle["files"].append({"id": "F2", "path": str(fifo), "sha256": "0" * 64})
        result = self.success(self.run_cli())
        self.assertEqual(result["files"], [
            {"id": identifier, "status": "UNREADABLE", "bytes": None, "sha256": None, "lines": None}
            for identifier in ["F1", "F2"]])

    def test_duplicate_ids_and_unknown_file_are_input_errors(self):
        self.file("same", "part.json", b'{}')
        self.selector("same", "same", "")
        self.success(self.run_cli())
        duplicate_file = copy.deepcopy(self.bundle)
        duplicate_file["files"].append(dict(duplicate_file["files"][0]))
        self.input_error(duplicate_file, "Duplicate file id")
        duplicate_selector = copy.deepcopy(self.bundle)
        duplicate_selector["selectors"].append(dict(duplicate_selector["selectors"][0]))
        self.input_error(duplicate_selector, "Duplicate selector id")
        unknown = copy.deepcopy(self.bundle)
        unknown["selectors"][0]["file"] = "unknown"
        self.input_error(unknown, "existing file id")

    def test_invalid_pointer_is_input_error(self):
        self.file("F1", "part.json", b'{}')
        for pointer in ["key", "/~", "/~2", "/a~01~3", None, 1]:
            with self.subTest(pointer=pointer):
                candidate = copy.deepcopy(self.bundle)
                candidate["selectors"] = [{"id": "S1", "file": "F1", "pointer": pointer}]
                self.input_error(candidate, "pointer")

    def test_escape_relative_and_unresolved_paths_are_rejected(self):
        self.file("F1", "part.json", b'{}')
        for path in [str(self.base / "outside.json"), str(self.root) + "-other/file.json"]:
            with self.subTest(path=path):
                candidate = copy.deepcopy(self.bundle)
                candidate["files"][0]["path"] = path
                self.input_error(candidate, "escapes root")
        for field in ["root", "path"]:
            for path in ["relative", str(self.root) + "/../data", str(self.root) + "/./part.json",
                         str(self.root) + "//part.json", str(self.root) + "/", "/bad\x00path"]:
                with self.subTest(field=field, path=path):
                    candidate = copy.deepcopy(self.bundle)
                    target = candidate if field == "root" else candidate["files"][0]
                    target[field] = path
                    self.input_error(candidate, "absolute and resolved")

    def test_symlinks_in_file_ancestors_root_and_dangling_links_are_rejected(self):
        target = self.file("F1", "part.json", b'{}')
        file_link = self.root / "link.json"
        file_link.symlink_to(target)
        dangling = self.root / "dangling.json"
        dangling.symlink_to(self.root / "absent.json")
        directory_link = self.root / "sub"
        directory_link.symlink_to(self.root, target_is_directory=True)
        root_link = self.base / "root-link"
        root_link.symlink_to(self.root, target_is_directory=True)
        for path in [file_link, dangling, directory_link / "part.json"]:
            with self.subTest(path=path):
                candidate = copy.deepcopy(self.bundle)
                candidate["files"][0]["path"] = str(path)
                self.input_error(candidate, "Symlink")
        candidate = copy.deepcopy(self.bundle)
        candidate["root"] = str(root_link)
        candidate["files"][0]["path"] = str(root_link / "part.json")
        self.input_error(candidate, "Symlink")
        candidate["files"] = []
        self.input_error(candidate, "Symlink")

    def test_shape_digest_and_output_limit_errors_are_diagnostic(self):
        self.file("F1", "part.json", b'{}')
        for field, value in [("schema", True), ("schema", 2), ("files", {}), ("selectors", {}),
                             ("max_output_bytes", 0), ("max_output_bytes", 65537),
                             ("max_output_bytes", True), ("max_output_bytes", 2.0)]:
            with self.subTest(field=field, value=value):
                candidate = copy.deepcopy(self.bundle)
                candidate[field] = value
                self.input_error(candidate, field)
        for entry in [{}, {"id": [], "path": str(self.root), "sha256": "0" * 64},
                      {"id": "F1", "path": str(self.root), "sha256": "A" * 64}]:
            with self.subTest(entry=entry):
                candidate = copy.deepcopy(self.bundle)
                candidate["files"] = [entry]
                self.input_error(candidate, "file")
        for candidate in [[], {}, {**self.bundle, "extra": "SYNTHETIC_SECRET"}]:
            result = self.input_error(candidate, "bundle")
            self.assertNotIn(b"SYNTHETIC_SECRET", result.stderr)

    def test_invalid_bundle_json_and_unavailable_bundle_do_not_fake_success(self):
        for payload in [b'{"secret":"SYNTHETIC_SECRET",broken', b'null', b'NaN',
                        b'{"schema":1,"schema":1}', b'\xff']:
            with self.subTest(payload=payload):
                self.manifest.write_bytes(payload)
                result = subprocess.run([sys.executable, str(SCRIPT), str(self.manifest)], capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertNotIn(b"SYNTHETIC_SECRET", result.stderr)
                self.assertNotIn(b"Traceback", result.stderr)
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.base / "missing")], capture_output=True)
        self.assertEqual((result.returncode, result.stdout), (2, b""))
        self.assertIn(b"Cannot read input bundle", result.stderr)

    def test_utf8_output_bound_counts_newline_and_emits_no_partial_response(self):
        self.file("F1", "unicode.json", json.dumps({"text": "漢" * 1000}, ensure_ascii=False).encode("utf-8"))
        self.selector("S1", "F1", "/text")
        result = self.run_cli()
        self.assertEqual(self.success(result)["values"], [{"id": "S1", "status": "VALUE", "value": "漢" * 1000}])
        byte_count = len(result.stdout)
        self.assertGreater(byte_count, len(result.stdout.decode("utf-8")))
        self.bundle["max_output_bytes"] = byte_count
        exact = self.run_cli()
        self.success(exact)
        self.assertEqual(exact.stdout, result.stdout)
        self.bundle["max_output_bytes"] = byte_count - 1
        self.input_error(self.bundle, "OUTPUT_TOO_LARGE")
        self.bundle["max_output_bytes"] = len(result.stdout.decode("utf-8"))
        self.input_error(self.bundle, "OUTPUT_TOO_LARGE")

    def test_limit_endpoints_and_large_object_do_not_silently_truncate(self):
        self.bundle["max_output_bytes"] = 1
        self.input_error(self.bundle, "OUTPUT_TOO_LARGE")
        self.bundle["max_output_bytes"] = 65536
        self.success(self.run_cli())
        self.file("F1", "large.json", json.dumps({"blob": ["synthetic" * 10000]}).encode())
        self.selector("S1", "F1", "")
        self.input_error(self.bundle, "OUTPUT_TOO_LARGE")

    def test_sources_parse_with_python39_grammar(self):
        for path in [SCRIPT, Path(__file__)]:
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 9))


if __name__ == "__main__":
    unittest.main()
