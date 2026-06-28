# Project Recovery Modules

<sub><em>Building tomorrow's recovery framework, one module at a time.</em></sub>

---

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
| `facebook_interactions` | v0.1.0 | Extract names, handles or identifiers, timestamps, interaction rows, and entity interaction counts. |
| `facebook_ip_correlation` | v0.1.0 | Extract and correlate identified IP/network/location signals with timestamps and context without treating IP location as proof. |
| `facebook_identity_variants` | v0.1.0 | Track deleted-user labels, name variants, Facebook IDs, profile URLs, thread identifiers, Marketplace/object IDs, notification IDs, contact/device/session anchors, reused identifiers, and IP-linked identity context. |

## Repository Layout

```text
Project-Recovery-Modules/
+-- README.md
+-- QUICKSTART.md
+-- LICENSE
+-- modules/
|   +-- facebook_interactions/
|   +-- facebook_ip_correlation/
|   +-- facebook_identity_variants/
+-- scripts/
+-- tests/
```

Each module must remain optional, documented, and safe to run independently.

## Module Boundaries

`facebook_interactions` answers who interacted, when they interacted, how often
they appeared, and which Facebook export surface produced the record.

`facebook_ip_correlation` is reserved for account, network, device, session, and
location-adjacent signals. It should compare identified IP evidence with
timestamps and interaction context, but it must label results as correlation
rather than proof of physical proximity.

`facebook_identity_variants` tracks names, deleted-user labels, Facebook IDs,
handles, profile URLs, vanity slugs, participant lists, message-thread
identifiers, reused handles or profile slugs, same-name/different-ID leads, and
IP-linked identity context. It also preserves related Marketplace, notification,
post, comment, tag, photo, video, story, group, page, event, actor, owner, and
target IDs as review leads, plus contact, device, session, app, engagement,
location, and commerce/payment identifiers when present. It must label variant
matches as correlation rather than proof of account control.

## Privacy Boundary

This public repository contains synthetic sample data only. Do not commit real
exports, private case material, generated outputs, jobs, or evidence.

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
