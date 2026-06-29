# Quickstart

Install from a clean clone:

```powershell
python -m pip install -e .
```

Run the Facebook interactions sample:

```powershell
python -m facebook_interactions.cli `
  --source modules/facebook_interactions/examples/facebook_sample `
  --output outputs/sample_interactions
```

Expected outputs:

- `interactions_by_timestamp.jsonl`
- `interactions_by_timestamp.csv`
- `entity_interaction_summary.json`
- `entity_interaction_summary.csv`
- `run_summary.json`

Use an extracted Facebook export folder or a `.zip` export as `--source`.

Run the Facebook IP correlation sample:

```powershell
python -m facebook_ip_correlation.cli `
  --source modules/facebook_ip_correlation/examples/facebook_sample `
  --output outputs/sample_ip_correlation
```

Expected outputs:

- `ip_observations.jsonl`
- `ip_observations.csv`
- `ip_correlation_summary.json`
- `ip_correlation_summary.csv`
- `run_summary.json`

Run the Facebook identity variants sample:

```powershell
python -m facebook_identity_variants.cli `
  --source modules/facebook_identity_variants/examples/facebook_sample `
  --output outputs/sample_identity_variants
```

Optionally pass a case-reviewed alias hypothesis map:

```powershell
python -m facebook_identity_variants.cli `
  --source path\to\facebook_json_export `
  --output outputs\sample_identity_variants `
  --alias-map path\to\identity_aliases.json
```

Alias maps do not merge identities by themselves. The module promotes a
proposed alias only when timestamped export data connects it to the master
identity through same-session search, profile visit, page/follow, content-view,
or profile-update evidence.

Expected outputs:

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

Use the same identity variants CLI for a multi-pack batch with master crosscheck files:

```powershell
python -m facebook_identity_variants.cli `
  --source path\to\facebook_export_pack_1 `
  --source path\to\facebook_export_pack_2 `
  --output outputs\sample_identity_variants_batch
```

The batch writer creates master outputs such as
`OWNER_IDENTITY_VARIANT_CROSSCHECK_ROSTER.csv` without requiring real case data
in the repository.
