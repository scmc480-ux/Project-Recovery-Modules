from __future__ import annotations

import csv
import html
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


IDENTITY_SOURCE_HINTS = (
    "connections/",
    "logged_information/notifications/",
    "logged_information/interactions/",
    "logged_information/search/",
    "notifications/",
    "ads_information/",
    "apps_and_websites/",
    "personal_information/",
    "security_and_login_information/",
    "your_facebook_activity/comments_and_reactions/",
    "your_facebook_activity/events/",
    "your_facebook_activity/facebook_marketplace/",
    "your_facebook_activity/groups/",
    "your_facebook_activity/likes_and_reactions/",
    "your_facebook_activity/marketplace/",
    "your_facebook_activity/messages/",
    "your_facebook_activity/pages/",
    "your_facebook_activity/photos_and_videos/",
    "your_facebook_activity/posts/",
    "your_facebook_activity/reels/",
)

IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
FB_ID_RE = re.compile(r"(?<!\d)(\d{6,})(?!\d)")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d .()\-]{7,}\d(?!\w)")
THREAD_DIR_RE = re.compile(r"(?:^|/)(?:inbox|archived_threads|e2ee_cutover)/([^/]+?)(?:_(\d{6,}))?/message_\d+\.html$", re.IGNORECASE)
DELETED_RE = re.compile(r"\b(deleted user|facebook user|unknown user|unavailable user)\b", re.IGNORECASE)
PROFILE_SLUG_RE = re.compile(r"(?:facebook\.com/|fb\.com/|profile/)(?!profile\.php)([A-Za-z0-9_.-]+)", re.IGNORECASE)
URL_ID_RE = re.compile(
    r"(?:[?&/](?P<key>"
    r"id|fbid|story_fbid|comment_id|reply_comment_id|post_id|photo_id|video_id|story_id|"
    r"group_id|page_id|event_id|listing_id|marketplace_listing_id|notification_id|notif_id|"
    r"account_id|actor_id|app_id|attachment_id|browser_id|business_id|buyer_id|checkin_id|"
    r"contact_id|cookie_id|device_id|external_id|invite_id|like_id|location_id|owner_id|"
    r"managed_approved_user_id|multi_permalinks|neo_managed_approved_user_id|payment_id|place_id|"
    r"reaction_id|ref_profile_id|session_id|settings_notif_id|share_id|seller_id|source_id|target_id|"
    r"transaction_id|v"
    r")[=/])(?P<value>\d{5,})",
    re.IGNORECASE,
)
URL_ROUTE_ID_RE = re.compile(
    r"facebook\.com/(?:"
    r"groups|events|pages|posts|photos|videos|reel|reels|watch|permalink|marketplace/item"
    r")/(?P<value>\d{5,})",
    re.IGNORECASE,
)
PATH_ID_RE = re.compile(
    r"(?:^|/)(?P<kind>"
    r"marketplace|listings|posts|comments|photos|videos|stories|groups|pages|events|notifications|tags|reels|likes|reactions|shares|checkins|places|sessions|devices|apps|payments|orders"
    r")[_/-](?P<id>\d{5,})(?:/|$)",
    re.IGNORECASE,
)

TIMESTAMP_KEYS = ("timestamp", "time", "date", "created_timestamp", "creation_timestamp", "updated_timestamp")
NAME_KEYS = ("name", "full_name", "display_name", "title", "sender_name", "actor", "author")
ID_KEYS = ("facebook_id", "profile_id", "user_id", "uid", "profile_identifier")
HANDLE_KEYS = ("handle", "username")
PROFILE_URL_KEYS = ("profile_url", "url", "uri", "href")
IP_KEYS = ("ip", "ip_address", "ipAddress")
RESERVED_FACEBOOK_SLUGS = {
    "events",
    "groups",
    "marketplace",
    "messages",
    "notifications",
    "pages",
    "photo.php",
    "photos",
    "posts",
    "reel",
    "story.php",
    "watch",
}
RELATED_ID_KEYS = {
    "account_id": "account_id",
    "actor_id": "actor_id",
    "ad_id": "ad_id",
    "app_id": "app_id",
    "application_id": "app_id",
    "attachment_id": "attachment_id",
    "author_id": "author_id",
    "browser_id": "browser_id",
    "business_id": "business_id",
    "buyer_id": "buyer_id",
    "checkin_id": "checkin_id",
    "comment_id": "comment_id",
    "contact_id": "contact_id",
    "conversation_id": "conversation_id",
    "cookie_id": "cookie_id",
    "device_id": "device_id",
    "email": "email_address",
    "email_address": "email_address",
    "event_id": "event_id",
    "external_id": "external_id",
    "fbid": "fbid",
    "group_id": "group_id",
    "invite_id": "invite_id",
    "invitation_id": "invite_id",
    "like_id": "like_id",
    "listing_id": "marketplace_listing_id",
    "location_id": "location_id",
    "marketplace_listing_id": "marketplace_listing_id",
    "member_id": "member_id",
    "message_id": "message_id",
    "multi_permalinks": "post_id",
    "neo_managed_approved_user_id": "managed_user_id",
    "notification_id": "notification_id",
    "notif_id": "notification_id",
    "order_id": "order_id",
    "owner_id": "owner_id",
    "page_id": "page_id",
    "payment_id": "payment_id",
    "phone": "phone_number",
    "phone_number": "phone_number",
    "photo_id": "photo_id",
    "place_id": "place_id",
    "post_id": "post_id",
    "product_id": "marketplace_product_id",
    "profile_id": "profile_id",
    "reaction_id": "reaction_id",
    "ref_profile_id": "profile_id",
    "reply_comment_id": "reply_comment_id",
    "seller_id": "seller_id",
    "session_id": "session_id",
    "settings_notif_id": "notification_id",
    "share_id": "share_id",
    "source_id": "source_id",
    "story_fbid": "story_fbid",
    "story_id": "story_id",
    "tag_id": "tag_id",
    "tagged_user_id": "tagged_user_id",
    "target_id": "target_id",
    "thread_id": "thread_id",
    "transaction_id": "transaction_id",
    "v": "video_id",
    "video_id": "video_id",
}
PATH_ID_TYPES = {
    "comments": "comment_id",
    "events": "event_id",
    "apps": "app_id",
    "checkins": "checkin_id",
    "devices": "device_id",
    "groups": "group_id",
    "likes": "like_id",
    "listings": "marketplace_listing_id",
    "marketplace": "marketplace_listing_id",
    "notifications": "notification_id",
    "orders": "order_id",
    "pages": "page_id",
    "payments": "payment_id",
    "places": "place_id",
    "photos": "photo_id",
    "posts": "post_id",
    "reactions": "reaction_id",
    "reels": "reel_id",
    "sessions": "session_id",
    "shares": "share_id",
    "stories": "story_id",
    "tags": "tag_id",
    "videos": "video_id",
}

OBSERVATION_COLUMNS = [
    "timestamp",
    "timestamp_raw",
    "observation_type",
    "entity_key",
    "facebook_id",
    "name",
    "normalized_name",
    "handle_or_identifier",
    "profile_url",
    "vanity_slug",
    "thread_identifier",
    "participant_context",
    "ip_address",
    "related_id_type",
    "related_id_value",
    "related_id_context",
    "deleted_user_observed",
    "source_path",
    "source_sha256",
    "raw_payload_path",
    "confidence",
    "explanation",
]

SUMMARY_COLUMNS = [
    "entity_key",
    "variant_type",
    "observation_count",
    "facebook_ids",
    "names",
    "handles_or_identifiers",
    "profile_urls",
    "vanity_slugs",
    "thread_identifiers",
    "participant_contexts",
    "ip_addresses",
    "related_ids",
    "deleted_user_observed",
    "first_timestamp",
    "last_timestamp",
    "source_paths",
    "confidence",
    "explanation",
]

TIMELINE_COLUMNS = [
    "variant_id",
    "variant_id_type",
    "variant_id_value",
    "interaction_date",
    "timestamp",
    "timestamp_raw",
    "observation_type",
    "entity_key",
    "facebook_id",
    "name",
    "normalized_name",
    "handle_or_identifier",
    "profile_url",
    "vanity_slug",
    "thread_identifier",
    "participant_context",
    "ip_address",
    "related_id_type",
    "related_id_value",
    "related_id_context",
    "deleted_user_observed",
    "source_path",
    "source_sha256",
    "raw_payload_path",
    "confidence",
    "explanation",
]

OWNER_ROSTER_COLUMNS = [
    "identity_status",
    "identity_key",
    "display_name",
    "master_identity_key",
    "master_identity_name",
    "alias_cluster_id",
    "alias_cluster_confidence",
    "alias_cluster_explanation",
    "alias_cluster_evidence",
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
    "source_paths_sample",
    "deleted_user_observed",
]

MASTER_ALIAS_CLUSTER_COLUMNS = [
    "alias_cluster_id",
    "master_identity_key",
    "master_identity_name",
    "alias_identity_keys",
    "alias_display_names",
    "observation_count",
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
    "source_paths_sample",
    "alias_cluster_confidence",
    "alias_cluster_explanation",
    "alias_cluster_evidence",
]

FIRST_CONTACT_COLUMNS = [
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
    "source_path",
    "evidence_name",
    "profile_url",
    "thread_identifier",
    "ip_address",
]

MASTER_FIRST_CONTACT_COLUMNS = [
    "master_identity_key",
    "master_identity_name",
    "alias_identity_key",
    "alias_display_name",
    "alias_cluster_id",
    "alias_cluster_confidence",
    "variant_id",
    "variant_id_type",
    "variant_id_value",
    "first_interaction_date",
    "timestamp",
    "observation_type",
    "related_id_type",
    "related_id_value",
    "related_id_context",
    "source_path",
    "evidence_name",
    "profile_url",
    "thread_identifier",
    "ip_address",
]

UNASSIGNED_ID_COLUMNS = [
    "related_id_type",
    "related_id_value",
    "observation_count",
    "first_observed_timestamp",
    "last_observed_timestamp",
    "contexts",
    "names_seen_on_same_rows",
    "source_paths_sample",
]

ACTION_NAME_TOKENS = (
    " liked ",
    " commented ",
    " posted ",
    " shared ",
    " updated ",
    " replied ",
    " reacted ",
    " tagged ",
    " invited ",
    " joined ",
    " viewed ",
    " watched ",
)

NON_PERSON_NAMES = {
    "ad",
    "ads",
    "attachments",
    "comments",
    "contacts",
    "cover photos",
    "facebook",
    "groups",
    "likes",
    "marketplace",
    "media",
    "messenger",
    "mobile uploads",
    "notifications",
    "original author",
    "owner",
    "photos",
    "posts",
    "profile",
    "profile pictures",
    "question",
    "shares",
    "stories",
    "story",
    "timeline photos",
    "videos",
}

OWNER_PROFILE_SOURCE = "personal_information/profile_information/profile_information.json"
OWNER_AFFILIATED_SOURCES = {
    OWNER_PROFILE_SOURCE,
    "personal_information/facebook_accounts_center/your_account_password_information.json",
    "personal_information/other_personal_information/emails_we_sent_you.json",
}
EPOCH_INTERACTION_DATES = {"1969-12-31", "1970-01-01"}
ALIAS_SESSION_SECONDS = 3600


@dataclass(frozen=True)
class SourceItem:
    path: str
    sha256: str
    suffix: str
    payload: Any


@dataclass(frozen=True)
class IdentityObservation:
    timestamp: str
    timestamp_raw: str
    observation_type: str
    entity_key: str
    facebook_id: str
    name: str
    normalized_name: str
    handle_or_identifier: str
    profile_url: str
    vanity_slug: str
    thread_identifier: str
    participant_context: str
    ip_address: str
    related_id_type: str
    related_id_value: str
    related_id_context: str
    deleted_user_observed: bool
    source_path: str
    source_sha256: str
    raw_payload_path: str
    confidence: str
    explanation: str


