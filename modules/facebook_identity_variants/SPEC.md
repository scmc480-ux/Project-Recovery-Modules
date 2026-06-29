# Facebook Identity Variants Specification

Status: initial implementation

## Scope

The module ingests Facebook export surfaces that contain names, profile IDs,
handles, profile URLs, vanity slugs, participant lists, message-thread path
identifiers, deleted-user labels, IP context, platform object IDs, Marketplace
IDs, notification IDs, popup/push notification actor/target/source IDs, email
notification `fbid` tags, post/comment IDs, tag IDs, media IDs,
group/page/event IDs, actor/owner/target IDs, contact anchors,
device/session/app IDs, engagement IDs, location/place/check-in IDs, and
commerce/payment IDs.

It is not part of the Facebook Reader v1 model and remains optional.

## Record Fields

- `timestamp`
- `timestamp_raw`
- `observation_type`
- `entity_key`
- `facebook_id`
- `name`
- `normalized_name`
- `handle_or_identifier`
- `profile_url`
- `vanity_slug`
- `thread_identifier`
- `participant_context`
- `ip_address`
- `related_id_type`
- `related_id_value`
- `related_id_context`
- `deleted_user_observed`
- `source_path`
- `source_sha256`
- `raw_payload_path`
- `confidence`
- `explanation`

## Timeline Fields

The module also writes `identity_variant_timeline.jsonl` and
`identity_variant_timeline.csv`. Each row represents one interaction attached to
one identified variant anchor.

- `variant_id`
- `variant_id_type`
- `variant_id_value`
- `interaction_date`
- `timestamp`
- all observation provenance and context fields needed to trace the row back to
  the source record

Timeline rows are sorted by `variant_id`, then timestamp, then source path.

## Owner Crosscheck Fields

The module also writes reviewer-facing owner/variant outputs:

- `owner_identity_roster.json`
- `owner_identity_roster.csv`
- `owner_identity_first_contact_timeline.jsonl`
- `owner_identity_first_contact_timeline.csv`
- `owner_identity_unassigned_id_variants.json`
- `owner_identity_unassigned_id_variants.csv`
- `owner_identity_crosscheck_report.txt`
- `master_identity_alias_clusters.json`
- `master_identity_alias_clusters.csv`
- `master_identity_first_contact_timeline.jsonl`
- `master_identity_first_contact_timeline.csv`

The roster places `CONFIRMED_ACCOUNT_OWNER` first only when native
`personal_information/profile_information/profile_information.json` owner-name
evidence is present. Other rows are `observed_identity` variants. Roster fields
include observed Facebook/profile IDs, phone numbers, email addresses, profile
URLs, vanity slugs, thread identifiers, IP context, other identifying IDs,
source-path samples, and first-contact references.

The first-contact timeline records the earliest non-placeholder interaction for
each master identity and each variant anchor. Dates such as `1970-01-01` are
treated as placeholder/epoch values and excluded from first-contact selection.

The unassigned-ID output preserves identifiable IDs that could not be safely
attached to a named identity.

## Alias Maps

The CLI accepts `--alias-map path/to/identity_aliases.json`. The module also
auto-loads `identity_aliases.json` or `facebook_identity_aliases.json` from the
source folder or its parent folder when present.

Alias maps are hypothesis inputs, not proof. The module promotes an alias into a
master identity only when timestamped Facebook export data connects that alias
to the master through a same-session chain of search history, profile visits,
content views, follows/pages, or profile-update activity. The generated cluster
rows include `alias_cluster_evidence`; aliases without data support remain as
separate observed identity rows.

Alias map shape:

```json
{
  "clusters": [
    {
      "alias_cluster_id": "alias_cluster:example",
      "master_identity": "Example Person",
      "aliases": ["Example Person", "Example Handle", "Example Page"],
      "confidence": "candidate_alias_map",
      "explanation": "Case review supplied this alias hypothesis."
    }
  ]
}
```

Alias maps do not delete or overwrite original observed identity rows. When the
data supports a proposed alias, the module adds `master_identity_key`,
`master_identity_name`, `alias_cluster_id`, data-supported confidence,
explanation, and evidence fields to the roster, and writes master-level cluster
and first-contact timeline outputs.

## Summary Labels

- `name_variant_same_facebook_id`
- `identifier_variant_same_facebook_id`
- `deleted_user_or_unavailable_label`
- `facebook_id_with_ip_context`
- `profile_url_identity`
- `thread_identifier_identity`
- `participant_list_identity`
- `facebook_id_identity`
- `ip_only_identity_context`
- `name_only_identity`
- `platform_object_id_with_facebook_id_context`
- `platform_object_identifier_context`
- `marketplace_identifier_context`
- `contact_identifier_context`
- `device_session_identifier_context`
- `commerce_payment_identifier_context`
- `reaction_or_engagement_identifier_context`
- `location_or_place_identifier_context`
- `social_graph_object_identifier_context`
- `shared_ip_across_identity_keys`
- `same_normalized_name_different_facebook_ids`
- `shared_handle_across_identity_keys`
- `shared_profile_url_across_identity_keys`
- `shared_profile_slug_across_identity_keys`
- `shared_platform_object_id_across_identity_keys`
- `same_numeric_id_across_related_id_types`
- `related_id_value_matches_facebook_id`

## Cross-Identity Review Ideas

The module may emit cross-identity summary rows when one value appears across
more than one entity key. These rows are review leads only. They can identify:

- IP context shared by multiple identity keys
- a normalized name appearing with different Facebook IDs
- a handle appearing across multiple identity keys
- a profile or vanity slug appearing across multiple identity keys
- a Marketplace listing, seller, buyer, or product ID near identity context
- a post, comment, tag, notification, photo, video, story, group, page, event,
  actor, owner, or target ID near identity context
- notification URLs, popup/push notification records, and email notifications
  sent by Facebook when they carry `fbid`, `target_id`, `source_id`,
  `settings_notif_id`, or other URL/user ID tags
- the same platform object ID appearing near more than one identity key
- the same numeric value appearing under different labels, such as `post_id`,
  `story_fbid`, `target_id`, or URL `id`
- a related object/actor/owner ID matching a Facebook profile ID elsewhere
- email, phone, contact, account, device, session, browser, cookie, app,
  reaction, like, share, place, check-in, payment, transaction, order, or
  business identifiers near identity context

Cross-identity rows must not merge identities automatically.

## Interpretation Rule

Every result must be labeled as correlation. A name variant, shared IP, or
deleted-user label is not proof of account control without supporting evidence.
