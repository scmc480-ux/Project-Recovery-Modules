from __future__ import annotations

import csv
import html
import ipaddress
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


IP_SOURCE_HINTS = (
    "security_and_login_information/",
    "logged_information/location/",
    "logged_information/other_logged_information/locations",
    "ads_information/your_sampled_locations",
    "personal_information/profile_information/your_devices",
    "your_facebook_activity/messages/information_about_your_devices",
    "your_facebook_activity/facebook_marketplace/your_marketplace_device_history",
)

IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|(?<![:\w])(?:[a-f0-9]{1,4}:){2,7}[a-f0-9]{1,4}(?![:\w])", re.IGNORECASE)
COORD_RE = re.compile(r"(?P<lat>-?\d{1,2}\.\d+)\s*,\s*(?P<lon>-?\d{1,3}\.\d+)")

TIMESTAMP_KEYS = (
    "timestamp",
    "time",
    "date",
    "created_timestamp",
    "creation_timestamp",
    "last_active_timestamp",
    "login_timestamp",
)

IP_KEYS = ("ip", "ip_address", "ipAddress", "ip_address_v4", "ip_address_v6")
DEVICE_KEYS = ("device", "device_label", "device_name", "device_type", "hardware", "user_agent")
SESSION_KEYS = ("session", "session_id", "cookie", "login_cookie")
BROWSER_KEYS = ("browser", "browser_name", "user_agent")
LOCATION_KEYS = ("location", "city", "region", "country", "approximate_location")
PRECISE_LOCATION_KEYS = ("precise_location", "coordinates", "latitude", "longitude", "lat", "lon", "lng")

OBSERVATION_COLUMNS = [
    "timestamp",
    "timestamp_raw",
    "ip_address",
    "ip_version",
    "location_signal_type",
    "source_path",
    "source_sha256",
    "raw_payload_path",
    "device_label",
    "session_label",
    "browser_label",
    "approximate_location",
    "precise_location",
    "confidence",
    "explanation",
]

CORRELATION_COLUMNS = [
    "correlation_id",
    "label",
    "confidence",
    "ip_addresses",
    "observation_count",
    "first_timestamp",
    "last_timestamp",
    "source_paths",
    "explanation",
]


@dataclass(frozen=True)
class SourceItem:
    path: str
    sha256: str
    suffix: str
    payload: Any


@dataclass(frozen=True)
class IpObservation:
    timestamp: str
    timestamp_raw: str
    ip_address: str
    ip_version: str
    location_signal_type: str
    source_path: str
    source_sha256: str
    raw_payload_path: str
    device_label: str
    session_label: str
    browser_label: str
    approximate_location: str
    precise_location: str
    confidence: str
    explanation: str


@dataclass(frozen=True)
class CorrelationRecord:
    correlation_id: str
    label: str
    confidence: str
    ip_addresses: str
    observation_count: int
    first_timestamp: str
    last_timestamp: str
    source_paths: str
    explanation: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tokens: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(html.unescape(data).split())
        if value:
            self.tokens.append(value)


