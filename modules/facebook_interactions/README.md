# Project Recovery Facebook Interactions

Optional timestamped interaction module for Project Recovery Facebook exports.

This module is separate from the Facebook Reader model so users can choose
whether to run the interaction timeline layer.

## Purpose

Facebook exports store interaction signals across many JSON surfaces, not just
message threads. This module scans those surfaces and produces a timestamped
list of interaction-like records and a per-entity count summary.

It is designed as a companion module to:

- Project Recovery Facebook Reader v1
- Project Recovery Core Engine

It does not modify either repository.

## What It Scans

The module scans timestamped records from surfaces such as:

- `logged_information/interactions`
- `logged_information/notifications`
- `logged_information/activity_messages`
- `your_facebook_activity/comments_and_reactions`
- `your_facebook_activity/groups`
- `your_facebook_activity/posts`
- `connections/friends`
- `connections/followers`

## Outputs

For each run, the module writes:

- `interactions_by_timestamp.jsonl`
- `interactions_by_timestamp.csv`
- `entity_interaction_summary.json`
- `entity_interaction_summary.csv`
- `run_summary.json`

Each timestamped row includes timestamp, raw timestamp, interaction type,
action, actor, target, entity name, handle or profile identifier when present,
summary, source path, source hash, and raw payload path.

The entity summary lists identified names, handles or profile identifiers, total
interaction count, first timestamp, last timestamp, observed interaction types,
and source paths.

## Intended Questions

This module is meant to answer:

- Which names, handles, pages, groups, or identifiers appear in interaction data?
- When did each interaction occur?
- How many interactions are associated with each identified entity?
- What is the first and last timestamp for each entity?
- Which source files and raw JSON paths support the result?

## Quick Run

```powershell
python -m facebook_interactions.cli `
  --source modules/facebook_interactions/examples/facebook_sample `
  --output outputs/sample_interactions
```

Use an extracted Facebook export folder or a `.zip` export as `--source`.

## Privacy Boundary

This public repository contains synthetic sample data only. Do not commit real
Facebook exports, generated outputs, private jobs, or case material.
