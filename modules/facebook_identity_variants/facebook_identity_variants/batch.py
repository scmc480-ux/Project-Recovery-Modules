from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .extractor import OBSERVATION_COLUMNS, SUMMARY_COLUMNS, TIMELINE_COLUMNS, process_export


OWNER_ROSTER_BATCH_COLUMNS = [
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
]

RUN_SUMMARY_COLUMNS = [
    "finished_at",
    "json_count",
    "observation_count",
    "output_path",
    "related_id_count",
    "source_name",
    "source_path",
    "started_at",
    "status",
    "variant_group_count",
    "variant_timeline_id_count",
    "variant_timeline_row_count",
]

TEXT_JOIN_COLUMNS = {
    "all_name_variants",
    "facebook_ids_observed",
    "phone_numbers_direct",
    "phone_number_candidates",
    "emails_observed",
    "profile_urls",
    "vanity_slugs",
    "thread_identifiers",
    "ip_addresses",
    "other_identifying_ids",
    "variant_ids_sample",
    "source_paths_sample",
}


def process_batch(sources: Iterable[Path], output: Path, alias_map: Path | None = None) -> dict[str, Any]:
    source_list = [Path(source) for source in sources]
    if not source_list:
        raise ValueError("At least one source path is required.")

    output.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    used_names: set[str] = set()
    common_parent = _common_parent(source_list)

    for source in source_list:
        source_name = _unique_name(_safe_name(source.stem or source.name), used_names)
        pack_output = output / source_name
        started_at = _now()
        json_count, html_count = _source_file_counts(source)

        if json_count == 0 and html_count == 0:
            manifest.append(
                _ordered_manifest_entry(
                    {
                    "source_name": source_name,
                    "source_path": str(source),
                    "output_path": str(pack_output),
                    "json_count": json_count,
                    "html_count": html_count,
                    "status": "skipped_empty",
                    "started_at": started_at,
                    "finished_at": _now(),
                    }
                )
            )
            continue

        summary = process_export(source, pack_output, alias_map)
        manifest.append(
            _ordered_manifest_entry(
                {
                "source_name": source_name,
                "source_path": str(source),
                "output_path": str(pack_output),
                "json_count": json_count,
                "html_count": html_count,
                "status": "completed",
                "started_at": started_at,
                "finished_at": _now(),
                **{key: summary[key] for key in summary if key.endswith("_count")},
                }
            )
        )

    completed = [row for row in manifest if row["status"] == "completed"]
    _write_json(output / "batch_manifest.json", manifest)
    masters = _write_master_outputs(output, completed)
    counts = _batch_counts(output, common_parent, manifest, masters)
    _write_json(output / "MASTER_counts.json", counts)
    _write_json(output / "MASTER_run_summary.json", manifest)
    _write_csv(output / "MASTER_run_summary.csv", manifest, RUN_SUMMARY_COLUMNS)
    return counts