def process_export(source: Path, output: Path) -> dict[str, Any]:
    observations = extract_observations(source)
    correlations = correlate_observations(observations)
    output.mkdir(parents=True, exist_ok=True)

    _write_jsonl(output / "ip_observations.jsonl", observations)
    _write_csv(output / "ip_observations.csv", observations, OBSERVATION_COLUMNS)
    _write_json(output / "ip_correlation_summary.json", correlations)
    _write_csv(output / "ip_correlation_summary.csv", correlations, CORRELATION_COLUMNS)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "observation_count": len(observations),
        "correlation_count": len(correlations),
        "first_timestamp": _first_timestamp(observations),
        "last_timestamp": _last_timestamp(observations),
        "confidence_counts": _confidence_counts(observations),
    }
    (output / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def extract_observations(source: Path) -> list[IpObservation]:
    records: list[IpObservation] = []
    seen: set[tuple[str, str, str, str]] = set()
    for item in _iter_source_items(source):
        if not _is_ip_source(item.path):
            continue
        if item.suffix == ".json":
            item_records = _json_observations(item)
        elif item.suffix in {".html", ".htm"}:
            item_records = _html_observations(item)
        else:
            item_records = []
        for record in item_records:
            key = (record.ip_address, record.timestamp_raw, record.source_path, record.raw_payload_path)
            if key in seen:
                continue
            seen.add(key)
            records.append(record)
    return sorted(records, key=lambda row: (row.timestamp == "", row.timestamp))


def correlate_observations(observations: list[IpObservation]) -> list[CorrelationRecord]:
    rows: list[CorrelationRecord] = []
    rows.extend(_correlate_by_exact_ip(observations))
    rows.extend(_correlate_by_subnet(observations))
    return sorted(rows, key=lambda row: (row.label, row.correlation_id))


def _iter_source_items(source: Path) -> Iterable[SourceItem]:
    source = Path(source)
    suffixes = {".json", ".html", ".htm"}
    if source.is_dir():
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            relative_path = path.relative_to(source).as_posix()
            if not _is_ip_source(relative_path):
                continue
            data = path.read_bytes()
            payload = _decode_payload(data, path.suffix.lower())
            if payload is None:
                continue
            yield SourceItem(path=relative_path, sha256=sha256(data).hexdigest(), suffix=path.suffix.lower(), payload=payload)
        return

    if source.is_file() and source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            for name in sorted(archive.namelist()):
                suffix = Path(name).suffix.lower()
                if suffix not in suffixes:
                    continue
                if not _is_ip_source(name):
                    continue
                data = archive.read(name)
                payload = _decode_payload(data, suffix)
                if payload is None:
                    continue
                yield SourceItem(path=name, sha256=sha256(data).hexdigest(), suffix=suffix, payload=payload)
        return

    raise ValueError(f"Source must be an extracted folder or .zip file: {source}")


def _decode_payload(data: bytes, suffix: str) -> Any | None:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    if suffix == ".json":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    return text


def _is_ip_source(path: str) -> bool:
    lower = path.replace("\\", "/").lower()
    return any(hint in lower for hint in IP_SOURCE_HINTS)


def _json_observations(item: SourceItem) -> list[IpObservation]:
    rows: list[IpObservation] = []
    for value, trail in _walk_dicts(item.payload, ""):
        ip = _first_for_keys(value, IP_KEYS)
        if not ip and not _has_nested_container(value):
            text_ip = IP_RE.search(json.dumps(value, ensure_ascii=False))
            ip = text_ip.group(0) if text_ip else ""
        if not _valid_ip(ip):
            continue
        rows.append(
            _make_observation(
                item=item,
                raw_payload_path=trail,
                ip_address=ip,
                timestamp_raw=_first_for_keys(value, TIMESTAMP_KEYS),
                device_label=_first_for_keys(value, DEVICE_KEYS),
                session_label=_first_for_keys(value, SESSION_KEYS),
                browser_label=_first_for_keys(value, BROWSER_KEYS),
                approximate_location=_first_for_keys(value, LOCATION_KEYS),
                precise_location=_precise_location(value),
            )
        )
    return rows


def _html_observations(item: SourceItem) -> list[IpObservation]:
    parser = _TextExtractor()
    parser.feed(str(item.payload))
    return [_make_observation(item=item, raw_payload_path=f"html_record[{index}]", **record) for index, record in enumerate(_records_from_tokens(parser.tokens))]


def _records_from_tokens(tokens: list[str]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        label = _label_name(token)
        if label:
            if label in {"timestamp_raw", "time"} and current.get("ip_address"):
                records.append(current)
                current = {}
            value = _next_value(tokens, index)
            if value:
                if label == "time":
                    label = "timestamp_raw"
                current[label] = value
            index += 2
            continue
        ip_match = IP_RE.search(token)
        if ip_match and _valid_ip(ip_match.group(0)):
            current["ip_address"] = ip_match.group(0)
        coord_match = COORD_RE.search(token)
        if coord_match:
            current["precise_location"] = coord_match.group(0)
        index += 1
    if current.get("ip_address"):
        records.append(current)
    return records


def _label_name(token: str) -> str:
    normalized = token.strip().lower().rstrip(":")
    mapping = {
        "time": "time",
        "date": "timestamp_raw",
        "timestamp": "timestamp_raw",
        "ip": "ip_address",
        "ip address": "ip_address",
        "browser": "browser_label",
        "device": "device_label",
        "device name": "device_label",
        "session": "session_label",
        "session id": "session_label",
        "location": "approximate_location",
        "city": "approximate_location",
        "region": "approximate_location",
        "country": "approximate_location",
        "precise location": "precise_location",
        "coordinates": "precise_location",
    }
    return mapping.get(normalized, "")


def _next_value(tokens: list[str], index: int) -> str:
    if index + 1 >= len(tokens):
        return ""
    value = tokens[index + 1].strip()
    if _label_name(value):
        return ""
    return value


def _make_observation(
    *,
    item: SourceItem,
    raw_payload_path: str,
    ip_address: str,
    timestamp_raw: str = "",
    device_label: str = "",
    session_label: str = "",
    browser_label: str = "",
    approximate_location: str = "",
    precise_location: str = "",
) -> IpObservation:
    ip_obj = ipaddress.ip_address(ip_address)
    confidence, explanation = _confidence_and_explanation(ip_address, timestamp_raw, device_label, session_label, precise_location, approximate_location)
    return IpObservation(
        timestamp=_timestamp_to_iso(timestamp_raw),
        timestamp_raw=timestamp_raw,
        ip_address=ip_address,
        ip_version=f"IPv{ip_obj.version}",
        location_signal_type=_location_signal_type(precise_location, approximate_location),
        source_path=item.path,
        source_sha256=item.sha256,
        raw_payload_path=raw_payload_path,
        device_label=device_label,
        session_label=session_label,
        browser_label=browser_label,
        approximate_location=approximate_location,
        precise_location=precise_location,
        confidence=confidence,
        explanation=explanation,
    )


def _confidence_and_explanation(ip: str, timestamp: str, device: str, session: str, precise: str, approximate: str) -> tuple[str, str]:
    if precise:
        return "high", "Explicit precise-location evidence is present with the IP observation."
    if ip and timestamp and (device or session):
        return "high", "IP observation includes timestamp plus device or session context."
    if ip and timestamp:
        return "medium", "IP observation includes timestamp context."
    if approximate:
        return "low", "IP observation includes approximate location only."
    return "low", "IP observation has limited context."


def _location_signal_type(precise: str, approximate: str) -> str:
    if precise:
        return "precise_device_location"
    if approximate:
        return "ip_or_profile_approximate_location"
    return "ip_only"


def _walk_dicts(value: Any, trail: str) -> Iterable[tuple[dict[str, Any], str]]:
    if isinstance(value, dict):
        yield value, trail
        for key, nested in value.items():
            child_trail = f"{trail}.{key}" if trail else key
            yield from _walk_dicts(nested, child_trail)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _walk_dicts(nested, f"{trail}[{index}]")


def _has_nested_container(value: dict[str, Any]) -> bool:
    return any(isinstance(item, (dict, list)) for item in value.values())


def _first_for_keys(value: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        if key in value:
            text = _text_from_value(value.get(key))
            if text:
                return text
    return ""


def _precise_location(value: dict[str, Any]) -> str:
    lat = _text_from_value(value.get("latitude") or value.get("lat"))
    lon = _text_from_value(value.get("longitude") or value.get("lon") or value.get("lng"))
    if lat and lon:
        return f"{lat},{lon}"
    for key in PRECISE_LOCATION_KEYS:
        text = _text_from_value(value.get(key))
        if COORD_RE.search(text):
            return text
    return ""


def _text_from_value(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        for key in ("name", "title", "text", "value", "description", "label", "uri", "href"):
            text = _text_from_value(value.get(key))
            if text:
                return text
    if isinstance(value, list):
        for item in value:
            text = _text_from_value(item)
            if text:
                return text
    return ""


def _timestamp_to_iso(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        number = int(value)
    except ValueError:
        parsed = _parse_datetime(value)
        return parsed.isoformat() if parsed else value
    if number > 9999999999:
        return datetime.fromtimestamp(number / 1000, tz=timezone.utc).isoformat()
    return datetime.fromtimestamp(number, tz=timezone.utc).isoformat()


def _parse_datetime(value: str) -> datetime | None:
    normalized = value.replace(" at ", " ").replace(",", "")
    formats = (
        "%b %d %Y %I:%M %p",
        "%b %d %Y %I:%M:%S %p",
        "%B %d %Y %I:%M %p",
        "%B %d %Y %I:%M:%S %p",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    )
    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def _network_key(value: str) -> str:
    ip_obj = ipaddress.ip_address(value)
    if ip_obj.version == 4:
        return str(ipaddress.ip_network(f"{value}/24", strict=False))
    return str(ipaddress.ip_network(f"{value}/64", strict=False))


def _correlate_by_exact_ip(observations: list[IpObservation]) -> list[CorrelationRecord]:
    grouped: dict[str, list[IpObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.ip_address, []).append(observation)
    return [
        _correlation_row(label="same_ip", key=ip, rows=rows, confidence="medium")
        for ip, rows in grouped.items()
        if len(rows) > 1
    ]


def _correlate_by_subnet(observations: list[IpObservation]) -> list[CorrelationRecord]:
    grouped: dict[str, list[IpObservation]] = {}
    for observation in observations:
        grouped.setdefault(_network_key(observation.ip_address), []).append(observation)
    rows = []
    for network, values in grouped.items():
        if len({row.ip_address for row in values}) > 1:
            rows.append(_correlation_row(label="same_subnet", key=network, rows=values, confidence="low"))
    return rows


def _correlation_row(label: str, key: str, rows: list[IpObservation], confidence: str) -> CorrelationRecord:
    timestamps = [row.timestamp for row in rows if row.timestamp]
    sources = sorted({row.source_path for row in rows})
    ips = sorted({row.ip_address for row in rows})
    return CorrelationRecord(
        correlation_id=f"{label}:{key}",
        label=label,
        confidence=confidence,
        ip_addresses=";".join(ips),
        observation_count=len(rows),
        first_timestamp=min(timestamps) if timestamps else "",
        last_timestamp=max(timestamps) if timestamps else "",
        source_paths=";".join(sources),
        explanation=f"{len(rows)} observations share {label.replace('_', ' ')} evidence. This is correlation, not proof of physical proximity.",
    )


def _write_jsonl(path: Path, rows: list[Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), ensure_ascii=False, sort_keys=True) + "\n")


def _write_json(path: Path, rows: list[Any]) -> None:
    path.write_text(json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[Any], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _confidence_counts(rows: list[IpObservation]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.confidence] = counts.get(row.confidence, 0) + 1
    return dict(sorted(counts.items()))


def _first_timestamp(rows: list[IpObservation]) -> str:
    timestamps = [row.timestamp for row in rows if row.timestamp]
    return min(timestamps) if timestamps else ""


def _last_timestamp(rows: list[IpObservation]) -> str:
    timestamps = [row.timestamp for row in rows if row.timestamp]
    return max(timestamps) if timestamps else ""
