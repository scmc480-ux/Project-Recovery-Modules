from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules/facebook_identity_variants"))

from facebook_identity_variants.extractor import (  # noqa: E402
    build_owner_identity_crosscheck,
    build_variant_timeline,
    extract_observations,
    load_alias_rules,
    process_export,
    summarize_variants,
)
from facebook_identity_variants.batch import process_batch  # noqa: E402

SAMPLE = ROOT / "modules/facebook_identity_variants/examples/facebook_sample"


class IdentityVariantTests(unittest.TestCase):
    def test_extracts_deleted_user_and_name_variants(self) -> None:
        records = extract_observations(SAMPLE)
        self.assertGreaterEqual(len(records), 6)
        self.assertIn("123456789", {row.facebook_id for row in records})
        self.assertIn("555555555", {row.facebook_id for row in records})
        self.assertTrue(any(row.deleted_user_observed for row in records))
        self.assertTrue(any(row.ip_address == "198.51.100.10" for row in records))
        self.assertTrue(any(row.profile_url == "facebook.com/alexsample" for row in records))
        self.assertTrue(any(row.vanity_slug == "alexsample" for row in records))
        self.assertTrue(any(row.thread_identifier == "alexsample_123456789" for row in records))
        self.assertTrue(any(row.participant_context in {"participant_list", "message_thread"} for row in records))

    def test_extracts_wide_identifier_variants(self) -> None:
        records = extract_observations(SAMPLE)
        related_ids = {f"{row.related_id_type}:{row.related_id_value}" for row in records if row.related_id_value}
        self.assertIn("marketplace_listing_id:900100200300", related_ids)
        self.assertIn("seller_id:123456789", related_ids)
        self.assertIn("buyer_id:987654321", related_ids)
        self.assertIn("notification_id:600700800900", related_ids)
        self.assertIn("notification_id:600700800902", related_ids)
        self.assertIn("target_id:444555666777", related_ids)
        self.assertIn("post_id:444555666777", related_ids)
        self.assertIn("comment_id:111222333444", related_ids)
        self.assertIn("tag_id:222333444555", related_ids)
        self.assertIn("photo_id:333444555666", related_ids)
        self.assertIn("video_id:777888999000", related_ids)
        self.assertIn("email_address:alex.sample@example.invalid", related_ids)
        self.assertIn("phone_number:+15550102000", related_ids)
        self.assertIn("device_id:555666777888", related_ids)
        self.assertIn("session_id:222333444666", related_ids)
        self.assertIn("reaction_id:101010101010", related_ids)
        self.assertIn("like_id:202020202020", related_ids)
        self.assertIn("share_id:303030303030", related_ids)
        self.assertIn("group_id:707070707070", related_ids)
        self.assertIn("event_id:909090909090", related_ids)
        self.assertIn("place_id:515151515151", related_ids)
        self.assertIn("payment_id:343434343434", related_ids)
        self.assertIn("transaction_id:454545454545", related_ids)

    def test_extracts_notification_actor_and_email_notification_ids(self) -> None:
        records = extract_observations(SAMPLE)
        self.assertTrue(
            any(
                row.observation_type == "notification_actor_identity"
                and row.facebook_id == "123456789"
                and row.name == "Alex Sample"
                and row.related_id_type == "notification_id"
                and row.related_id_value == "600700800900"
                for row in records
            )
        )
        self.assertTrue(
            any(
                row.observation_type == "email_notification_identifier"
                and row.related_id_type == "fbid"
                and row.related_id_value == "123456789"
                and row.participant_context == "email_notification_sent"
                for row in records
            )
        )

    def test_flags_cross_identity_variant_ideas(self) -> None:
        records = extract_observations(SAMPLE)
        summaries = summarize_variants(records)
        variant_types = {row.variant_type for row in summaries}
        self.assertIn("shared_ip_across_identity_keys", variant_types)
        self.assertIn("same_normalized_name_different_facebook_ids", variant_types)
        self.assertIn("shared_handle_across_identity_keys", variant_types)
        self.assertIn("shared_profile_slug_across_identity_keys", variant_types)
        self.assertIn("marketplace_identifier_context", variant_types)
        self.assertIn("shared_platform_object_id_across_identity_keys", variant_types)
        self.assertIn("contact_identifier_context", variant_types)
        self.assertIn("device_session_identifier_context", variant_types)
        self.assertIn("commerce_payment_identifier_context", variant_types)
        self.assertIn("reaction_or_engagement_identifier_context", variant_types)
        self.assertIn("location_or_place_identifier_context", variant_types)
        self.assertIn("social_graph_object_identifier_context", variant_types)
        self.assertIn("same_numeric_id_across_related_id_types", variant_types)
        self.assertIn("related_id_value_matches_facebook_id", variant_types)
        self.assertIn("shared_profile_url_across_identity_keys", variant_types)

    def test_builds_variant_timeline_by_date(self) -> None:
        records = extract_observations(SAMPLE)
        timeline = build_variant_timeline(records)
        self.assertGreater(len(timeline), len(records))
        self.assertTrue(any(row.variant_id == "facebook_id:123456789" and row.interaction_date == "2024-04-02" for row in timeline))
        self.assertTrue(any(row.variant_id == "related_id:marketplace_listing_id:900100200300" for row in timeline))
        self.assertTrue(any(row.variant_id == "related_id:notification_id:600700800900" for row in timeline))
        self.assertTrue(all(row.variant_id for row in timeline))
        self.assertEqual(timeline, sorted(timeline, key=lambda row: (row.variant_id, row.timestamp == "", row.timestamp, row.source_path, row.raw_payload_path)))

    def test_builds_owner_identity_crosscheck(self) -> None:
        records = extract_observations(SAMPLE)
        timeline = build_variant_timeline(records)
        roster, first_contacts, unassigned, report, alias_clusters, master_first_contacts = build_owner_identity_crosscheck(
            records,
            timeline,
            load_alias_rules(SAMPLE / "identity_aliases.json"),
        )
        self.assertGreater(len(roster), 0)
        owner = roster[0]
        self.assertEqual(owner.identity_status, "CONFIRMED_ACCOUNT_OWNER")
        self.assertEqual(owner.display_name, "Alex Sample")
        self.assertIn("alex.sample@example.invalid", owner.emails_observed)
        self.assertIn("123456789", owner.facebook_ids_observed)
        self.assertTrue(any(row.display_name == "Alex Alias" and row.master_identity_name == "Alex Sample" for row in roster))
        self.assertTrue(any("Alex Alias" in row.alias_display_names for row in alias_clusters))
        self.assertTrue(any(row.alias_cluster_confidence == "data_supported_alias_session" for row in alias_clusters))
        self.assertTrue(any("recently_visited_alias.json" in row.alias_cluster_evidence for row in alias_clusters))
        self.assertTrue(any(row.master_identity_name == "Alex Sample" and row.alias_display_name == "Alex Alias" for row in master_first_contacts))
        self.assertTrue(any(row.identity_key == "alex sample" and row.variant_id == "identity" for row in first_contacts))
        self.assertTrue(any(row.related_id_type == "notification_id" for row in unassigned))
        self.assertIn("CONFIRMED ACCOUNT OWNER IDENTITY", report)

    def test_writes_observations_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = process_export(SAMPLE, Path(tmp))
            self.assertGreaterEqual(summary["observation_count"], 6)
            self.assertGreaterEqual(summary["variant_group_count"], 6)
            self.assertGreater(summary["variant_timeline_row_count"], summary["observation_count"])
            self.assertGreaterEqual(summary["variant_timeline_id_count"], summary["related_id_count"])
            self.assertGreaterEqual(summary["deleted_user_observation_count"], 1)
            self.assertGreaterEqual(summary["related_id_count"], 50)

            observations_jsonl = Path(tmp) / "identity_observations.jsonl"
            observations_csv = Path(tmp) / "identity_observations.csv"
            variants_json = Path(tmp) / "identity_variant_summary.json"
            variants_csv = Path(tmp) / "identity_variant_summary.csv"
            timeline_jsonl = Path(tmp) / "identity_variant_timeline.jsonl"
            timeline_csv = Path(tmp) / "identity_variant_timeline.csv"
            owner_roster = Path(tmp) / "owner_identity_roster.csv"
            owner_timeline = Path(tmp) / "owner_identity_first_contact_timeline.csv"
            owner_unassigned = Path(tmp) / "owner_identity_unassigned_id_variants.csv"
            owner_report = Path(tmp) / "owner_identity_crosscheck_report.txt"
            master_aliases = Path(tmp) / "master_identity_alias_clusters.csv"
            master_timeline = Path(tmp) / "master_identity_first_contact_timeline.csv"
            self.assertTrue(observations_jsonl.exists())
            self.assertTrue(observations_csv.exists())
            self.assertTrue(variants_json.exists())
            self.assertTrue(variants_csv.exists())
            self.assertTrue(timeline_jsonl.exists())
            self.assertTrue(timeline_csv.exists())
            self.assertTrue(owner_roster.exists())
            self.assertTrue(owner_timeline.exists())
            self.assertTrue(owner_unassigned.exists())
            self.assertTrue(owner_report.exists())
            self.assertTrue(master_aliases.exists())
            self.assertTrue(master_timeline.exists())
            self.assertGreaterEqual(summary["owner_identity_roster_count"], 1)
            self.assertGreaterEqual(summary["owner_identity_first_contact_count"], 1)
            self.assertGreaterEqual(summary["master_identity_alias_cluster_count"], 1)
            self.assertGreaterEqual(summary["master_identity_first_contact_count"], 1)

            rows = [json.loads(line) for line in observations_jsonl.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), summary["observation_count"])
            timeline_rows = [json.loads(line) for line in timeline_jsonl.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(timeline_rows), summary["variant_timeline_row_count"])
            self.assertTrue(any(row["variant_id"] == "related_id:marketplace_listing_id:900100200300" for row in timeline_rows))
            self.assertTrue(any(row["variant_id"] == "facebook_id:123456789" and row["interaction_date"] for row in timeline_rows))
            variants = json.loads(variants_json.read_text(encoding="utf-8"))
            self.assertTrue(any(row["variant_type"] == "name_variant_same_facebook_id" for row in variants))
            self.assertTrue(any(row["variant_type"] == "same_normalized_name_different_facebook_ids" for row in variants))
            self.assertTrue(any(row["variant_type"] == "shared_ip_across_identity_keys" for row in variants))
            self.assertTrue(any(row["variant_type"] == "marketplace_identifier_context" for row in variants))
            self.assertTrue(any(row["variant_type"] == "shared_platform_object_id_across_identity_keys" for row in variants))
            self.assertTrue(any(row["variant_type"] == "same_numeric_id_across_related_id_types" for row in variants))
            self.assertTrue(any(row["variant_type"] == "related_id_value_matches_facebook_id" for row in variants))
            self.assertTrue(any("marketplace_listing_id:900100200300" in row["related_ids"] for row in variants))
            self.assertTrue(any("notification_id:600700800900" in row["related_ids"] for row in variants))
            self.assertTrue(any("email_address:alex.sample@example.invalid" in row["related_ids"] for row in variants))
            self.assertTrue(any(row["variant_type"] == "deleted_user_or_unavailable_label" for row in variants))
            self.assertTrue(any("alexsample" in row["vanity_slugs"] for row in variants))
            self.assertTrue(any("alexsample_123456789" in row["thread_identifiers"] for row in variants))
            with observations_csv.open("r", encoding="utf-8", newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), summary["observation_count"])
            with timeline_csv.open("r", encoding="utf-8", newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), summary["variant_timeline_row_count"])

    def test_zip_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "sample.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                for path in SAMPLE.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(SAMPLE).as_posix())
            records = extract_observations(zip_path)
            self.assertGreaterEqual(len(records), 5)

    def test_batch_writer_recreates_master_crosscheck_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "batch"
            summary = process_batch([SAMPLE], output)

            self.assertEqual(summary["completed_source_count"], 1)
            self.assertEqual(summary["skipped_source_count"], 0)
            self.assertTrue((output / "batch_manifest.json").exists())
            self.assertTrue((output / "MASTER_counts.json").exists())
            self.assertTrue((output / "MASTER_run_summary.csv").exists())
            self.assertTrue((output / "MASTER_identity_observations.jsonl").exists())
            self.assertTrue((output / "MASTER_identity_variant_summary.jsonl").exists())
            self.assertTrue((output / "MASTER_identity_variant_timeline_by_date.jsonl").exists())
            self.assertTrue((output / "OWNER_IDENTITY_VARIANT_CROSSCHECK_ROSTER.csv").exists())
            self.assertTrue((output / "OWNER_IDENTITY_FIRST_CONTACT_TIMELINE.csv").exists())
            self.assertTrue((output / "OWNER_IDENTITY_FIRST_CONTACT_TIMELINE.txt").exists())
            self.assertTrue((output / "OWNER_IDENTITY_UNASSIGNED_ID_VARIANTS.csv").exists())
            self.assertTrue((output / "OWNER_IDENTITY_VARIANT_CROSSCHECK_REPORT.txt").exists())

            with (output / "MASTER_identity_observations.csv").open("r", encoding="utf-8", newline="") as handle:
                self.assertEqual(next(csv.reader(handle))[:2], ["source_pack", "source_root"])
            with (output / "MASTER_identity_variant_timeline_by_date.csv").open("r", encoding="utf-8", newline="") as handle:
                self.assertEqual(next(csv.reader(handle))[:4], ["source_pack", "source_root", "variant_id", "variant_id_type"])
            with (output / "OWNER_IDENTITY_VARIANT_CROSSCHECK_ROSTER.csv").open("r", encoding="utf-8", newline="") as handle:
                header = next(csv.reader(handle))
            self.assertEqual(
                header,
                [
                    "identity_status",
                    "identity_key",
                    "display_name",
                    "all_name_variants",
                    "observation_count",
                    "first_observed_timestamp",
                    "last_observed_timestamp",
                    "first_contact_date",
                    "first_contact_source_path",
                    "facebook_ids_observed",
                    "phone_numbers_direct",
                    "phone_number_candidates",
                    "emails_observed",
                    "profile_urls",
                    "vanity_slugs",
                    "thread_identifiers",
                    "ip_addresses",
                    "other_identifying_ids",
                    "variant_ids_count",
                    "variant_ids_sample",
                    "source_packs",
                    "source_paths_sample",
                    "deleted_user_observed",
                ],
            )


if __name__ == "__main__":
    unittest.main()
