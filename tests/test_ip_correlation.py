from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules/facebook_ip_correlation"))

from facebook_ip_correlation.extractor import extract_observations, process_export  # noqa: E402

SAMPLE = ROOT / "modules/facebook_ip_correlation/examples/facebook_sample"


class IpCorrelationTests(unittest.TestCase):
    def test_extracts_html_and_json_observations(self) -> None:
        records = extract_observations(SAMPLE)
        self.assertEqual(len(records), 4)
        self.assertIn("IPv4", {item.ip_version for item in records})
        self.assertIn("precise_device_location", {item.location_signal_type for item in records})
        self.assertIn("same_ip", {item.label for item in _summary_rows(SAMPLE)})

    def test_writes_observations_correlations_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = process_export(SAMPLE, Path(tmp))
            self.assertEqual(summary["observation_count"], 4)
            self.assertGreaterEqual(summary["correlation_count"], 2)

            observations_jsonl = Path(tmp) / "ip_observations.jsonl"
            observations_csv = Path(tmp) / "ip_observations.csv"
            correlations_json = Path(tmp) / "ip_correlation_summary.json"
            correlations_csv = Path(tmp) / "ip_correlation_summary.csv"
            self.assertTrue(observations_jsonl.exists())
            self.assertTrue(observations_csv.exists())
            self.assertTrue(correlations_json.exists())
            self.assertTrue(correlations_csv.exists())

            rows = [json.loads(line) for line in observations_jsonl.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 4)
            with observations_csv.open("r", encoding="utf-8", newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 4)
            correlation_rows = json.loads(correlations_json.read_text(encoding="utf-8"))
            self.assertTrue(any(row["label"] == "same_subnet" for row in correlation_rows))

    def test_zip_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "sample.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                for path in SAMPLE.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(SAMPLE).as_posix())
            records = extract_observations(zip_path)
            self.assertEqual(len(records), 4)


def _summary_rows(sample: Path):
    with tempfile.TemporaryDirectory() as tmp:
        process_export(sample, Path(tmp))
        data = json.loads((Path(tmp) / "ip_correlation_summary.json").read_text(encoding="utf-8"))
    return [type("Row", (), item) for item in data]


if __name__ == "__main__":
    unittest.main()
