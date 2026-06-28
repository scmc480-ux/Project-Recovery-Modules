# Facebook IP Correlation

*Building tomorrow's recovery framework, one module at a time.*

---

Planned optional module for Project Recovery.

This module is intentionally separate from `facebook_interactions` because IP
and location correlation is a different evidentiary layer.

## Intended Purpose

The module will compare identified IP/network/location signals against
timestamped interaction context.

Potential outputs include:

- exact IP matches
- subnet or network proximity
- approximate geolocation matches
- GPS or precise device-location records when explicitly present in the export
- time-window overlap
- device or session overlap when present
- confidence labels and plain-English explanations

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

*Building tomorrow's recovery framework, one module at a time.*

https://github.com/scmc480-ux/Project-Recovery

---

### Project Symphony

*One Vision. Infinite Perspectives.*

https://github.com/scmc480-ux/Project-Symphony

---

### Project Orchestra

*Become the Conductor. Orchestrate Intelligence.*

https://github.com/scmc480-ux/Project-Orchestra
