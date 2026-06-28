from __future__ import annotations

import csv
import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable


INTERACTION_PATH_HINTS = (
    "apps_and_websites_off_of_facebook/",
    "connections/followers/",
    "connections/friends/",
    "logged_information/activity_messages/",
    "logged_information/interactions/",
    "logged_information/notifications/",
    "logged_information/search/",
    "your_facebook_activity/comments_and_reactions/",
    "your_facebook_activity/facebook_gaming/",
    "your_facebook_activity/fundraisers/",
    "your_facebook_activity/groups/",
    "your_facebook_activity/navigation_bar/",
    "your_facebook_activity/posts/",
)

TIMESTAMP_KEYS = (
    "timestamp",
    "creation_timestamp",
    "timestamp_ms",
    "update_timestamp",
    "taken_timestamp",
    "upload_timestamp",
    "last_modified_timestamp",
)

TEXT_KEYS = (
    "title",
    "text",
    "comment",
    "name",
    "description",
    "reaction",
    "post",
    "label",
    "value",
)

CSV_COLUMNS = [
    "timestamp",
    "timestamp_raw",
    "interaction_type",
    "action",
    "actor",
    "target",
    "entity_name",
    "handle_or_identifier",
    "summary",
    "source_path",
    "source_sha256",
    "raw_payload_path",
]

ENTITY_COLUMNS = [
    "entity_name",
    "handle_or_identifier",
    "interaction_count",
    "first_timestamp",
    "last_timestamp",
    "interaction_types",
    "source_paths",
]


@dataclass(frozen=True)
class SourceJson:
    path: str
    sha256: str
    payload: Any


@dataclass(frozen=True)
class InteractionRecord:
    timestamp: str
    timestamp_raw: str
    interaction_type: str
    action: str
    actor: str
    target: str
    entity_name: str
    handle_or_identifier: str
    summary: str
    source_path: str
    source_sha256: str
    raw_payload_path: str


