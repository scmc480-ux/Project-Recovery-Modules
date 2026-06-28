from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules/facebook_interactions"))

from facebook_interactions.extractor import extract_interactions, process_export  # noqa: E402

SAMPLE = ROOT / "modules/facebook_interactions/examples/facebook_sample"


class InteractionTests(unittest.TestCase):
    def test_extracts_sample_interactions_sorted_by_timestamp(self) -> None:
        records = extract_interactions(SAMPLE)
        self.assertGreaterEqual(len(records), 3)
        self.assertEqual([item.timestamp for item in records], sorted(item.timestamp for item in records))
        self.assertIn("comment", {item.interaction_type for item in records})
        self.assertIn("view_or_visit", {item.interaction_type for item in records})

    def test_writes_jsonl_csv_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = process_export(SAMPLE, Path(tmp))
            self.assertGreaterEqual(summary["interaction_count"], 3)
            jsonl = Path(tmp) / "interactions_by_timestamp.jsonl"
            csv_path = Path(tmp) / "interactions_by_timestamp.csv"
            entity_json = Path(tmp) / "entity_interaction_summary.json"
            entity_csv = Path(tmp) / "entity_interaction_summary.csv"
            self.assertTrue(jsonl.exists())
            self.assertTrue(csv_path.exists())
            self.assertTrue(entity_json.exists())
            self.assertTrue(entity_csv.exists())

            rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), summary["interaction_count"])
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(len(csv_rows), summary["interaction_count"])
            entity_rows = json.loads(entity_json.read_text(encoding="utf-8"))
            self.assertTrue(any(row["interaction_count"] >= 1 for row in entity_rows))
            with entity_csv.open("r", encoding="utf-8", newline="") as handle:
                self.assertTrue(list(csv.DictReader(handle)))

    def test_zip_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "sample.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                for path in SAMPLE.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(SAMPLE).as_posix())
            records = extract_interactions(zip_path)
            self.assertGreaterEqual(len(records), 3)


if __name__ == "__main__":
    unittest.main()