@dataclass(frozen=True)
class VariantSummary:
    entity_key: str
    variant_type: str
    observation_count: int
    facebook_ids: str
    names: str
    handles_or_identifiers: str
    profile_urls: str
    vanity_slugs: str
    thread_identifiers: str
    participant_contexts: str
    ip_addresses: str
    related_ids: str
    deleted_user_observed: bool
    first_timestamp: str
    last_timestamp: str
    source_paths: str
    confidence: str
    explanation: str


@dataclass(frozen=True)
class VariantTimelineRow:
    variant_id: str
    variant_id_type: str
    variant_id_value: str
    interaction_date: str
    timestamp: str
    timestamp_raw: str
    observation_type: str
    entity_key: str
    facebook_id: str
    name: str
    normalized_name: str
    handle_or_identifier: str
    profile_url: str
    vanity_slug: str
    thread_identifier: str
    participant_context: str
    ip_address: str
    related_id_type: str
    related_id_value: str
    related_id_context: str
    deleted_user_observed: bool
    source_path: str
    source_sha256: str
    raw_payload_path: str
    confidence: str
    explanation: str


@dataclass(frozen=True)
class OwnerIdentityRow:
    identity_status: str
    identity_key: str
    display_name: str
    master_identity_key: str
    master_identity_name: str
    alias_cluster_id: str
    alias_cluster_confidence: str
    alias_cluster_explanation: str
    alias_cluster_evidence: str
    all_name_variants: str
    observation_count: int
    first_observed_timestamp: str
    last_observed_timestamp: str
    first_contact_date: str
    first_contact_source_path: str
    facebook_ids_observed: str
    phone_numbers_direct: str
    phone_number_candidates: str
    emails_observed: str
    profile_urls: str
    vanity_slugs: str
    thread_identifiers: str
    ip_addresses: str
    other_identifying_ids: str
    variant_ids_count: int
    variant_ids_sample: str
    source_paths_sample: str
    deleted_user_observed: bool


@dataclass(frozen=True)
class MasterIdentityAliasClusterRow:
    alias_cluster_id: str
    master_identity_key: str
    master_identity_name: str
    alias_identity_keys: str
    alias_display_names: str
    observation_count: int
    first_contact_date: str
    first_contact_source_path: str
    facebook_ids_observed: str
    phone_numbers_direct: str
    phone_number_candidates: str
    emails_observed: str
    profile_urls: str
    vanity_slugs: str
    thread_identifiers: str
    ip_addresses: str
    other_identifying_ids: str
    source_paths_sample: str
    alias_cluster_confidence: str
    alias_cluster_explanation: str
    alias_cluster_evidence: str


@dataclass(frozen=True)
class IdentityFirstContactRow:
    identity_key: str
    display_name: str
    identity_status: str
    variant_id: str
    variant_id_type: str
    variant_id_value: str
    first_interaction_date: str
    timestamp: str
    observation_type: str
    related_id_type: str
    related_id_value: str
    related_id_context: str
    source_path: str
    evidence_name: str
    profile_url: str
    thread_identifier: str
    ip_address: str


@dataclass(frozen=True)
class MasterIdentityFirstContactRow:
    master_identity_key: str
    master_identity_name: str
    alias_identity_key: str
    alias_display_name: str
    alias_cluster_id: str
    alias_cluster_confidence: str
    variant_id: str
    variant_id_type: str
    variant_id_value: str
    first_interaction_date: str
    timestamp: str
    observation_type: str
    related_id_type: str
    related_id_value: str
    related_id_context: str
    source_path: str
    evidence_name: str
    profile_url: str
    thread_identifier: str
    ip_address: str


@dataclass(frozen=True)
class UnassignedIdVariantRow:
    related_id_type: str
    related_id_value: str
    observation_count: int
    first_observed_timestamp: str
    last_observed_timestamp: str
    contexts: str
    names_seen_on_same_rows: str
    source_paths_sample: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tokens: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(html.unescape(data).split())
        if value:
            self.tokens.append(value)


