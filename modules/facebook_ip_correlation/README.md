# Facebook IP Correlation

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
- time-window overlap
- device or session overlap when present
- confidence labels and plain-English explanations

## Evidence Boundary

IP correlation is not proof of physical proximity. It can produce investigative
leads, but conclusions must remain tied to the available source data,
timestamps, and provenance.

