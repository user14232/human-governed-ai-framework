from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kernel.store.file_store import (
    ParseError,
    append_json_array_element,
    atomic_rename,
    atomic_write,
    read_json,
    read_yaml,
    sha256_from_disk,
)
from kernel.store.run_store import create_run_directory, list_run_ids, run_directory


class StorePrimitivesTest(unittest.TestCase):
    def test_run_store_directory_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "RUN-20260314-0001"
            run_dir = create_run_directory(root, run_id)
            self.assertTrue((run_dir / "artifacts").is_dir())
            self.assertEqual(run_directory(root, run_id), run_dir)
            self.assertEqual(list_run_ids(root), [run_id])

    def test_atomic_write_and_hash_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "artifact.txt"
            atomic_write(path, "a\r\nb\r\n")
            self.assertEqual(path.read_text(encoding="utf-8"), "a\nb\n")
            h1 = sha256_from_disk(path)
            path.write_text("a\nb\n", encoding="utf-8")
            h2 = sha256_from_disk(path)
            self.assertEqual(h1, h2)

    def test_atomic_rename_rejects_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.txt"
            dst = Path(td) / "b.txt"
            src.write_text("x", encoding="utf-8")
            dst.write_text("y", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                atomic_rename(src, dst)

    def test_read_yaml_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            y = Path(td) / "a.yaml"
            j = Path(td) / "a.json"
            y.write_text("id: 1\nname: test\n", encoding="utf-8")
            j.write_text('{"id": "x"}', encoding="utf-8")
            self.assertEqual(read_yaml(y)["name"], "test")
            self.assertEqual(read_json(j)["id"], "x")

    def test_append_json_array_element(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "events.json"
            append_json_array_element(path, {"id": 1})
            append_json_array_element(path, {"id": 2})
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in data], [1, 2])

    def test_append_json_array_element_rejects_non_array(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.json"
            path.write_text('{"id":1}', encoding="utf-8")
            with self.assertRaises(ParseError):
                append_json_array_element(path, {"id": 2})


if __name__ == "__main__":
    unittest.main()

