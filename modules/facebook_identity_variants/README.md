# Facebook Identity Variants

<sub><em>Building tomorrow's recovery framework, one module at a time.</em></sub>

---

Optional deleted-user and identity variant tracking module for Project Recovery.

This module tracks identity observations across Facebook exports where names,
labels, profile IDs, handles, and IP context may appear in different forms.

## Intended Purpose

The module is designed to help identify:

- deleted or unavailable user labels
- name changes or name variants tied to the same Facebook ID
- profile IDs observed across different source surfaces
- handles or profile identifiers linked to names
- profile URLs and vanity slugs
- message thread folder identifiers
- participant-list context
- IP context that appears alongside identity records
- same-name/different-ID review leads
- reused handle or profile-slug review leads
- IP context shared across identity keys
- Marketplace listing, seller, buyer, and product identifiers
- notification IDs, popup/push notification actor/target/source IDs, and email
  notification `fbid`/notification URL tags
- post, comment, tag, photo, video, story, group, page, and event IDs
- URL parameter IDs and source-path IDs that appear near identity records
- email, phone, contact, account, app, device, session, browser, and cookie IDs
- reaction, like, share, place, check-in, payment, transaction, order, business,
  member, and invitation IDs
- alias-style IDs where the same numeric value appears under different labels

## Evidence Boundary

Identity variant tracking is correlation, not proof of account control. A shared
IP address, repeated name, or deleted-user label can be useful evidence, but it
must remain tied to source paths, timestamps, and confidence labels.

## Quick Run

```powershell
python -m facebook_identity_variants.cli `
  --source modules/facebook_identity_variants/examples/facebook_sample `
  --output outputs/sample_identity_variants
```

Suspected aliases can be supplied with an alias map:

```powershell
python -m facebook_identity_variants.cli `
  --source path\to\facebook_json_export `
  --output outputs\identity_variants `
  --alias-map path\to\identity_aliases.json
```

If `identity_aliases.json` or `facebook_identity_aliases.json` exists in the
source folder or its parent folder, the module loads it automatically. Alias
maps are treated as review hypotheses: an alias is promoted into a master
identity only when timestamped Facebook data connects it to the master through a
same-session search/profile/page activity chain.

## Outputs

For each run, the module writes:

- `identity_observations.jsonl`
- `identity_observations.csv`
- `identity_variant_summary.json`
- `identity_variant_summary.csv`
- `identity_variant_timeline.jsonl`
- `identity_variant_timeline.csv`
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
- `run_summary.json`

Each observation includes timestamp, observation type, entity key, Facebook ID,
name, normalized name, handle or identifier, profile URL, vanity slug, thread
identifier, participant context, IP address, related platform ID type/value,
related ID context, deleted-user flag, source path, source hash, raw payload
path, confidence, and explanation.

The summary output includes direct identity groups plus cross-identity review
leads such as shared IP context, same normalized name across different Facebook
IDs, reused handles, reused profile slugs, Marketplace object IDs, notification
IDs, post/comment/tag/media IDs, contact/device/session anchors, commerce IDs,
engagement IDs, location IDs, and shared or relabeled platform object IDs.

The timeline output lists every dated interaction by `variant_id`, so a reviewer
can filter one identified variant anchor and read its source-backed interactions
in chronological order.

The owner identity outputs put the confirmed account owner first when native
`profile_information.json` owner-name evidence is present. They then list other
observed identity variants with phone numbers, Facebook/profile IDs, email
addresses, profile URLs, thread IDs, and other platform identifiers where the
data supports them. The first-contact timeline records the earliest
non-placeholder interaction for each master identity and variant anchor.
Unassigned ID outputs preserve identifiable IDs that were not safely tied to a
named identity.

Alias-map outputs preserve original observed identities while adding a master
identity layer for data-supported aliases. This is useful when case review has
identified likely names, handles, pages, or business profiles, but the module
still requires the export itself to connect those aliases through timestamped
search/profile/page activity before merging them. Unsupported aliases remain as
their original observed identity rows, and supported rows include the evidence
chain used for the merge.

---

# Project Ecosystem

### Project Recovery

<sub><em>Building tomorrow's recovery framework, one module at a time.</em></sub>

https://github.com/scmc480-ux/Project-Recovery

---

### Project Symphony

<sub><em>One Vision. Infinite Perspectives.</em></sub>

https://github.com/scmc480-ux/Project-Symphony

---

### Project Orchestra

<sub><em>Become the Conductor. Orchestrate Intelligence.</em></sub>

https://github.com/scmc480-ux/Project-Orchestra
