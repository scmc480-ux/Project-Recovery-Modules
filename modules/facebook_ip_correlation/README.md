# Facebook IP Correlation

<sub><em>Building tomorrow's recovery framework, one module at a time.</em></sub>

---

Optional IP and location correlation module for Project Recovery.

This module is intentionally separate from `facebook_interactions` because IP
and location correlation is a different evidentiary layer.

## Intended Purpose

The module compares identified IP/network/location signals against
timestamped interaction context.

Current outputs include:

- exact IP matches
- subnet or network proximity
- approximate geolocation matches
- GPS or precise device-location records when explicitly present in the export
- device or session context when present
- confidence labels and plain-English explanations

## Quick Run

```powershell
python -m facebook_ip_correlation.cli `
  --source modules/facebook_ip_correlation/examples/facebook_sample `
  --output outputs/sample_ip_correlation
```

## Outputs

For each run, the module writes:

- `ip_observations.jsonl`
- `ip_observations.csv`
- `ip_correlation_summary.json`
- `ip_correlation_summary.csv`
- `run_summary.json`

Each observation includes timestamp, raw timestamp, IP address, IP version,
location signal type, source path, source hash, raw payload path, device label,
session label, browser label, approximate location, precise location,
confidence, and explanation.

## Evidence Boundary

IP-derived location is approximate. It may reflect a household, workplace,
carrier gateway, VPN, public network, or shared infrastructure. GPS or precise
device-location records, when present, are a separate and stronger category of
location evidence.

IP correlation is not proof of physical proximity. It can produce investigative
leads, but conclusions must remain tied to the available source data,
timestamps, provenance, and confidence label.

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
