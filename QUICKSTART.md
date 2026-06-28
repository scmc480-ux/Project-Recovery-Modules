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

