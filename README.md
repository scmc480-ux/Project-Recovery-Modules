# Project Recovery Modules

Optional extension modules for the Project Recovery ecosystem.

This repository is the public home for add-on modules that are useful for some
cases but should not be forced into the core engine or a specific reader model.

## Purpose

Project Recovery separates reusable recovery infrastructure from optional
analysis layers. This keeps the core engine small while allowing users to add
specialized modules when their case needs them.

## Current Modules

| Module | Status | Purpose |
| --- | --- | --- |
| `facebook_interactions` | v0.1.0 | Extract timestamped Facebook interaction rows and entity interaction counts. |
| `facebook_ip_correlation` | Planned | Correlate identified IP/network/location signals with timestamps and interaction context. |

## Repository Layout

```text
Project-Recovery-Modules/
├── README.md
├── QUICKSTART.md
├── LICENSE
├── modules/
│   ├── facebook_interactions/
│   └── facebook_ip_correlation/
├── scripts/
└── tests/
```

Each module must remain optional, documented, and safe to run independently.

## Privacy Boundary

This public repository contains synthetic sample data only. Do not commit real
exports, private case material, generated outputs, jobs, or evidence.