def process_export(source: Path, output: Path) -> dict[str, Any]:
    records = extract_interactions(source)
    entities = summarize_entities(records)
    output.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output / "interactions_by_timestamp.jsonl", records)
    _write_csv(output / "interactions_by_timestamp.csv", records)
    _write_json(output / "entity_interaction_summary.json", entities)
    _write_entity_csv(output / "entity_interaction_summary.csv", entities)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "interaction_count": len(records),
        "entity_count": len(entities),
        "first_timestamp": records[0].timestamp if records else "",
        "last_timestamp": records[-1].timestamp if records else "",
        "interaction_types": _type_counts(records),
    }
    (output / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def extract_interactions(source: Path) -> list[InteractionRecord]:
    records: list[InteractionRecord] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for item in _iter_source_json(source):
        if not _is_interaction_source(item.path):
            continue
        for record in _records_from_payload(item):
            key = (
                record.timestamp_raw,
                record.summary,
                record.interaction_type,
                record.source_path,
                record.raw_payload_path,
            )
            if key in seen:
                continue
            seen.add(key)
            records.append(record)
    return sorted(records, key=lambda row: row.timestamp or "9999")


def summarize_entities(records: list[InteractionRecord]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        name = record.entity_name or record.target or record.actor
        identifier = record.handle_or_identifier
        if not name and not identifier:
            continue
        key = (name, identifier)
        current = grouped.setdefault(
            key,
            {
                "entity_name": name,
                "handle_or_identifier": identifier,
                "interaction_count": 0,
                "first_timestamp": record.timestamp,
                "last_timestamp": record.timestamp,
                "interaction_types": set(),
                "source_paths": set(),
            },
        )
        current["interaction_count"] += 1
        if record.timestamp:
            timestamps = [value for value in (current["first_timestamp"], current["last_timestamp"], record.timestamp) if value]
            current["first_timestamp"] = min(timestamps)
            current["last_timestamp"] = max(timestamps)
        current["interaction_types"].add(record.interaction_type)
        current["source_paths"].add(record.source_path)

    rows = []
    for value in grouped.values():
        rows.append(
            {
                "entity_name": value["entity_name"],
                "handle_or_identifier": value["handle_or_identifier"],
                "interaction_count": value["interaction_count"],
                "first_timestamp": value["first_timestamp"],
                "last_timestamp": value["last_timestamp"],
                "interaction_types": sorted(value["interaction_types"]),
                "source_paths": sorted(value["source_paths"]),
            }
        )
    return sorted(rows, key=lambda row: (-row["interaction_count"], row["entity_name"], row["handle_or_identifier"]))


def _iter_source_json(source: Path) -> Iterable[SourceJson]:
    source = Path(source)
    if source.is_dir():
        for path in sorted(source.rglob("*.json")):
            data = path.read_bytes()
            try:
                payload = json.loads(data.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            yield SourceJson(path=path.relative_to(source).as_posix(), sha256=sha256(data).hexdigest(), payload=payload)
        return

    if source.is_file() and source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            for name in sorted(archive.namelist()):
                if not name.lower().endswith(".json"):
                    continue
                data = archive.read(name)
                try:
                    payload = json.loads(data.decode("utf-8-sig"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                yield SourceJson(path=name, sha256=sha256(data).hexdigest(), payload=payload)
        return

    raise ValueError(f"Source must be an extracted folder or .zip file: {source}")


def _records_from_payload(item: SourceJson) -> list[InteractionRecord]:
    records: list[InteractionRecord] = []
    for value, trail in _walk_dicts(item.payload, ""):
        timestamp_raw = _first_timestamp(value)
        if not timestamp_raw:
            continue
        summary = _first_text(value)
        actor = _first_text_for_keys(value, ("actor", "author", "sender_name"))
        target = _target_label(value)
        entity_name = target or actor
        identifier = _identifier_label(value)
        action = _action_label(value, summary)
        interaction_type = _interaction_type(trail, value)
        if not summary:
            summary = " ".join(part for part in (action, actor, target) if part)
        if not summary:
            continue
        records.append(
            InteractionRecord(
                timestamp=_timestamp_to_iso(timestamp_raw),
                timestamp_raw=timestamp_raw,
                interaction_type=interaction_type,
                action=action,
                actor=actor,
                target=target,
                entity_name=entity_name,
                handle_or_identifier=identifier,
                summary=summary,
                source_path=item.path,
                source_sha256=item.sha256,
                raw_payload_path=trail,
            )
        )
    return records


def _walk_dicts(value: Any, trail: str) -> Iterable[tuple[dict[str, Any], str]]:
    if isinstance(value, dict):
        yield value, trail
        for key, nested in value.items():
            child_trail = f"{trail}.{key}" if trail else key
            yield from _walk_dicts(nested, child_trail)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _walk_dicts(nested, f"{trail}[{index}]")


def _is_interaction_source(path: str) -> bool:
    lower = path.replace("\\", "/").lower()
    return any(hint in lower for hint in INTERACTION_PATH_HINTS)


def _first_timestamp(value: dict[str, Any]) -> str:
    for key in TIMESTAMP_KEYS:
        raw = value.get(key)
        if raw not in (None, "") and _is_plausible_timestamp(raw):
            return _safe_str(raw)
    return ""


def _first_text(value: dict[str, Any]) -> str:
    for key in TEXT_KEYS:
        text = _text_from_value(value.get(key))
        if text:
            return text
    return _text_from_value(value.get("data"))


def _first_text_for_keys(value: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _text_from_value(value.get(key))
        if text:
            return text
    return ""


def _target_label(value: dict[str, Any]) -> str:
    for key in ("group", "profile", "page", "target", "post", "name", "title"):
        text = _text_from_value(value.get(key))
        if text:
            return text
    return ""


def _identifier_label(value: dict[str, Any]) -> str:
    for key in ("handle", "username", "profile_id", "profile_identifier", "id", "url", "uri", "href"):
        text = _text_from_value(value.get(key))
        if text:
            return text
    for key in ("profile", "page", "target", "actor", "author"):
        nested = value.get(key)
        if isinstance(nested, dict):
            text = _identifier_label(nested)
            if text:
                return text
    return ""


def _action_label(value: dict[str, Any], summary: str) -> str:
    reaction = _text_from_value(value.get("reaction"))
    if reaction:
        return f"reaction:{reaction}"
    lowered = summary.lower()
    for token in ("comment", "like", "react", "follow", "friend", "view", "visit", "tag", "share"):
        if token in lowered:
            return token
    return ""


def _interaction_type(trail: str, value: dict[str, Any]) -> str:
    lower = trail.lower()
    if "notification" in lower:
        return "notification"
    if "reaction" in lower or value.get("reaction"):
        return "reaction"
    if "comment" in lower or value.get("comment"):
        return "comment"
    if "friend" in lower or "follow" in lower:
        return "connection"
    if "visited" in lower or "viewed" in lower:
        return "view_or_visit"
    if "group" in lower:
        return "group_activity"
    if "post" in lower:
        return "post_activity"
    return "interaction"


def _text_from_value(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float)):
        return _safe_str(value)
    if isinstance(value, dict):
        for key in ("name", "title", "text", "value", "description", "comment", "uri", "href"):
            text = _text_from_value(value.get(key))
            if text:
                return text
    if isinstance(value, list):
        for item in value:
            text = _text_from_value(item)
            if text:
                return text
    return ""


def _timestamp_to_iso(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return _safe_str(value)
    if number > 9999999999:
        dt = datetime.fromtimestamp(number / 1000, tz=timezone.utc)
    else:
        dt = datetime.fromtimestamp(number, tz=timezone.utc)
    return dt.isoformat()


def _is_plausible_timestamp(value: Any) -> bool:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return bool(_safe_str(value))
    return number > 0


def _write_jsonl(path: Path, records: list[InteractionRecord]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n")


def _write_csv(path: Path, records: list[InteractionRecord]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def _write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_entity_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ENTITY_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "interaction_types": ";".join(row["interaction_types"]),
                    "source_paths": ";".join(row["source_paths"]),
                }
            )


def _type_counts(records: list[InteractionRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.interaction_type] = counts.get(record.interaction_type, 0) + 1
    return dict(sorted(counts.items()))


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
