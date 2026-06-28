# Quickstart

## 1. Clone And Enter The Repo

```powershell
git clone <repo-url> Project-Recovery-Modules
cd Project-Recovery-Modules
```

## 2. Run The Sample

```powershell
python -m facebook_interactions.cli --source modules/facebook_interactions/examples/facebook_sample --output outputs/sample_interactions
```

## 3. Inspect Outputs

Open:

```text
outputs/sample_interactions/interactions_by_timestamp.jsonl
outputs/sample_interactions/interactions_by_timestamp.csv
outputs/sample_interactions/entity_interaction_summary.json
outputs/sample_interactions/entity_interaction_summary.csv
outputs/sample_interactions/run_summary.json
```

## 4. Run Against Your Own Export

```powershell
python -m facebook_interactions.cli --source "<path-to-facebook-export>" --output outputs/my_interactions
```

Do not commit your export or generated outputs.