def _write_master_outputs(output: Path, manifest: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    observations = _collect_rows(output, manifest, "identity_observations.csv")
    observations_path = output / "MASTER_identity_observations.csv"
    observations_jsonl = output / "MASTER_identity_observations.jsonl"
    _write_csv(observations_path, observations, ["source_pack", "source_root", *OBSERVATION_COLUMNS])
    _write_jsonl(observations_jsonl, observations, ["source_pack", "source_root", *OBSERVATION_COLUMNS])

    summaries = _collect_rows(output, manifest, "identity_variant_summary.csv")
    summaries_path = output / "MASTER_identity_variant_summary.csv"
    summaries_jsonl = output / "MASTER_identity_variant_summary.jsonl"
    _write_csv(summaries_path, summaries, ["source_pack", "source_root", *SUMMARY_COLUMNS])
    _write_jsonl(summaries_jsonl, summaries, ["source_pack", "source_root", *SUMMARY_COLUMNS])

    timeline = _collect_rows(output, manifest, "identity_variant_timeline.csv")
    timeline.sort(key=lambda row: (row.get("interaction_date", ""), row.get("timestamp", ""), row.get("variant_id", ""), row.get("source_path", "")))
    timeline_path = output / "MASTER_identity_variant_timeline_by_date.csv"
    timeline_jsonl = output / "MASTER_identity_variant_timeline_by_date.jsonl"
    _write_csv(timeline_path, timeline, ["source_pack", "source_root", *TIMELINE_COLUMNS])
    _write_jsonl(timeline_jsonl, timeline, ["source_pack", "source_root", *TIMELINE_COLUMNS])

    owner_roster = _merge_owner_rosters(_collect_rows(output, manifest, "owner_identity_roster.csv"))
    owner_roster_path = output / "OWNER_IDENTITY_VARIANT_CROSSCHECK_ROSTER.csv"
    _write_csv(owner_roster_path, owner_roster, OWNER_ROSTER_BATCH_COLUMNS)

    first_contacts = _collect_rows(output, manifest, "owner_identity_first_contact_timeline.csv")
    first_contacts.sort(key=lambda row: (row.get("first_interaction_date", ""), row.get("identity_key", ""), row.get("variant_id", "")))
    first_contacts_path = output / "OWNER_IDENTITY_FIRST_CONTACT_TIMELINE.csv"
    first_contacts_txt = output / "OWNER_IDENTITY_FIRST_CONTACT_TIMELINE.txt"
    _write_csv(first_contacts_path, first_contacts, [
        "identity_key",
        "display_name",
        "identity_status",
        "variant_id",
        "variant_id_type",
        "variant_id_value",
        "first_interaction_date",
        "timestamp",
        "observation_type",
        "related_id_type",
        "related_id_value",
        "related_id_context",
        "source_pack",
        "source_path",
        "evidence_name",
        "profile_url",
        "thread_identifier",
        "ip_address",
    ])
    _write_first_contact_text(first_contacts_txt, first_contacts)

    unassigned = _collect_rows(output, manifest, "owner_identity_unassigned_id_variants.csv")
    unassigned.sort(key=lambda row: (row.get("related_id_type", ""), row.get("related_id_value", ""), row.get("source_pack", "")))
    unassigned_path = output / "OWNER_IDENTITY_UNASSIGNED_ID_VARIANTS.csv"
    _write_csv(unassigned_path, _merge_unassigned(unassigned), [
        "related_id_type",
        "related_id_value",
        "observation_count",
        "first_observed_timestamp",
        "last_observed_timestamp",
        "contexts",
        "names_seen_on_same_rows",
        "source_packs",
        "source_paths_sample",
    ])

    report_path = output / "OWNER_IDENTITY_VARIANT_CROSSCHECK_REPORT.txt"
    _write_combined_owner_report(report_path, output, manifest, owner_roster)
    return {
        "observations": {"row_count": len(observations), "csv": str(observations_path), "jsonl": str(observations_jsonl)},
        "summary": {"row_count": len(summaries), "csv": str(summaries_path), "jsonl": str(summaries_jsonl)},
        "timeline": {"row_count": len(timeline), "csv": str(timeline_path), "jsonl": str(timeline_jsonl)},
        "runs": {"row_count": len(manifest), "csv": str(output / "MASTER_run_summary.csv"), "json": str(output / "MASTER_run_summary.json")},
    }


def _collect_rows(output: Path, manifest: list[dict[str, Any]], filename: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in manifest:
        source_name = str(entry["source_name"])
        path = output / source_name / filename
        for row in _read_csv(path):
            row["source_pack"] = source_name
            row["source_root"] = str(entry["source_path"])
            rows.append(row)
    return rows


def _merge_owner_rosters(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.get("identity_key", "") or row.get("display_name", "")
        current = grouped.setdefault(key, _empty_owner_row(row))
        current["observation_count"] += _as_int(row.get("observation_count"))
        current["variant_ids_count"] += _as_int(row.get("variant_ids_count"))
        current["deleted_user_observed"] = current["deleted_user_observed"] or _as_bool(row.get("deleted_user_observed"))
        current["first_observed_timestamp"] = _min_nonempty(current["first_observed_timestamp"], row.get("first_observed_timestamp", ""))
        current["last_observed_timestamp"] = _max_nonempty(current["last_observed_timestamp"], row.get("last_observed_timestamp", ""))
        current["first_contact_date"] = _min_nonempty(current["first_contact_date"], row.get("first_contact_date", ""))
        if current["first_contact_date"] == row.get("first_contact_date", ""):
            current["first_contact_source_path"] = row.get("first_contact_source_path", "") or current["first_contact_source_path"]
        current["source_packs"].update(_split_joined(row.get("source_pack", "")))
        for column in TEXT_JOIN_COLUMNS:
            current[column].update(_split_joined(row.get(column, "")))
        for column in (
            "identity_status",
            "display_name",
        ):
            if not current[column] and row.get(column):
                current[column] = row[column]

    merged = []
    for row in grouped.values():
        flat = {column: "" for column in OWNER_ROSTER_BATCH_COLUMNS}
        for column in flat:
            value = row.get(column, "")
            if isinstance(value, set):
                flat[column] = _join_values(value)
            else:
                flat[column] = str(value)
        flat["deleted_user_observed"] = "True" if row["deleted_user_observed"] else "False"
        merged.append(flat)

    merged.sort(key=lambda row: (0 if row["identity_status"] == "CONFIRMED_ACCOUNT_OWNER" else 1, -_as_int(row["observation_count"]), row["display_name"].lower()))
    return merged


def _empty_owner_row(row: dict[str, str]) -> dict[str, Any]:
    current: dict[str, Any] = {column: row.get(column, "") for column in OWNER_ROSTER_BATCH_COLUMNS}
    for column in TEXT_JOIN_COLUMNS:
        current[column] = set()
    current["source_packs"] = set()
    current["observation_count"] = 0
    current["variant_ids_count"] = 0
    current["deleted_user_observed"] = False
    return current


def _merge_unassigned(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row.get("related_id_type", ""), row.get("related_id_value", ""))
        current = grouped.setdefault(
            key,
            {
                "related_id_type": key[0],
                "related_id_value": key[1],
                "observation_count": 0,
                "first_observed_timestamp": "",
                "last_observed_timestamp": "",
                "contexts": set(),
                "names_seen_on_same_rows": set(),
                "source_packs": set(),
                "source_paths_sample": set(),
            },
        )
        current["observation_count"] += _as_int(row.get("observation_count"))
        current["first_observed_timestamp"] = _min_nonempty(current["first_observed_timestamp"], row.get("first_observed_timestamp", ""))
        current["last_observed_timestamp"] = _max_nonempty(current["last_observed_timestamp"], row.get("last_observed_timestamp", ""))
        for source, target in (
            ("contexts", "contexts"),
            ("names_seen_on_same_rows", "names_seen_on_same_rows"),
            ("source_pack", "source_packs"),
            ("source_packs", "source_packs"),
            ("source_paths_sample", "source_paths_sample"),
        ):
            current[target].update(_split_joined(row.get(source, "")))

    merged = []
    for row in grouped.values():
        merged.append(
            {
                "related_id_type": row["related_id_type"],
                "related_id_value": row["related_id_value"],
                "observation_count": str(row["observation_count"]),
                "first_observed_timestamp": row["first_observed_timestamp"],
                "last_observed_timestamp": row["last_observed_timestamp"],
                "contexts": _join_values(row["contexts"]),
                "names_seen_on_same_rows": _join_values(row["names_seen_on_same_rows"]),
                "source_packs": _join_values(row["source_packs"]),
                "source_paths_sample": _join_values(row["source_paths_sample"]),
            }
        )
    return sorted(merged, key=lambda row: (row["related_id_type"], row["related_id_value"]))


def _write_first_contact_text(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "OWNER IDENTITY FIRST-CONTACT TIMELINE",
        f"Generated: {_now()}",
        f"Rows: {len(rows)}",
        "",
    ]
    current_identity = None
    for row in rows:
        identity_label = f"{row.get('display_name', '')} [{row.get('identity_status', '')}]"
        if identity_label != current_identity:
            lines.extend(["", "=" * 88, identity_label])
            current_identity = identity_label
        related = ""
        if row.get("related_id_type") and row.get("related_id_value"):
            related = f" | {row['related_id_type']}={row['related_id_value']}"
        lines.append(
            (
                f"- {row.get('first_interaction_date') or 'undated'} | {row.get('variant_id', '')} | "
                f"{row.get('observation_type', '')}{related} | {row.get('source_path', '')}"
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_combined_owner_report(path: Path, output: Path, manifest: list[dict[str, Any]], roster: list[dict[str, str]]) -> None:
    lines = [
        "OWNER IDENTITY AND VARIANT CROSSCHECK",
        "",
        f"Generated: {_now()}",
        f"Batch output: {output}",
        "",
        "SCOPE",
        "- Built from completed extracted Facebook export folder runs.",
        "- Confirmed owner identity comes from native profile_information.json full_name evidence when present.",
        "- Other identities are observed/correlated variants and require source review.",
        "- Placeholder epoch dates such as 1970-01-01 are excluded from first-contact calculations.",
        "",
        "MASTER COUNTS",
        f"Source packs processed: {sum(1 for row in manifest if row['status'] == 'completed')}",
        f"Roster identities: {len(roster)}",
        "",
        "IDENTITY ROSTER - CONFIRMED OWNER FIRST, THEN OTHER IDENTIFIABLE VARIANTS",
        "Format: status | display name | obs | first contact | phones | FB/profile IDs | emails | other IDs sample",
    ]
    for row in roster[:100]:
        lines.append(
            (
                f"- {row.get('identity_status', '')} | {row.get('display_name', '')} | "
                f"obs={row.get('observation_count', '')} | first_contact={row.get('first_contact_date') or 'undated'} | "
                f"phones={row.get('phone_numbers_direct') or 'none'} | "
                f"fb/profile_ids={row.get('facebook_ids_observed') or 'none'} | "
                f"emails={row.get('emails_observed') or 'none'} | "
                f"other_ids={row.get('other_identifying_ids') or 'none'}"
            )
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _batch_counts(output: Path, common_parent: Path | None, manifest: list[dict[str, Any]], masters: dict[str, dict[str, Any]]) -> dict[str, Any]:
    completed = [row for row in manifest if row["status"] == "completed"]
    return {
        "batch_root": str(output),
        "source_folder": str(common_parent) if common_parent else "",
        "completed_source_count": len(completed),
        "skipped_source_count": sum(1 for row in manifest if row["status"] == "skipped_empty"),
        "sources": manifest,
        "masters": masters,
    }


def _source_file_counts(source: Path) -> tuple[int, int]:
    if source.is_file() and source.suffix.lower() == ".zip":
        import zipfile

        with zipfile.ZipFile(source) as archive:
            names = [name.lower() for name in archive.namelist()]
        return sum(name.endswith(".json") for name in names), sum(name.endswith(".html") for name in names)
    if not source.exists():
        return 0, 0
    files = [path.suffix.lower() for path in source.rglob("*") if path.is_file()]
    return files.count(".json"), files.count(".html")


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = {column: row.get(column, "") for column in columns} if columns else row
            handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def _split_joined(value: str) -> set[str]:
    return {part.strip() for part in str(value or "").split(" | ") if part.strip()}


def _join_values(values: Iterable[str]) -> str:
    return " | ".join(sorted({value for value in values if value}))


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _min_nonempty(left: str, right: str) -> str:
    if not left:
        return right
    if not right:
        return left
    return min(left, right)


def _max_nonempty(left: str, right: str) -> str:
    if not left:
        return right
    if not right:
        return left
    return max(left, right)


def _safe_name(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._-")
    return clean or "source"


def _unique_name(name: str, used: set[str]) -> str:
    candidate = name
    index = 2
    while candidate in used:
        candidate = f"{name}_{index}"
        index += 1
    used.add(candidate)
    return candidate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ordered_manifest_entry(row: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in RUN_SUMMARY_COLUMNS:
        if key in row:
            ordered[key] = row[key]
    for key, value in row.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _common_parent(paths: list[Path]) -> Path | None:
    parents = [path.parent.resolve() for path in paths if path.exists()]
    if not parents:
        return None
    first = parents[0]
    return first if all(parent == first for parent in parents) else None