def process_export(source: Path, output: Path, alias_map: Path | None = None) -> dict[str, Any]:
    observations = extract_observations(source)
    summaries = summarize_variants(observations)
    timeline = build_variant_timeline(observations)
    alias_rules = load_alias_rules(alias_map or _default_alias_map_path(source))
    owner_roster, first_contacts, unassigned_ids, owner_report, alias_clusters, master_first_contacts = build_owner_identity_crosscheck(
        observations,
        timeline,
        alias_rules,
    )
    output.mkdir(parents=True, exist_ok=True)

    _write_jsonl(output / "identity_observations.jsonl", observations)
    _write_csv(output / "identity_observations.csv", observations, OBSERVATION_COLUMNS)
    _write_json(output / "identity_variant_summary.json", summaries)
    _write_csv(output / "identity_variant_summary.csv", summaries, SUMMARY_COLUMNS)
    _write_jsonl(output / "identity_variant_timeline.jsonl", timeline)
    _write_csv(output / "identity_variant_timeline.csv", timeline, TIMELINE_COLUMNS)
    _write_json(output / "owner_identity_roster.json", owner_roster)
    _write_csv(output / "owner_identity_roster.csv", owner_roster, OWNER_ROSTER_COLUMNS)
    _write_jsonl(output / "owner_identity_first_contact_timeline.jsonl", first_contacts)
    _write_csv(output / "owner_identity_first_contact_timeline.csv", first_contacts, FIRST_CONTACT_COLUMNS)
    _write_json(output / "owner_identity_unassigned_id_variants.json", unassigned_ids)
    _write_csv(output / "owner_identity_unassigned_id_variants.csv", unassigned_ids, UNASSIGNED_ID_COLUMNS)
    (output / "owner_identity_crosscheck_report.txt").write_text(owner_report, encoding="utf-8")
    _write_json(output / "master_identity_alias_clusters.json", alias_clusters)
    _write_csv(output / "master_identity_alias_clusters.csv", alias_clusters, MASTER_ALIAS_CLUSTER_COLUMNS)
    _write_jsonl(output / "master_identity_first_contact_timeline.jsonl", master_first_contacts)
    _write_csv(output / "master_identity_first_contact_timeline.csv", master_first_contacts, MASTER_FIRST_CONTACT_COLUMNS)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "observation_count": len(observations),
        "variant_group_count": len(summaries),
        "variant_timeline_row_count": len(timeline),
        "variant_timeline_id_count": len({row.variant_id for row in timeline}),
        "owner_identity_roster_count": len(owner_roster),
        "owner_identity_first_contact_count": len(first_contacts),
        "owner_identity_unassigned_id_count": len(unassigned_ids),
        "master_identity_alias_cluster_count": len(alias_clusters),
        "master_identity_first_contact_count": len(master_first_contacts),
        "deleted_user_observation_count": sum(1 for row in observations if row.deleted_user_observed),
        "facebook_id_count": len({row.facebook_id for row in observations if row.facebook_id}),
        "ip_address_count": len({row.ip_address for row in observations if row.ip_address}),
        "related_id_count": len({_format_related_id(row) for row in observations if row.related_id_value}),
        "first_timestamp": _first_timestamp(observations),
        "last_timestamp": _last_timestamp(observations),
    }
    (output / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def extract_observations(source: Path) -> list[IdentityObservation]:
    records: list[IdentityObservation] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for item in _iter_source_items(source):
        if item.suffix == ".json":
            item_records = _json_observations(item)
        elif item.suffix in {".html", ".htm"}:
            item_records = _html_observations(item)
        else:
            item_records = []
        item_records.extend(_path_observations(item))
        for record in item_records:
            key = (
                record.entity_key,
                record.name,
                record.facebook_id,
                record.profile_url,
                record.thread_identifier,
                record.ip_address,
                record.related_id_type,
                record.related_id_value,
                record.raw_payload_path,
            )
            if key in seen:
                continue
            seen.add(key)
            records.append(record)
    return sorted(records, key=lambda row: (row.timestamp == "", row.timestamp, row.entity_key))


def summarize_variants(observations: list[IdentityObservation]) -> list[VariantSummary]:
    grouped: dict[str, list[IdentityObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.entity_key, []).append(observation)

    summaries = [_summary_row(entity_key, rows) for entity_key, rows in grouped.items()]
    summaries.extend(_cross_identity_summaries(observations))
    return sorted(summaries, key=lambda row: (row.variant_type, row.entity_key))


def build_variant_timeline(observations: list[IdentityObservation]) -> list[VariantTimelineRow]:
    rows: list[VariantTimelineRow] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for observation in observations:
        for variant_id_type, variant_id_value in _variant_anchors(observation):
            variant_id = f"{variant_id_type}:{variant_id_value}"
            key = (
                variant_id,
                observation.timestamp,
                observation.source_path,
                observation.raw_payload_path,
                observation.observation_type,
            )
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                VariantTimelineRow(
                    variant_id=variant_id,
                    variant_id_type=variant_id_type,
                    variant_id_value=variant_id_value,
                    interaction_date=_interaction_date(observation.timestamp),
                    timestamp=observation.timestamp,
                    timestamp_raw=observation.timestamp_raw,
                    observation_type=observation.observation_type,
                    entity_key=observation.entity_key,
                    facebook_id=observation.facebook_id,
                    name=observation.name,
                    normalized_name=observation.normalized_name,
                    handle_or_identifier=observation.handle_or_identifier,
                    profile_url=observation.profile_url,
                    vanity_slug=observation.vanity_slug,
                    thread_identifier=observation.thread_identifier,
                    participant_context=observation.participant_context,
                    ip_address=observation.ip_address,
                    related_id_type=observation.related_id_type,
                    related_id_value=observation.related_id_value,
                    related_id_context=observation.related_id_context,
                    deleted_user_observed=observation.deleted_user_observed,
                    source_path=observation.source_path,
                    source_sha256=observation.source_sha256,
                    raw_payload_path=observation.raw_payload_path,
                    confidence=observation.confidence,
                    explanation=observation.explanation,
                )
            )
    return sorted(rows, key=lambda row: (row.variant_id, row.timestamp == "", row.timestamp, row.source_path, row.raw_payload_path))


def build_owner_identity_crosscheck(
    observations: list[IdentityObservation],
    timeline: list[VariantTimelineRow],
    alias_rules: dict[str, dict[str, str]] | None = None,
) -> tuple[
    list[OwnerIdentityRow],
    list[IdentityFirstContactRow],
    list[UnassignedIdVariantRow],
    str,
    list[MasterIdentityAliasClusterRow],
    list[MasterIdentityFirstContactRow],
]:
    alias_rules = alias_rules or {}
    owner_names = _confirmed_owner_names(observations)
    owner_keys = {_normalize_name(name) for name in owner_names if name}
    identities: dict[str, dict[str, Any]] = {}
    unassigned: dict[tuple[str, str], dict[str, Any]] = {}

    for observation in observations:
        identity_key = _identity_roster_key(observation, owner_keys)
        if identity_key:
            row = identities.setdefault(identity_key, _empty_identity(identity_key, identity_key in owner_keys))
            _add_identity_observation(row, observation)
            continue
        if observation.related_id_value:
            key = (observation.related_id_type, observation.related_id_value)
            row = unassigned.setdefault(key, _empty_unassigned_id(observation.related_id_type, observation.related_id_value))
            _add_unassigned_observation(row, observation)

    if owner_keys:
        for observation in observations:
            if observation.source_path not in OWNER_AFFILIATED_SOURCES:
                continue
            owner_key = sorted(owner_keys)[0]
            row = identities.setdefault(owner_key, _empty_identity(owner_key, True))
            _add_owner_affiliated_identifier(row, observation)

    first_contacts = _first_contact_rows(timeline, identities, owner_keys)
    _apply_alias_rules(identities, alias_rules, observations)
    first_by_identity = {row.identity_key: row for row in first_contacts if row.variant_id_type == "identity"}
    for row in identities.values():
        first = first_by_identity.get(row["identity_key"])
        if first:
            row["first_contact_date"] = first.first_interaction_date
            row["first_contact_source_path"] = first.source_path

    roster = [_identity_to_roster_row(row) for row in identities.values()]
    roster.sort(key=lambda row: (0 if row.identity_status == "CONFIRMED_ACCOUNT_OWNER" else 1, -row.observation_count, row.display_name.lower()))

    unassigned_rows = [_unassigned_to_row(row) for row in unassigned.values()]
    unassigned_rows.sort(key=lambda row: (row.related_id_type, -row.observation_count, row.related_id_value))

    alias_clusters = _master_alias_clusters(roster)
    master_first_contacts = _master_first_contact_rows(first_contacts, roster)
    report = _owner_report_text(roster, first_contacts, unassigned_rows, alias_clusters)
    return roster, first_contacts, unassigned_rows, report, alias_clusters, master_first_contacts


def load_alias_rules(alias_map: Path | None) -> dict[str, dict[str, str]]:
    if not alias_map:
        return {}
    path = Path(alias_map)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    clusters = data.get("clusters", []) if isinstance(data, dict) else data
    rules: dict[str, dict[str, str]] = {}
    for index, cluster in enumerate(clusters):
        if not isinstance(cluster, dict):
            continue
        master_name = str(cluster.get("master_identity") or cluster.get("master_identity_name") or "").strip()
        if not master_name:
            continue
        master_key = _normalize_name(str(cluster.get("master_identity_key") or master_name))
        cluster_id = str(cluster.get("alias_cluster_id") or f"alias_cluster:{master_key}").strip()
        confidence = str(cluster.get("confidence") or "manual_alias_map").strip()
        explanation = str(cluster.get("explanation") or "Aliases were supplied by a case-specific alias map.").strip()
        aliases = list(cluster.get("aliases") or [])
        aliases.extend(cluster.get("identity_keys") or [])
        aliases.append(master_name)
        for alias in aliases:
            alias_key = _normalize_name(str(alias))
            if not alias_key:
                continue
            rules[alias_key] = {
                "master_identity_key": master_key,
                "master_identity_name": master_name,
                "alias_cluster_id": cluster_id,
                "alias_cluster_confidence": confidence,
                "alias_cluster_explanation": explanation,
                "alias_rule_index": str(index),
            }
    return rules


def _default_alias_map_path(source: Path) -> Path | None:
    source = Path(source)
    candidates = []
    if source.is_dir():
        candidates.extend([source / "identity_aliases.json", source / "facebook_identity_aliases.json"])
        candidates.extend([source.parent / "identity_aliases.json", source.parent / "facebook_identity_aliases.json"])
    return next((candidate for candidate in candidates if candidate.exists()), None)


def _confirmed_owner_names(observations: list[IdentityObservation]) -> set[str]:
    names = set()
    for observation in observations:
        if observation.source_path != OWNER_PROFILE_SOURCE:
            continue
        if observation.raw_payload_path.endswith("profile_v2.name") or ".profile_v2.name" in observation.raw_payload_path:
            if observation.name:
                names.add(observation.name)
    return names


def _identity_roster_key(observation: IdentityObservation, owner_keys: set[str]) -> str:
    if observation.normalized_name in owner_keys:
        return observation.normalized_name
    if _is_person_like_name(observation.name):
        return observation.normalized_name
    if DELETED_RE.search(observation.name):
        return _normalize_name(observation.name)
    return ""


def _empty_identity(identity_key: str, confirmed_owner: bool) -> dict[str, Any]:
    return {
        "identity_key": identity_key,
        "identity_status": "CONFIRMED_ACCOUNT_OWNER" if confirmed_owner else "observed_identity",
        "master_identity_key": identity_key,
        "master_identity_name": "",
        "alias_cluster_id": "",
        "alias_cluster_confidence": "",
        "alias_cluster_explanation": "",
        "alias_cluster_evidence": "",
        "display_names": {},
        "observation_count": 0,
        "first_observed_timestamp": "",
        "last_observed_timestamp": "",
        "first_contact_date": "",
        "first_contact_source_path": "",
        "names": set(),
        "facebook_ids": set(),
        "phone_numbers": set(),
        "phone_candidates": set(),
        "emails": set(),
        "profile_urls": set(),
        "vanity_slugs": set(),
        "thread_identifiers": set(),
        "ip_addresses": set(),
        "other_ids": set(),
        "variant_ids": set(),
        "source_paths": set(),
        "deleted_user_observed": False,
    }


def _empty_unassigned_id(related_id_type: str, related_id_value: str) -> dict[str, Any]:
    return {
        "related_id_type": related_id_type,
        "related_id_value": related_id_value,
        "observation_count": 0,
        "first_observed_timestamp": "",
        "last_observed_timestamp": "",
        "contexts": {},
        "names": set(),
        "source_paths": set(),
    }


def _add_identity_observation(row: dict[str, Any], observation: IdentityObservation) -> None:
    row["observation_count"] += 1
    if observation.name:
        row["names"].add(observation.name)
        row["display_names"][observation.name] = row["display_names"].get(observation.name, 0) + 1
    _add_timestamp_bounds(row, observation.timestamp)
    _set_add(row["facebook_ids"], observation.facebook_id)
    _set_add(row["profile_urls"], observation.profile_url)
    _set_add(row["vanity_slugs"], observation.vanity_slug)
    _set_add(row["thread_identifiers"], observation.thread_identifier)
    _set_add(row["ip_addresses"], observation.ip_address)
    _set_add(row["source_paths"], observation.source_path)
    if observation.deleted_user_observed:
        row["deleted_user_observed"] = True
    _add_related_identifier(row, observation)


def _add_owner_affiliated_identifier(row: dict[str, Any], observation: IdentityObservation) -> None:
    _set_add(row["source_paths"], observation.source_path)
    _set_add(row["facebook_ids"], observation.facebook_id)
    _add_related_identifier(row, observation)


def _add_related_identifier(row: dict[str, Any], observation: IdentityObservation) -> None:
    if not observation.related_id_value:
        return
    related_id = f"{observation.related_id_type}:{observation.related_id_value}"
    if observation.related_id_type in {"fbid", "profile_id", "actor_id", "author_id", "owner_id", "source_id"}:
        row["facebook_ids"].add(observation.related_id_value)
    elif observation.related_id_type == "email_address":
        row["emails"].add(observation.related_id_value)
    elif observation.related_id_type == "phone_number":
        if _direct_phone_context(observation.related_id_context):
            row["phone_numbers"].add(observation.related_id_value)
        else:
            row["phone_candidates"].add(observation.related_id_value)
    else:
        row["other_ids"].add(related_id)


def _add_unassigned_observation(row: dict[str, Any], observation: IdentityObservation) -> None:
    row["observation_count"] += 1
    _add_timestamp_bounds(row, observation.timestamp)
    _set_add(row["names"], observation.name)
    _set_add(row["source_paths"], observation.source_path)
    if observation.related_id_context:
        row["contexts"][observation.related_id_context] = row["contexts"].get(observation.related_id_context, 0) + 1


def _add_timestamp_bounds(row: dict[str, Any], timestamp: str) -> None:
    if not timestamp or _interaction_date(timestamp) in EPOCH_INTERACTION_DATES:
        return
    if not row["first_observed_timestamp"] or timestamp < row["first_observed_timestamp"]:
        row["first_observed_timestamp"] = timestamp
    if not row["last_observed_timestamp"] or timestamp > row["last_observed_timestamp"]:
        row["last_observed_timestamp"] = timestamp


def _first_contact_rows(
    timeline: list[VariantTimelineRow],
    identities: dict[str, dict[str, Any]],
    owner_keys: set[str],
) -> list[IdentityFirstContactRow]:
    first: dict[tuple[str, str], VariantTimelineRow] = {}
    for row in timeline:
        identity_key = row.normalized_name
        if identity_key not in identities and identity_key not in owner_keys:
            continue
        interaction_date = row.interaction_date
        if not interaction_date or interaction_date in EPOCH_INTERACTION_DATES:
            continue
        variant_key = row.variant_id or "identity"
        identities[identity_key]["variant_ids"].add(row.variant_id)
        key = (identity_key, variant_key)
        if key not in first or (row.timestamp or interaction_date) < (first[key].timestamp or first[key].interaction_date):
            first[key] = row

    identity_level: dict[str, VariantTimelineRow] = {}
    for (identity_key, _), row in first.items():
        if identity_key not in identity_level or (row.timestamp or row.interaction_date) < (identity_level[identity_key].timestamp or identity_level[identity_key].interaction_date):
            identity_level[identity_key] = row
    for identity_key, row in identity_level.items():
        first[(identity_key, "identity")] = row

    result = [
        _timeline_to_first_contact(identity_key, row, identities[identity_key], variant_key == "identity")
        for (identity_key, variant_key), row in first.items()
    ]
    return sorted(result, key=lambda row: (0 if row.identity_status == "CONFIRMED_ACCOUNT_OWNER" else 1, row.identity_key, row.first_interaction_date, row.variant_id))


def _apply_alias_rules(
    identities: dict[str, dict[str, Any]],
    alias_rules: dict[str, dict[str, str]],
    observations: list[IdentityObservation],
) -> None:
    support_by_cluster = _alias_rule_support(alias_rules, observations)
    for identity_key, row in identities.items():
        rule = alias_rules.get(identity_key)
        support = support_by_cluster.get(rule["alias_cluster_id"] if rule else "")
        if not rule or not support or identity_key not in support["supported_aliases"]:
            row["master_identity_key"] = identity_key
            row["master_identity_name"] = _display_name(row)
            continue
        row["master_identity_key"] = rule["master_identity_key"]
        row["master_identity_name"] = rule["master_identity_name"]
        row["alias_cluster_id"] = rule["alias_cluster_id"]
        row["alias_cluster_confidence"] = support["confidence"]
        row["alias_cluster_explanation"] = rule["alias_cluster_explanation"]
        row["alias_cluster_evidence"] = support["evidence"]


def _alias_rule_support(
    alias_rules: dict[str, dict[str, str]],
    observations: list[IdentityObservation],
) -> dict[str, dict[str, Any]]:
    aliases_by_cluster: dict[str, set[str]] = {}
    master_by_cluster: dict[str, str] = {}
    for alias_key, rule in alias_rules.items():
        cluster_id = rule["alias_cluster_id"]
        aliases_by_cluster.setdefault(cluster_id, set()).add(alias_key)
        master_by_cluster[cluster_id] = rule["master_identity_key"]

    events_by_cluster: dict[str, list[tuple[int, str, IdentityObservation]]] = {cluster_id: [] for cluster_id in aliases_by_cluster}
    for observation in observations:
        event_key = _alias_event_key(observation)
        if not event_key:
            continue
        timestamp = _timestamp_seconds(observation.timestamp)
        if timestamp is None:
            continue
        for cluster_id, aliases in aliases_by_cluster.items():
            if event_key in aliases:
                events_by_cluster[cluster_id].append((timestamp, event_key, observation))

    support: dict[str, dict[str, Any]] = {}
    for cluster_id, events in events_by_cluster.items():
        events.sort(key=lambda row: row[0])
        aliases = aliases_by_cluster[cluster_id]
        master_key = master_by_cluster[cluster_id]
        edges: dict[str, set[str]] = {alias: set() for alias in aliases}
        evidence_by_edge: dict[tuple[str, str], str] = {}
        for left_index, left in enumerate(events):
            left_ts, left_alias, left_observation = left
            for right_ts, right_alias, right_observation in events[left_index + 1:]:
                if right_ts - left_ts > ALIAS_SESSION_SECONDS:
                    break
                if left_alias == right_alias:
                    continue
                edges.setdefault(left_alias, set()).add(right_alias)
                edges.setdefault(right_alias, set()).add(left_alias)
                edge_key = tuple(sorted((left_alias, right_alias)))
                evidence_by_edge.setdefault(
                    edge_key,
                    (
                        f"{left_observation.timestamp}|{left_alias}|{left_observation.participant_context or left_observation.observation_type}|"
                        f"{left_observation.source_path}|{left_observation.raw_payload_path}"
                        f" -> {right_observation.timestamp}|{right_alias}|{right_observation.participant_context or right_observation.observation_type}|"
                        f"{right_observation.source_path}|{right_observation.raw_payload_path}"
                    ),
                )
        connected = _connected_aliases(master_key, edges)
        if len(connected) < 2:
            continue
        evidence_parts = [
            evidence
            for edge, evidence in sorted(evidence_by_edge.items())
            if edge[0] in connected and edge[1] in connected
        ]
        missing = sorted(aliases - connected)
        support[cluster_id] = {
            "confidence": "data_supported_alias_session",
            "evidence": ";".join(evidence_parts[:20])
            + (f";not_promoted_without_session_evidence={','.join(missing)}" if missing else ""),
            "supported_aliases": connected,
        }
    return support


def _connected_aliases(start: str, edges: dict[str, set[str]]) -> set[str]:
    if start not in edges:
        return set()
    seen = {start}
    pending = [start]
    while pending:
        current = pending.pop()
        for next_alias in edges.get(current, set()):
            if next_alias in seen:
                continue
            seen.add(next_alias)
            pending.append(next_alias)
    return seen


def _alias_event_key(observation: IdentityObservation) -> str:
    if observation.participant_context not in {
        "facebook_search_query",
        "facebook_profile_visit",
        "facebook_content_view",
        "facebook_follow_or_page",
        "facebook_profile_update",
    }:
        return ""
    for value in (observation.normalized_name, _normalize_name(observation.handle_or_identifier), _normalize_name(observation.vanity_slug)):
        if value:
            return value
    return ""


def _timestamp_seconds(timestamp: str) -> int | None:
    if not timestamp:
        return None
    try:
        return int(datetime.fromisoformat(timestamp).timestamp())
    except ValueError:
        return None


def _timeline_to_first_contact(
    identity_key: str,
    row: VariantTimelineRow,
    identity: dict[str, Any],
    identity_level: bool,
) -> IdentityFirstContactRow:
    variant_id = "identity" if identity_level else row.variant_id
    display_name = _display_name(identity)
    return IdentityFirstContactRow(
        identity_key=identity_key,
        display_name=display_name,
        identity_status=identity["identity_status"],
        variant_id=variant_id,
        variant_id_type="identity" if variant_id == "identity" else row.variant_id_type,
        variant_id_value=identity_key if variant_id == "identity" else row.variant_id_value,
        first_interaction_date=row.interaction_date,
        timestamp=row.timestamp,
        observation_type=row.observation_type,
        related_id_type=row.related_id_type,
        related_id_value=row.related_id_value,
        related_id_context=row.related_id_context,
        source_path=row.source_path,
        evidence_name=row.name,
        profile_url=row.profile_url,
        thread_identifier=row.thread_identifier,
        ip_address=row.ip_address,
    )


def _identity_to_roster_row(row: dict[str, Any]) -> OwnerIdentityRow:
    return OwnerIdentityRow(
        identity_status=row["identity_status"],
        identity_key=row["identity_key"],
        display_name=_display_name(row),
        master_identity_key=row["master_identity_key"],
        master_identity_name=row["master_identity_name"] or _display_name(row),
        alias_cluster_id=row["alias_cluster_id"],
        alias_cluster_confidence=row["alias_cluster_confidence"],
        alias_cluster_explanation=row["alias_cluster_explanation"],
        alias_cluster_evidence=row["alias_cluster_evidence"],
        all_name_variants=_join_values(row["names"], 50),
        observation_count=row["observation_count"],
        first_observed_timestamp=row["first_observed_timestamp"],
        last_observed_timestamp=row["last_observed_timestamp"],
        first_contact_date=row["first_contact_date"],
        first_contact_source_path=row["first_contact_source_path"],
        facebook_ids_observed=_join_values(row["facebook_ids"], 100),
        phone_numbers_direct=_join_values(row["phone_numbers"], 100),
        phone_number_candidates=_join_values(row["phone_candidates"], 100),
        emails_observed=_join_values(row["emails"], 100),
        profile_urls=_join_values(row["profile_urls"], 50),
        vanity_slugs=_join_values(row["vanity_slugs"], 100),
        thread_identifiers=_join_values(row["thread_identifiers"], 100),
        ip_addresses=_join_values(row["ip_addresses"], 100),
        other_identifying_ids=_join_values(row["other_ids"], 200),
        variant_ids_count=len(row["variant_ids"]),
        variant_ids_sample=_join_values(row["variant_ids"], 50),
        source_paths_sample=_join_values(row["source_paths"], 50),
        deleted_user_observed=row["deleted_user_observed"],
    )


def _master_alias_clusters(roster: list[OwnerIdentityRow]) -> list[MasterIdentityAliasClusterRow]:
    grouped: dict[str, list[OwnerIdentityRow]] = {}
    for row in roster:
        grouped.setdefault(row.master_identity_key or row.identity_key, []).append(row)

    clusters = []
    for master_key, rows in grouped.items():
        if len(rows) < 2 and not rows[0].alias_cluster_id:
            continue
        first_contact_rows = [row for row in rows if row.first_contact_date]
        first_contact_rows.sort(key=lambda row: row.first_contact_date)
        first_contact = first_contact_rows[0] if first_contact_rows else None
        clusters.append(
            MasterIdentityAliasClusterRow(
                alias_cluster_id=rows[0].alias_cluster_id or f"identity_cluster:{master_key}",
                master_identity_key=master_key,
                master_identity_name=rows[0].master_identity_name or rows[0].display_name,
                alias_identity_keys=_join_values(row.identity_key for row in rows),
                alias_display_names=_join_values(row.display_name for row in rows),
                observation_count=sum(row.observation_count for row in rows),
                first_contact_date=first_contact.first_contact_date if first_contact else "",
                first_contact_source_path=first_contact.first_contact_source_path if first_contact else "",
                facebook_ids_observed=_join_joined_fields(row.facebook_ids_observed for row in rows),
                phone_numbers_direct=_join_joined_fields(row.phone_numbers_direct for row in rows),
                phone_number_candidates=_join_joined_fields(row.phone_number_candidates for row in rows),
                emails_observed=_join_joined_fields(row.emails_observed for row in rows),
                profile_urls=_join_joined_fields(row.profile_urls for row in rows),
                vanity_slugs=_join_joined_fields(row.vanity_slugs for row in rows),
                thread_identifiers=_join_joined_fields(row.thread_identifiers for row in rows),
                ip_addresses=_join_joined_fields(row.ip_addresses for row in rows),
                other_identifying_ids=_join_joined_fields(row.other_identifying_ids for row in rows),
                source_paths_sample=_join_joined_fields(row.source_paths_sample for row in rows),
                alias_cluster_confidence=rows[0].alias_cluster_confidence or "identity_grouping",
                alias_cluster_explanation=rows[0].alias_cluster_explanation or "Rows share the same master identity key.",
                alias_cluster_evidence=_join_joined_fields(row.alias_cluster_evidence for row in rows),
            )
        )
    return sorted(clusters, key=lambda row: (row.master_identity_name.lower(), row.alias_cluster_id))


def _master_first_contact_rows(
    first_contacts: list[IdentityFirstContactRow],
    roster: list[OwnerIdentityRow],
) -> list[MasterIdentityFirstContactRow]:
    by_identity = {row.identity_key: row for row in roster}
    rows = []
    for first in first_contacts:
        roster_row = by_identity.get(first.identity_key)
        if not roster_row:
            continue
        rows.append(
            MasterIdentityFirstContactRow(
                master_identity_key=roster_row.master_identity_key,
                master_identity_name=roster_row.master_identity_name,
                alias_identity_key=first.identity_key,
                alias_display_name=first.display_name,
                alias_cluster_id=roster_row.alias_cluster_id,
                alias_cluster_confidence=roster_row.alias_cluster_confidence,
                variant_id=first.variant_id,
                variant_id_type=first.variant_id_type,
                variant_id_value=first.variant_id_value,
                first_interaction_date=first.first_interaction_date,
                timestamp=first.timestamp,
                observation_type=first.observation_type,
                related_id_type=first.related_id_type,
                related_id_value=first.related_id_value,
                related_id_context=first.related_id_context,
                source_path=first.source_path,
                evidence_name=first.evidence_name,
                profile_url=first.profile_url,
                thread_identifier=first.thread_identifier,
                ip_address=first.ip_address,
            )
        )
    return sorted(rows, key=lambda row: (row.master_identity_name.lower(), row.first_interaction_date, row.alias_identity_key, row.variant_id))


def _unassigned_to_row(row: dict[str, Any]) -> UnassignedIdVariantRow:
    contexts = [f"{context} ({count})" for context, count in sorted(row["contexts"].items())]
    return UnassignedIdVariantRow(
        related_id_type=row["related_id_type"],
        related_id_value=row["related_id_value"],
        observation_count=row["observation_count"],
        first_observed_timestamp=row["first_observed_timestamp"],
        last_observed_timestamp=row["last_observed_timestamp"],
        contexts=_join_values(contexts, 100),
        names_seen_on_same_rows=_join_values(row["names"], 50),
        source_paths_sample=_join_values(row["source_paths"], 50),
    )


def _owner_report_text(
    roster: list[OwnerIdentityRow],
    first_contacts: list[IdentityFirstContactRow],
    unassigned_ids: list[UnassignedIdVariantRow],
    alias_clusters: list[MasterIdentityAliasClusterRow],
) -> str:
    lines = [
        "FACEBOOK OWNER IDENTITY AND VARIANT CROSSCHECK",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "SCOPE",
        "- Confirmed owner identity is assigned only when native profile_information.json owner-name evidence is present.",
        "- Other rows are observed/correlated identity variants and require source review before asserting account control.",
        "- Placeholder epoch dates such as 1970-01-01 are excluded from first-contact calculations.",
        "",
    ]
    owner_rows = [row for row in roster if row.identity_status == "CONFIRMED_ACCOUNT_OWNER"]
    if owner_rows:
        owner = owner_rows[0]
        lines.extend(
            [
                "CONFIRMED ACCOUNT OWNER IDENTITY",
                f"Name: {owner.display_name}",
                "Status: CONFIRMED_ACCOUNT_OWNER",
                f"Emails observed: {owner.emails_observed or 'none'}",
                f"Phone numbers observed: {owner.phone_numbers_direct or 'none'}",
                f"Facebook/profile IDs observed: {owner.facebook_ids_observed or 'none'}",
                f"Vanity/profile slugs observed: {owner.vanity_slugs or 'none'}",
                f"Profile URLs observed: {owner.profile_urls or 'none'}",
                f"Observation rows tied to owner identity: {owner.observation_count}",
                f"First non-placeholder contact/interaction row: {owner.first_contact_date or 'undated'} | {owner.first_contact_source_path}",
                "",
            ]
        )
    lines.extend(
        [
            "MASTER COUNTS",
            f"Identity roster rows: {len(roster)}",
            f"Master alias cluster rows: {len(alias_clusters)}",
            f"First-contact identity/variant rows: {len(first_contacts)}",
            f"Unassigned ID-only variant rows: {len(unassigned_ids)}",
            "",
            "MASTER ALIAS CLUSTERS",
        ]
    )
    for row in alias_clusters:
        lines.append(
            " | ".join(
                [
                    row.master_identity_name,
                    f"aliases={row.alias_display_names}",
                    f"obs={row.observation_count}",
                    f"first_contact={row.first_contact_date or 'undated'}",
                    f"confidence={row.alias_cluster_confidence}",
                    f"why={row.alias_cluster_explanation}",
                    f"evidence={_clip(row.alias_cluster_evidence, 900) or 'none'}",
                ]
            )
        )
    lines.extend(
        [
            "",
            "IDENTITY ROSTER - CONFIRMED OWNER FIRST",
        ]
    )
    for row in roster:
        lines.append(
            " | ".join(
                [
                    row.identity_status,
                    row.display_name,
                    f"obs={row.observation_count}",
                    f"first_contact={row.first_contact_date or 'undated'}",
                    f"phones={row.phone_numbers_direct or 'none'}",
                    f"fb/profile_ids={row.facebook_ids_observed or 'none'}",
                    f"emails={row.emails_observed or 'none'}",
                    f"other_ids={_clip(row.other_identifying_ids, 400) or 'none'}",
                ]
            )
        )
    lines.extend(["", "FIRST CONTACT TIMELINE - FIRST 500 ROWS"])
    for row in first_contacts[:500]:
        extra = ""
        if row.related_id_type and row.related_id_value:
            extra = f" | {row.related_id_type}={row.related_id_value}"
        elif row.profile_url:
            extra = f" | {row.profile_url}"
        lines.append(
            f"{row.display_name} [{row.identity_status}] | {row.first_interaction_date} | "
            f"{row.variant_id} | {row.observation_type}{extra} | {row.source_path}"
        )
    if len(first_contacts) > 500:
        lines.append(f"... {len(first_contacts) - 500} additional first-contact rows are available in CSV/JSONL output.")
    return "\n".join(lines) + "\n"


def _is_person_like_name(name: str) -> bool:
    value = " ".join((name or "").split())
    if not value:
        return False
    normalized = value.lower()
    if normalized in NON_PERSON_NAMES or normalized.startswith("ad by "):
        return False
    if any(token in f" {normalized} " for token in ACTION_NAME_TOKENS):
        return False
    if "'s post" in normalized or "'s comment" in normalized or "'s link" in normalized:
        return False
    if value.endswith(".") or len(value) > 80:
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'.-]*", value)
    return len(words) >= 2


def _direct_phone_context(context: str) -> bool:
    lower = context.lower()
    if "device_type:phone" in lower:
        return False
    return any(token in lower for token in ("phone:phone", "contact", "autofill", "content:phone", "value:phone"))


def _set_add(values: set[str], value: str) -> None:
    value = (value or "").strip()
    if value:
        values.add(value)


def _display_name(row: dict[str, Any]) -> str:
    names = row.get("display_names", {})
    if names:
        return sorted(names.items(), key=lambda item: (-item[1], item[0].lower()))[0][0]
    return row["identity_key"]


def _join_values(values: Iterable[str], limit: int | None = None) -> str:
    result = sorted({value for value in values if value})
    if limit is not None and len(result) > limit:
        return ";".join(result[:limit]) + f";... +{len(result) - limit} more"
    return ";".join(result)


def _join_joined_fields(values: Iterable[str], limit: int | None = 200) -> str:
    pieces = []
    for value in values:
        pieces.extend(part.strip() for part in value.split(";") if part.strip())
    return _join_values(pieces, limit)


def _clip(value: str, length: int) -> str:
    if len(value) <= length:
        return value
    return value[:length] + "..."


def _iter_source_items(source: Path) -> Iterable[SourceItem]:
    source = Path(source)
    suffixes = {".json", ".html", ".htm"}
    if source.is_dir():
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            relative_path = path.relative_to(source).as_posix()
            if not _is_identity_source(relative_path):
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
                if suffix not in suffixes or not _is_identity_source(name):
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


def _is_identity_source(path: str) -> bool:
    lower = path.replace("\\", "/").lower()
    return any(hint in lower for hint in IDENTITY_SOURCE_HINTS)


def _path_observations(item: SourceItem) -> list[IdentityObservation]:
    rows: list[IdentityObservation] = []
    match = THREAD_DIR_RE.search(item.path)
    if match:
        raw_name, facebook_id = match.groups()
        name = _name_from_slug(raw_name)
        ip = _first_ip(str(item.payload)) if isinstance(item.payload, str) else ""
        thread_identifier = f"{raw_name}_{facebook_id}" if facebook_id else raw_name
        rows.append(_make_observation(
            item=item,
            raw_payload_path="source_path",
            observation_type="thread_path_identity",
            facebook_id=facebook_id or "",
            name=name,
            handle_or_identifier=raw_name,
            profile_url="",
            thread_identifier=thread_identifier,
            participant_context="message_thread_path",
            ip_address=ip,
            related_id_type="thread_id",
            related_id_value=thread_identifier,
            related_id_context="message_thread_path",
            timestamp_raw="",
            explanation="Identity was inferred from a Facebook message thread path.",
        ))
    for related_type, related_value, context in _related_ids_from_path(item.path):
        rows.append(_make_observation(
            item=item,
            raw_payload_path="source_path",
            observation_type="path_related_identifier",
            facebook_id="",
            name="",
            handle_or_identifier="",
            profile_url="",
            thread_identifier="",
            participant_context="",
            ip_address="",
            related_id_type=related_type,
            related_id_value=related_value,
            related_id_context=context,
            timestamp_raw="",
            explanation="Platform object identifier was inferred from the source path.",
        ))
    return rows


def _json_observations(item: SourceItem) -> list[IdentityObservation]:
    rows: list[IdentityObservation] = _notification_observations(item)
    rows.extend(_activity_entry_observations(item))
    rows.extend(_search_query_observations(item))
    for value, trail in _walk_dicts(item.payload, ""):
        name = _first_for_keys(value, NAME_KEYS)
        facebook_id = _facebook_id_from_record(value, trail, item.path)
        handle = _first_for_keys(value, HANDLE_KEYS)
        profile_url = _first_for_keys(value, PROFILE_URL_KEYS)
        ip = _first_for_keys(value, IP_KEYS) or _first_ip(json.dumps(value, ensure_ascii=False))
        participant_context = _participant_context(trail, item.path)
        related_ids = _related_ids_from_record(value, trail, item.path)
        if not any((name, facebook_id, handle, profile_url, ip, related_ids)):
            continue
        rows.append(
            _make_observation(
                item=item,
                raw_payload_path=trail,
                observation_type=_observation_type(name, facebook_id, profile_url, ip, "", ""),
                facebook_id=facebook_id,
                name=name,
                handle_or_identifier=handle,
                profile_url=profile_url,
                thread_identifier="",
                participant_context=participant_context,
                ip_address=ip,
                related_id_type="",
                related_id_value="",
                related_id_context="",
                timestamp_raw=_first_for_keys(value, TIMESTAMP_KEYS),
                explanation="Identity evidence was extracted from a structured Facebook JSON record.",
            )
        )
        for related_type, related_value, context in related_ids:
            rows.append(
                _make_observation(
                    item=item,
                    raw_payload_path=trail,
                    observation_type=_observation_type(name, facebook_id, profile_url, ip, related_type, related_value),
                    facebook_id=facebook_id,
                    name=name,
                    handle_or_identifier=handle,
                    profile_url=profile_url,
                    thread_identifier="",
                    participant_context=participant_context,
                    ip_address=ip,
                    related_id_type=related_type,
                    related_id_value=related_value,
                    related_id_context=context,
                    timestamp_raw=_first_for_keys(value, TIMESTAMP_KEYS),
                    explanation="Platform object identifier was extracted with nearby Facebook identity context.",
                )
            )
    return rows


def _activity_entry_observations(item: SourceItem) -> list[IdentityObservation]:
    rows: list[IdentityObservation] = []
    lower_path = item.path.lower()
    if not any(token in lower_path for token in ("recently_visited", "recently_viewed", "pages_", "who_you've_followed", "profile_update_history")):
        return rows
    for value, trail in _walk_dicts(item.payload, ""):
        timestamp_raw = _first_for_keys(value, TIMESTAMP_KEYS)
        if not timestamp_raw:
            continue
        data = value.get("data")
        if isinstance(data, dict):
            name = _text_from_value(data.get("name"))
            profile_url = _text_from_value(data.get("uri")) or _text_from_value(data.get("href"))
        elif isinstance(data, list):
            name = _first_name_from_label_values(data)
            profile_url = _first_url_from_label_values(data)
        else:
            name = _first_for_keys(value, NAME_KEYS)
            profile_url = _first_for_keys(value, PROFILE_URL_KEYS)
        if not name:
            name = _name_from_activity_title(_text_from_value(value.get("title")))
        if not any((name, profile_url)):
            continue
        rows.append(
            _make_observation(
                item=item,
                raw_payload_path=trail,
                observation_type="timestamped_activity_identity",
                facebook_id="",
                name=name,
                handle_or_identifier="",
                profile_url=profile_url,
                thread_identifier="",
                participant_context=_activity_context(lower_path),
                ip_address="",
                related_id_type="",
                related_id_value="",
                related_id_context="",
                timestamp_raw=timestamp_raw,
                explanation="Timestamped Facebook activity entry linked a name or profile URL to a source interaction.",
            )
        )
    return rows


def _search_query_observations(item: SourceItem) -> list[IdentityObservation]:
    if "logged_information/search/" not in item.path.lower():
        return []
    rows: list[IdentityObservation] = []
    for value, trail in _walk_dicts(item.payload, ""):
        timestamp_raw = _first_for_keys(value, TIMESTAMP_KEYS)
        if not timestamp_raw:
            continue
        query = _search_query_from_record(value)
        if not query:
            continue
        is_name = _is_person_like_name(query)
        rows.append(
            _make_observation(
                item=item,
                raw_payload_path=trail,
                observation_type="search_query_identity_candidate",
                facebook_id="",
                name=query if is_name else "",
                handle_or_identifier="" if is_name else query,
                profile_url="",
                thread_identifier="",
                participant_context="facebook_search_query",
                ip_address="",
                related_id_type="search_query",
                related_id_value=query,
                related_id_context="facebook_search_history",
                timestamp_raw=timestamp_raw,
                explanation="Facebook search history contained a query that can support alias review when paired with nearby searches or visits.",
            )
        )
    return rows


def _notification_observations(item: SourceItem) -> list[IdentityObservation]:
    lower_path = item.path.lower()
    if "notification" not in lower_path and "emails_we_sent_you" not in lower_path and "email" not in lower_path:
        return []

    rows: list[IdentityObservation] = []
    for value, trail in _walk_dicts(item.payload, ""):
        text = _notification_text(value)
        href = _first_for_keys(value, PROFILE_URL_KEYS)
        timestamp_raw = _first_for_keys(value, TIMESTAMP_KEYS)
        notification_id = _notification_id_from_record(value, href)
        actor_id = _text_from_value(value.get("actor_id"))
        target_id = _text_from_value(value.get("target_id"))
        source_id = _text_from_value(value.get("source_id"))
        fbid = _text_from_value(value.get("fbid"))
        actor_name = _notification_actor_name(text)

        if actor_id:
            rows.append(
                _make_observation(
                    item=item,
                    raw_payload_path=trail,
                    observation_type="notification_actor_identity",
                    facebook_id=actor_id,
                    name=actor_name,
                    handle_or_identifier="",
                    profile_url=href,
                    thread_identifier="",
                    participant_context="notification_actor",
                    ip_address="",
                    related_id_type="notification_id" if notification_id else "",
                    related_id_value=notification_id,
                    related_id_context="notification_actor_link",
                    timestamp_raw=timestamp_raw,
                    explanation="Notification actor ID was linked to nearby notification text and URL context.",
                )
            )
        for related_type, related_value, context in _notification_related_ids(value, href, target_id, source_id, fbid, notification_id):
            rows.append(
                _make_observation(
                    item=item,
                    raw_payload_path=trail,
                    observation_type=_notification_observation_type(related_type, lower_path),
                    facebook_id="",
                    name=actor_name if actor_name and related_type in {"target_id", "source_id", "profile_id"} else "",
                    handle_or_identifier="",
                    profile_url=href,
                    thread_identifier="",
                    participant_context=_notification_context(lower_path),
                    ip_address="",
                    related_id_type=related_type,
                    related_id_value=related_value,
                    related_id_context=context,
                    timestamp_raw=timestamp_raw,
                    explanation="Notification or email-notification identifier was extracted for variant linkage review.",
                )
            )
    return rows


def _notification_text(value: dict[str, Any]) -> str:
    parts = []
    for key in ("text", "title", "subject", "body", "message", "content"):
        text = _text_from_value(value.get(key))
        if text:
            parts.append(text)
    return " ".join(parts)


def _first_name_from_label_values(values: list[Any]) -> str:
    for item in values:
        if not isinstance(item, dict):
            continue
        label = _text_from_value(item.get("label")).lower()
        if label in {"name", "contact name"}:
            return _text_from_value(item.get("value"))
        text = _text_from_value(item.get("name"))
        if text:
            return text
    return ""


def _first_url_from_label_values(values: list[Any]) -> str:
    for item in values:
        if not isinstance(item, dict):
            continue
        text = _text_from_value(item.get("uri")) or _text_from_value(item.get("href")) or _text_from_value(item.get("url"))
        if text:
            return text
    return ""


def _activity_context(lower_path: str) -> str:
    if "recently_visited" in lower_path:
        return "facebook_profile_visit"
    if "recently_viewed" in lower_path:
        return "facebook_content_view"
    if "pages_" in lower_path or "who_you've_followed" in lower_path:
        return "facebook_follow_or_page"
    if "profile_update_history" in lower_path:
        return "facebook_profile_update"
    return "facebook_activity"


def _name_from_activity_title(title: str) -> str:
    title = " ".join((title or "").split())
    if not title:
        return ""
    patterns = (
        r"added (.+?) to (?:his|her|their|your) profile",
        r"(?:liked|commented on|reacted to|shared|replied to) (.+?)'s (?:post|photo|comment|link)",
        r"^(.+?)'s (?:post|photo|comment|link)$",
    )
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .:")
    return title


def _search_query_from_record(value: dict[str, Any]) -> str:
    data = value.get("data")
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                text = _text_from_value(item.get("text"))
                if text:
                    return text.strip('"')
    text = _text_from_value(value.get("text"))
    return text.strip('"') if text else ""


def _notification_actor_name(text: str) -> str:
    text = " ".join((text or "").split())
    if not text:
        return ""
    patterns = (
        r"^(.+?) (?:commented|mentioned|tagged|liked|reacted|shared|posted|added|invited|accepted|sent|replied)\b",
        r"friend suggestion: ([^.]+)",
        r"^(.+?) is now friends with ",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" .:")
            return candidate if _is_person_like_name(candidate) else ""
    return ""


def _notification_id_from_record(value: dict[str, Any], href: str) -> str:
    for key in ("notification_id", "notif_id", "settings_notif_id"):
        text = _text_from_value(value.get(key))
        if text:
            return text
    for related_type, related_value, _ in _related_ids_from_text(href, "notification_href"):
        if related_type == "notification_id":
            return related_value
    return ""


def _notification_related_ids(
    value: dict[str, Any],
    href: str,
    target_id: str,
    source_id: str,
    fbid: str,
    notification_id: str,
) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    if notification_id:
        rows.append(("notification_id", notification_id, "notification_record"))
    if target_id:
        rows.append(("target_id", target_id, "notification_target_id"))
    if source_id:
        rows.append(("source_id", source_id, "notification_source_id"))
    if fbid:
        rows.append(("fbid", fbid, "notification_or_email_fbid"))
    rows.extend(_related_ids_from_record(value, "notification_record", "notification_record"))
    rows.extend(_related_ids_from_text(href, "notification_href"))
    return _dedupe_related_ids(rows)


def _notification_observation_type(related_type: str, lower_path: str) -> str:
    if "emails_we_sent_you" in lower_path:
        return "email_notification_identifier"
    if related_type in {"actor_id", "target_id", "source_id", "fbid", "profile_id"}:
        return "notification_user_id_tag"
    return "notification_platform_identifier"


def _notification_context(lower_path: str) -> str:
    if "emails_we_sent_you" in lower_path:
        return "email_notification_sent"
    if "browser_push" in lower_path or "push" in lower_path:
        return "popup_or_push_notification"
    return "facebook_notification"


def _html_observations(item: SourceItem) -> list[IdentityObservation]:
    parser = _TextExtractor()
    parser.feed(str(item.payload))
    rows = []
    for index, record in enumerate(_records_from_tokens(parser.tokens)):
        rows.append(
            _make_observation(
                item=item,
                raw_payload_path=f"html_record[{index}]",
                observation_type=_observation_type(
                    record.get("name", ""),
                    record.get("facebook_id", ""),
                    record.get("profile_url", ""),
                    record.get("ip_address", ""),
                    record.get("related_id_type", ""),
                    record.get("related_id_value", ""),
                ),
                facebook_id=record.get("facebook_id", ""),
                name=record.get("name", ""),
                handle_or_identifier=record.get("handle_or_identifier", ""),
                profile_url=record.get("profile_url", ""),
                thread_identifier=_thread_identifier_from_path(item.path),
                participant_context=record.get("participant_context", ""),
                ip_address=record.get("ip_address", ""),
                related_id_type=record.get("related_id_type", ""),
                related_id_value=record.get("related_id_value", ""),
                related_id_context=record.get("related_id_context", ""),
                timestamp_raw=record.get("timestamp_raw", ""),
                explanation="Identity evidence was extracted from labeled Facebook HTML text.",
            )
        )
    for related_type, related_value, context in _related_ids_from_text(str(item.payload), "html_text"):
        rows.append(
            _make_observation(
                item=item,
                raw_payload_path="html_text",
                observation_type="html_related_identifier",
                facebook_id="",
                name="",
                handle_or_identifier="",
                profile_url="",
                thread_identifier=_thread_identifier_from_path(item.path),
                participant_context="",
                ip_address="",
                related_id_type=related_type,
                related_id_value=related_value,
                related_id_context=context,
                timestamp_raw="",
                explanation="Platform object identifier was extracted from Facebook HTML text or URL parameters.",
            )
        )
    return rows


def _records_from_tokens(tokens: list[str]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        label = _label_name(token)
        if label:
            if label in {"name", "facebook_id"} and current.get(label) and _record_has_identity(current):
                records.append(current)
                current = {}
            value = _next_value(tokens, index)
            if value:
                if label.startswith("related:"):
                    current["related_id_type"] = label.split(":", 1)[1]
                    current["related_id_value"] = value
                    current["related_id_context"] = "html_label"
                else:
                    current[label] = value
            index += 2
            continue
        if not current.get("ip_address"):
            ip = _first_ip(token)
            if ip:
                current["ip_address"] = ip
        if DELETED_RE.search(token) and not current.get("name"):
            current["name"] = token
        index += 1
    if _record_has_identity(current):
        records.append(current)
    return records


def _record_has_identity(record: dict[str, str]) -> bool:
    return any(record.get(key) for key in ("name", "facebook_id", "handle_or_identifier", "profile_url", "participant_context", "ip_address", "related_id_value"))


def _label_name(token: str) -> str:
    normalized = token.strip().lower().rstrip(":")
    mapping = {
        "name": "name",
        "display name": "name",
        "participant": "name",
        "facebook id": "facebook_id",
        "profile id": "facebook_id",
        "user id": "facebook_id",
        "actor id": "related:actor_id",
        "author id": "related:author_id",
        "buyer id": "related:buyer_id",
        "comment id": "related:comment_id",
        "event id": "related:event_id",
        "group id": "related:group_id",
        "listing id": "related:marketplace_listing_id",
        "marketplace listing id": "related:marketplace_listing_id",
        "notification id": "related:notification_id",
        "owner id": "related:owner_id",
        "page id": "related:page_id",
        "photo id": "related:photo_id",
        "post id": "related:post_id",
        "product id": "related:marketplace_product_id",
        "seller id": "related:seller_id",
        "story id": "related:story_id",
        "tag id": "related:tag_id",
        "target id": "related:target_id",
        "thread id": "related:thread_id",
        "video id": "related:video_id",
        "handle": "handle_or_identifier",
        "username": "handle_or_identifier",
        "profile url": "profile_url",
        "profile link": "profile_url",
        "url": "profile_url",
        "participant list": "participant_context",
        "participants": "participant_context",
        "ip": "ip_address",
        "ip address": "ip_address",
        "time": "timestamp_raw",
        "date": "timestamp_raw",
        "timestamp": "timestamp_raw",
    }
    return mapping.get(normalized, "")


def _next_value(tokens: list[str], index: int) -> str:
    if index + 1 >= len(tokens):
        return ""
    value = tokens[index + 1].strip()
    return "" if _label_name(value) else value


def _make_observation(
    *,
    item: SourceItem,
    raw_payload_path: str,
    observation_type: str,
    facebook_id: str,
    name: str,
    handle_or_identifier: str,
    profile_url: str,
    thread_identifier: str,
    participant_context: str,
    ip_address: str,
    related_id_type: str,
    related_id_value: str,
    related_id_context: str,
    timestamp_raw: str,
    explanation: str,
) -> IdentityObservation:
    normalized = _normalize_name(name)
    deleted = bool(DELETED_RE.search(name))
    vanity_slug = _vanity_slug(profile_url, handle_or_identifier, thread_identifier)
    entity_key = _entity_key(facebook_id, normalized, vanity_slug, thread_identifier, ip_address, related_id_type, related_id_value)
    confidence = _confidence(facebook_id, name, ip_address, deleted, related_id_value)
    return IdentityObservation(
        timestamp=_timestamp_to_iso(timestamp_raw),
        timestamp_raw=timestamp_raw,
        observation_type=observation_type,
        entity_key=entity_key,
        facebook_id=facebook_id,
        name=name,
        normalized_name=normalized,
        handle_or_identifier=handle_or_identifier,
        profile_url=profile_url,
        vanity_slug=vanity_slug,
        thread_identifier=thread_identifier,
        participant_context=participant_context,
        ip_address=ip_address,
        related_id_type=related_id_type,
        related_id_value=related_id_value,
        related_id_context=related_id_context,
        deleted_user_observed=deleted,
        source_path=item.path,
        source_sha256=item.sha256,
        raw_payload_path=raw_payload_path,
        confidence=confidence,
        explanation=explanation,
    )


def _summary_row(entity_key: str, rows: list[IdentityObservation]) -> VariantSummary:
    names = sorted({row.name for row in rows if row.name})
    normalized_names = sorted({row.normalized_name for row in rows if row.normalized_name})
    facebook_ids = sorted({row.facebook_id for row in rows if row.facebook_id})
    handles = sorted({row.handle_or_identifier for row in rows if row.handle_or_identifier})
    profile_urls = sorted({row.profile_url for row in rows if row.profile_url})
    vanity_slugs = sorted({row.vanity_slug for row in rows if row.vanity_slug})
    thread_identifiers = sorted({row.thread_identifier for row in rows if row.thread_identifier})
    participant_contexts = sorted({row.participant_context for row in rows if row.participant_context})
    ips = sorted({row.ip_address for row in rows if row.ip_address})
    related_ids = sorted({_format_related_id(row) for row in rows if row.related_id_value})
    deleted = any(row.deleted_user_observed for row in rows)
    variant_type = _variant_type(
        facebook_ids,
        normalized_names,
        handles,
        vanity_slugs,
        ips,
        related_ids,
        deleted,
        profile_urls,
        thread_identifiers,
        participant_contexts,
    )
    confidence, explanation = _summary_confidence(variant_type, rows, names, facebook_ids, ips)
    return VariantSummary(
        entity_key=entity_key,
        variant_type=variant_type,
        observation_count=len(rows),
        facebook_ids=";".join(facebook_ids),
        names=";".join(names),
        handles_or_identifiers=";".join(handles),
        profile_urls=";".join(profile_urls),
        vanity_slugs=";".join(vanity_slugs),
        thread_identifiers=";".join(thread_identifiers),
        participant_contexts=";".join(participant_contexts),
        ip_addresses=";".join(ips),
        related_ids=";".join(related_ids),
        deleted_user_observed=deleted,
        first_timestamp=_first_timestamp(rows),
        last_timestamp=_last_timestamp(rows),
        source_paths=";".join(sorted({row.source_path for row in rows})),
        confidence=confidence,
        explanation=explanation,
    )


def _variant_type(
    facebook_ids: list[str],
    normalized_names: list[str],
    handles: list[str],
    vanity_slugs: list[str],
    ips: list[str],
    related_ids: list[str],
    deleted: bool,
    profile_urls: list[str],
    thread_identifiers: list[str],
    participant_contexts: list[str],
) -> str:
    if deleted:
        return "deleted_user_or_unavailable_label"
    if facebook_ids and len(normalized_names) > 1:
        return "name_variant_same_facebook_id"
    if facebook_ids and (len(handles) > 1 or len(vanity_slugs) > 1 or len(thread_identifiers) > 1):
        return "identifier_variant_same_facebook_id"
    if related_ids and any(_related_id_has_prefix(value, ("email_address", "phone_number", "contact_id", "external_id")) for value in related_ids):
        return "contact_identifier_context"
    if related_ids and any(_related_id_has_prefix(value, ("device_id", "session_id", "browser_id", "cookie_id", "app_id", "account_id")) for value in related_ids):
        return "device_session_identifier_context"
    if related_ids and any(_related_id_has_prefix(value, ("payment_id", "transaction_id", "order_id", "business_id")) for value in related_ids):
        return "commerce_payment_identifier_context"
    if related_ids and any(value.startswith("marketplace_") or value.startswith("seller_id:") or value.startswith("buyer_id:") for value in related_ids):
        return "marketplace_identifier_context"
    if related_ids and any(_related_id_has_prefix(value, ("reaction_id", "like_id", "share_id")) for value in related_ids):
        return "reaction_or_engagement_identifier_context"
    if related_ids and any(_related_id_has_prefix(value, ("place_id", "location_id", "checkin_id")) for value in related_ids):
        return "location_or_place_identifier_context"
    if related_ids and any(_related_id_has_prefix(value, ("group_id", "page_id", "event_id", "invite_id")) for value in related_ids):
        return "social_graph_object_identifier_context"
    if related_ids and facebook_ids:
        return "platform_object_id_with_facebook_id_context"
    if related_ids:
        return "platform_object_identifier_context"
    if profile_urls:
        return "profile_url_identity"
    if thread_identifiers:
        return "thread_identifier_identity"
    if participant_contexts:
        return "participant_list_identity"
    if facebook_ids and ips:
        return "facebook_id_with_ip_context"
    if facebook_ids:
        return "facebook_id_identity"
    if ips:
        return "ip_only_identity_context"
    return "name_only_identity"


def _cross_identity_summaries(observations: list[IdentityObservation]) -> list[VariantSummary]:
    rows: list[VariantSummary] = []
    rows.extend(_cross_summary_by_value(observations, "ip_address", "shared_ip_across_identity_keys", "ip"))
    rows.extend(_cross_summary_by_value(observations, "normalized_name", "same_normalized_name_different_facebook_ids", "normalized_name"))
    rows.extend(_cross_summary_by_value(observations, "handle_or_identifier", "shared_handle_across_identity_keys", "handle"))
    rows.extend(_cross_summary_by_value(observations, "profile_url", "shared_profile_url_across_identity_keys", "profile_url"))
    rows.extend(_cross_summary_by_value(observations, "vanity_slug", "shared_profile_slug_across_identity_keys", "vanity_slug"))
    rows.extend(_cross_summary_by_related_id(observations))
    rows.extend(_cross_summary_by_related_value(observations))
    rows.extend(_related_family_summaries(observations))
    return rows


def _cross_summary_by_value(
    observations: list[IdentityObservation],
    attribute: str,
    variant_type: str,
    key_prefix: str,
) -> list[VariantSummary]:
    grouped: dict[str, list[IdentityObservation]] = {}
    for observation in observations:
        value = str(getattr(observation, attribute))
        if not value:
            continue
        grouped.setdefault(value, []).append(observation)

    summaries = []
    for value, rows in grouped.items():
        entity_keys = {row.entity_key for row in rows}
        facebook_ids = {row.facebook_id for row in rows if row.facebook_id}
        if variant_type == "same_normalized_name_different_facebook_ids" and len(facebook_ids) < 2:
            continue
        if len(entity_keys) < 2 and not (variant_type == "same_normalized_name_different_facebook_ids" and len(facebook_ids) > 1):
            continue
        summaries.append(_cross_summary_row(f"{key_prefix}:{value}", variant_type, rows))
    return summaries


def _cross_summary_by_related_id(observations: list[IdentityObservation]) -> list[VariantSummary]:
    grouped: dict[str, list[IdentityObservation]] = {}
    for observation in observations:
        if not observation.related_id_value:
            continue
        grouped.setdefault(_format_related_id(observation), []).append(observation)

    summaries = []
    for related_id, rows in grouped.items():
        entity_keys = {row.entity_key for row in rows}
        facebook_ids = {row.facebook_id for row in rows if row.facebook_id}
        names = {row.normalized_name for row in rows if row.normalized_name}
        if len(entity_keys) < 2 and len(facebook_ids) < 2 and len(names) < 2:
            continue
        summaries.append(_cross_summary_row(f"related_id:{related_id}", "shared_platform_object_id_across_identity_keys", rows))
    return summaries


def _cross_summary_by_related_value(observations: list[IdentityObservation]) -> list[VariantSummary]:
    grouped: dict[str, list[IdentityObservation]] = {}
    for observation in observations:
        if not observation.related_id_value:
            continue
        grouped.setdefault(observation.related_id_value, []).append(observation)

    summaries = []
    all_facebook_ids = {row.facebook_id for row in observations if row.facebook_id}
    for value, rows in grouped.items():
        related_types = {row.related_id_type for row in rows if row.related_id_type}
        if len(related_types) > 1:
            summaries.append(_cross_summary_row(f"related_value:{value}", "same_numeric_id_across_related_id_types", rows))
        if value in all_facebook_ids:
            summaries.append(_cross_summary_row(f"related_value_matches_facebook_id:{value}", "related_id_value_matches_facebook_id", rows))
    return summaries


def _related_family_summaries(observations: list[IdentityObservation]) -> list[VariantSummary]:
    grouped: dict[str, list[IdentityObservation]] = {}
    for observation in observations:
        if not observation.related_id_value:
            continue
        family = _related_family(observation.related_id_type)
        if not family:
            continue
        grouped.setdefault(family, []).append(observation)

    summaries = []
    for family, rows in grouped.items():
        variant_type = f"{family}_identifier_context"
        summaries.append(_cross_summary_row(f"related_family:{family}", variant_type, rows))
    return summaries


def _cross_summary_row(entity_key: str, variant_type: str, rows: list[IdentityObservation]) -> VariantSummary:
    names = sorted({row.name for row in rows if row.name})
    facebook_ids = sorted({row.facebook_id for row in rows if row.facebook_id})
    handles = sorted({row.handle_or_identifier for row in rows if row.handle_or_identifier})
    profile_urls = sorted({row.profile_url for row in rows if row.profile_url})
    vanity_slugs = sorted({row.vanity_slug for row in rows if row.vanity_slug})
    thread_identifiers = sorted({row.thread_identifier for row in rows if row.thread_identifier})
    participant_contexts = sorted({row.participant_context for row in rows if row.participant_context})
    ips = sorted({row.ip_address for row in rows if row.ip_address})
    related_ids = sorted({_format_related_id(row) for row in rows if row.related_id_value})
    deleted = any(row.deleted_user_observed for row in rows)
    confidence, explanation = _cross_summary_confidence(variant_type, rows, facebook_ids)
    return VariantSummary(
        entity_key=entity_key,
        variant_type=variant_type,
        observation_count=len(rows),
        facebook_ids=";".join(facebook_ids),
        names=";".join(names),
        handles_or_identifiers=";".join(handles),
        profile_urls=";".join(profile_urls),
        vanity_slugs=";".join(vanity_slugs),
        thread_identifiers=";".join(thread_identifiers),
        participant_contexts=";".join(participant_contexts),
        ip_addresses=";".join(ips),
        related_ids=";".join(related_ids),
        deleted_user_observed=deleted,
        first_timestamp=_first_timestamp(rows),
        last_timestamp=_last_timestamp(rows),
        source_paths=";".join(sorted({row.source_path for row in rows})),
        confidence=confidence,
        explanation=explanation,
    )


def _cross_summary_confidence(variant_type: str, rows: list[IdentityObservation], facebook_ids: list[str]) -> tuple[str, str]:
    if variant_type == "shared_profile_slug_across_identity_keys":
        return "medium", "The same profile slug appears across more than one identity key. Review source paths before treating this as a merge candidate."
    if variant_type == "shared_profile_url_across_identity_keys":
        return "medium", "The same profile URL appears across more than one identity key."
    if variant_type == "shared_handle_across_identity_keys":
        return "medium", "The same handle or identifier appears across more than one identity key."
    if variant_type == "same_normalized_name_different_facebook_ids":
        return "low", f"The same normalized name appears with {len(facebook_ids)} Facebook IDs. This may be a common-name collision."
    if variant_type == "shared_ip_across_identity_keys":
        return "low", f"{len(rows)} observations share IP context across identity keys. This is correlation, not proof of account control."
    if variant_type == "shared_platform_object_id_across_identity_keys":
        return "medium", "The same platform object ID appears with more than one identity key. Review the source context before linking identities."
    if variant_type == "same_numeric_id_across_related_id_types":
        return "medium", "The same numeric value appears under multiple related-ID labels. This can link object aliases such as post, story, target, or URL IDs."
    if variant_type == "related_id_value_matches_facebook_id":
        return "medium", "A related object/actor/owner ID value also appears as a Facebook profile ID elsewhere in the run."
    if variant_type == "contact_identifier_context":
        return "medium", "Email, phone, contact, or external identifier context appears in this run."
    if variant_type == "device_session_identifier_context":
        return "medium", "Device, app, session, browser, cookie, or account identifier context appears in this run."
    if variant_type == "commerce_payment_identifier_context":
        return "medium", "Payment, transaction, order, business, or commerce identifier context appears in this run."
    if variant_type == "reaction_or_engagement_identifier_context":
        return "low", "Reaction, like, or share identifier context appears in this run."
    if variant_type == "location_or_place_identifier_context":
        return "low", "Place, location, or check-in identifier context appears in this run."
    if variant_type == "social_graph_object_identifier_context":
        return "low", "Group, page, event, member, or invitation identifier context appears in this run."
    return "low", "Cross-identity variant evidence requires manual review."


def _summary_confidence(
    variant_type: str,
    rows: list[IdentityObservation],
    names: list[str],
    facebook_ids: list[str],
    ips: list[str],
) -> tuple[str, str]:
    if variant_type == "name_variant_same_facebook_id":
        return "high", f"{len(names)} name variants share the same Facebook ID evidence."
    if variant_type == "identifier_variant_same_facebook_id":
        return "high", "Multiple handles, profile slugs, or thread identifiers share the same Facebook ID evidence."
    if variant_type == "platform_object_id_with_facebook_id_context":
        return "medium", "A platform object ID appears alongside Facebook ID context."
    if variant_type == "contact_identifier_context":
        return "medium", "Email, phone, contact, or external identifier context is present near identity evidence."
    if variant_type == "device_session_identifier_context":
        return "medium", "Device, app, session, browser, cookie, or account identifier context is present."
    if variant_type == "commerce_payment_identifier_context":
        return "medium", "Payment, transaction, order, business, or commerce identifier context is present."
    if variant_type == "marketplace_identifier_context":
        return "medium", "Marketplace listing, seller, buyer, or product identifier context is present."
    if variant_type == "reaction_or_engagement_identifier_context":
        return "low", "Reaction, like, or share identifier context is present near identity evidence."
    if variant_type == "location_or_place_identifier_context":
        return "low", "Place, location, or check-in identifier context is present near identity evidence."
    if variant_type == "social_graph_object_identifier_context":
        return "low", "Group, page, event, or invitation identifier context is present near identity evidence."
    if variant_type == "platform_object_identifier_context":
        return "low", "A platform object ID is present without stronger identity context."
    if variant_type == "profile_url_identity":
        return "high", "A profile URL or vanity slug is present for this identity group."
    if variant_type == "thread_identifier_identity":
        return "medium", "A message thread identifier is present for this identity group."
    if variant_type == "participant_list_identity":
        return "medium", "A participant-list source links the identity evidence."
    if variant_type == "deleted_user_or_unavailable_label" and facebook_ids:
        return "medium", "A deleted or unavailable label appears with Facebook ID context."
    if facebook_ids and ips:
        return "medium", "Facebook ID evidence appears with IP context. This is correlation, not proof of identity control."
    if facebook_ids:
        return "medium", "Facebook ID evidence is present."
    if ips:
        return "low", "Only IP-linked identity context is present."
    return "low", f"{len(rows)} name-only observations were grouped."


def _entity_key(
    facebook_id: str,
    normalized_name: str,
    vanity_slug: str,
    thread_identifier: str,
    ip_address: str,
    related_id_type: str,
    related_id_value: str,
) -> str:
    if facebook_id:
        return f"facebook_id:{facebook_id}"
    if normalized_name:
        return f"name:{normalized_name}"
    if vanity_slug:
        return f"vanity_slug:{vanity_slug}"
    if thread_identifier:
        return f"thread:{thread_identifier}"
    if ip_address:
        return f"ip:{ip_address}"
    if related_id_value:
        return f"related_id:{related_id_type}:{related_id_value}"
    return "unknown"


def _observation_type(name: str, facebook_id: str, profile_url: str, ip_address: str, related_id_type: str, related_id_value: str) -> str:
    if DELETED_RE.search(name):
        return "deleted_user_label"
    if related_id_value and facebook_id:
        return "platform_object_id_with_facebook_id"
    if related_id_value and name:
        return "platform_object_id_with_name"
    if related_id_type.startswith("marketplace") or related_id_type in {"seller_id", "buyer_id"}:
        return "marketplace_identifier_context"
    if related_id_value:
        return "platform_object_identifier"
    if facebook_id and name:
        return "facebook_id_name_pair"
    if facebook_id:
        return "facebook_id_only"
    if profile_url:
        return "profile_url_identity"
    if ip_address:
        return "ip_identity_context"
    return "name_variant"


def _facebook_id_from_record(value: dict[str, Any], trail: str, path: str) -> str:
    direct = _first_for_keys(value, ID_KEYS)
    if direct:
        return direct
    raw_id = _text_from_value(value.get("id"))
    if not raw_id:
        return ""
    lower = f"{path}/{trail}/{' '.join(value.keys())}".lower()
    if any(token in lower for token in ("profile", "participant", "friend", "user", "actor", "author", "owner", "sender")):
        return raw_id
    return ""


def _related_ids_from_record(value: dict[str, Any], trail: str, path: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for key, raw_value in value.items():
        normalized_key = _normalize_key(key)
        related_type = RELATED_ID_KEYS.get(normalized_key)
        if not related_type and normalized_key == "id":
            related_type = _id_type_from_context(trail, path)
        if related_type:
            text = _text_from_value(raw_value)
            if _looks_like_identifier(text):
                rows.append((related_type, text, f"json_key:{key}"))
        text_value = _text_from_value(raw_value)
        if text_value:
            rows.extend(_related_ids_from_text(text_value, f"json_key:{key}"))
    rows.extend(_contact_ids_from_record(value))
    rows.extend(_related_ids_from_path(path))
    return _dedupe_related_ids(rows)


def _related_ids_from_text(value: str, context: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for match in URL_ID_RE.finditer(value):
        key = _normalize_key(match.group("key"))
        rows.append((RELATED_ID_KEYS.get(key, key), match.group("value"), f"{context}:url_parameter:{key}"))
    for match in URL_ROUTE_ID_RE.finditer(value):
        rows.append((_route_id_type(match.group(0)), match.group("value"), f"{context}:url_route"))
    for match in EMAIL_RE.finditer(value):
        rows.append(("email_address", match.group(0).lower(), f"{context}:email"))
    for match in PHONE_RE.finditer(value):
        phone = _normalize_phone(match.group(0))
        if phone:
            rows.append(("phone_number", phone, f"{context}:phone"))
    return _dedupe_related_ids(rows)


def _related_ids_from_path(path: str) -> list[tuple[str, str, str]]:
    rows = []
    for match in PATH_ID_RE.finditer(path.replace("\\", "/")):
        kind = match.group("kind").lower()
        rows.append((PATH_ID_TYPES.get(kind, f"{kind}_id"), match.group("id"), "source_path"))
    return _dedupe_related_ids(rows)


def _id_type_from_context(trail: str, path: str) -> str:
    lower = f"{path}/{trail}".lower()
    checks = (
        ("marketplace", "marketplace_listing_id"),
        ("listing", "marketplace_listing_id"),
        ("payment", "payment_id"),
        ("transaction", "transaction_id"),
        ("order", "order_id"),
        ("business", "business_id"),
        ("device", "device_id"),
        ("session", "session_id"),
        ("browser", "browser_id"),
        ("cookie", "cookie_id"),
        ("app", "app_id"),
        ("contact", "contact_id"),
        ("email", "email_address"),
        ("phone", "phone_number"),
        ("reaction", "reaction_id"),
        ("like", "like_id"),
        ("share", "share_id"),
        ("checkin", "checkin_id"),
        ("place", "place_id"),
        ("location", "location_id"),
        ("seller", "seller_id"),
        ("buyer", "buyer_id"),
        ("notification", "notification_id"),
        ("comment", "comment_id"),
        ("photo", "photo_id"),
        ("video", "video_id"),
        ("story", "story_id"),
        ("post", "post_id"),
        ("group", "group_id"),
        ("page", "page_id"),
        ("event", "event_id"),
        ("tag", "tag_id"),
    )
    for token, related_type in checks:
        if token in lower:
            return related_type
    return "object_id"


def _route_id_type(value: str) -> str:
    lower = value.lower()
    if "/marketplace/item/" in lower:
        return "marketplace_listing_id"
    if "/groups/" in lower:
        return "group_id"
    if "/events/" in lower:
        return "event_id"
    if "/pages/" in lower:
        return "page_id"
    if "/photos/" in lower:
        return "photo_id"
    if "/videos/" in lower or "/watch/" in lower:
        return "video_id"
    if "/reel/" in lower or "/reels/" in lower:
        return "reel_id"
    if "/posts/" in lower or "/permalink/" in lower:
        return "post_id"
    return "object_id"


def _contact_ids_from_record(value: dict[str, Any]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for key in ("email", "email_address", "contact_email"):
        text = _text_from_value(value.get(key))
        if text:
            rows.extend((related_type, related_value, f"json_key:{key}") for related_type, related_value, _ in _related_ids_from_text(text, f"json_key:{key}") if related_type == "email_address")
    for key in ("phone", "phone_number", "mobile_phone", "contact_phone"):
        text = _text_from_value(value.get(key))
        if text:
            rows.extend((related_type, related_value, f"json_key:{key}") for related_type, related_value, _ in _related_ids_from_text(text, f"json_key:{key}") if related_type == "phone_number")
    return rows


def _format_related_id(row: IdentityObservation) -> str:
    return f"{row.related_id_type}:{row.related_id_value}" if row.related_id_type else row.related_id_value


def _variant_anchors(observation: IdentityObservation) -> list[tuple[str, str]]:
    candidates = [
        ("facebook_id", observation.facebook_id),
        ("name", observation.normalized_name),
        ("handle", observation.handle_or_identifier),
        ("profile_url", observation.profile_url),
        ("vanity_slug", observation.vanity_slug),
        ("thread_id", observation.thread_identifier),
        ("ip", observation.ip_address),
    ]
    if observation.related_id_value:
        candidates.append(("related_id", _format_related_id(observation)))
    if not any(value for _, value in candidates) and observation.entity_key:
        candidates.append(("entity_key", observation.entity_key))

    seen: set[tuple[str, str]] = set()
    anchors = []
    for variant_id_type, variant_id_value in candidates:
        if not variant_id_value:
            continue
        key = (variant_id_type, variant_id_value)
        if key in seen:
            continue
        seen.add(key)
        anchors.append(key)
    return anchors


def _interaction_date(timestamp: str) -> str:
    return timestamp[:10] if re.match(r"\d{4}-\d{2}-\d{2}", timestamp) else ""


def _related_id_has_prefix(value: str, prefixes: tuple[str, ...]) -> bool:
    return any(value.startswith(prefix + ":") for prefix in prefixes)


def _related_family(related_id_type: str) -> str:
    families = {
        "contact": {"contact_id", "email_address", "external_id", "phone_number"},
        "device_session": {"account_id", "app_id", "browser_id", "cookie_id", "device_id", "session_id"},
        "commerce_payment": {"business_id", "order_id", "payment_id", "transaction_id"},
        "reaction_or_engagement": {"like_id", "reaction_id", "share_id"},
        "location_or_place": {"checkin_id", "location_id", "place_id"},
        "social_graph_object": {"event_id", "group_id", "invite_id", "member_id", "page_id"},
    }
    for family, values in families.items():
        if related_id_type in values:
            return family
    return ""


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _looks_like_identifier(value: str) -> bool:
    return bool(value and re.fullmatch(r"[A-Za-z0-9_.:-]{3,}", value))


def _normalize_phone(value: str) -> str:
    raw = value.strip()
    if IP_RE.fullmatch(raw):
        return ""
    if not raw.startswith("+") and not re.search(r"[\s().-]", raw):
        return ""
    digits = re.sub(r"\D+", "", value)
    if len(digits) < 8 or len(digits) > 15:
        return ""
    return "+" + digits if raw.startswith("+") else digits


def _dedupe_related_ids(rows: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    seen: set[tuple[str, str]] = set()
    result = []
    for related_type, related_value, context in rows:
        key = (related_type, related_value)
        if key in seen:
            continue
        seen.add(key)
        result.append((related_type, related_value, context))
    return result


def _walk_dicts(value: Any, trail: str) -> Iterable[tuple[dict[str, Any], str]]:
    if isinstance(value, dict):
        yield value, trail
        for key, nested in value.items():
            child_trail = f"{trail}.{key}" if trail else key
            yield from _walk_dicts(nested, child_trail)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _walk_dicts(nested, f"{trail}[{index}]")


def _first_for_keys(value: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        if key in value:
            text = _text_from_value(value.get(key))
            if text:
                return text
    return ""


def _participant_context(trail: str, path: str) -> str:
    lower = f"{path}/{trail}".lower()
    if "participant" in lower:
        return "participant_list"
    if "messages" in lower and any(part in lower for part in ("inbox", "archived_threads", "e2ee_cutover")):
        return "message_thread"
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


def _first_ip(value: str) -> str:
    match = IP_RE.search(value)
    return match.group(0) if match else ""


def _thread_identifier_from_path(path: str) -> str:
    match = THREAD_DIR_RE.search(path)
    if not match:
        return ""
    raw_name, facebook_id = match.groups()
    return f"{raw_name}_{facebook_id}" if facebook_id else raw_name


def _vanity_slug(profile_url: str, handle: str, thread_identifier: str) -> str:
    for value in (profile_url, handle, thread_identifier):
        if not value:
            continue
        match = PROFILE_SLUG_RE.search(value)
        if match:
            slug = match.group(1)
            if slug.lower() not in RESERVED_FACEBOOK_SLUGS:
                return slug
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{2,}", value):
            return value
    return ""


def _name_from_slug(value: str) -> str:
    if DELETED_RE.search(value):
        return "Facebook user"
    cleaned = re.sub(r"[_-]+", " ", value)
    cleaned = re.sub(r"\d+", "", cleaned)
    return " ".join(part.capitalize() for part in cleaned.split()) or value


def _normalize_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return " ".join(normalized.split())


def _confidence(facebook_id: str, name: str, ip_address: str, deleted: bool, related_id_value: str) -> str:
    if facebook_id and name and not deleted:
        return "high"
    if facebook_id or (name and ip_address):
        return "medium"
    if related_id_value and (name or ip_address):
        return "medium"
    return "low"


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
    for fmt in ("%b %d %Y %I:%M %p", "%b %d %Y %I:%M:%S %p", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _first_timestamp(rows: list[IdentityObservation]) -> str:
    timestamps = [row.timestamp for row in rows if row.timestamp]
    return min(timestamps) if timestamps else ""


def _last_timestamp(rows: list[IdentityObservation]) -> str:
    timestamps = [row.timestamp for row in rows if row.timestamp]
    return max(timestamps) if timestamps else ""


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
