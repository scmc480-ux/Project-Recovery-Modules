# Changelog

## 0.3.0

- Added `facebook_identity_variants` initial runnable module.
- Added deleted-user and unavailable-user label detection.
- Added name variant grouping by Facebook ID.
- Added handle, message-thread identifier, and IP-linked identity context extraction.
- Added profile URL, vanity slug, and participant-list identity signals.
- Added cross-identity review leads for shared IP context, same-name/different-ID records, reused handles, and reused profile slugs.
- Added wide related-ID extraction for Marketplace, notifications, posts, comments, tags, media, URL parameters, actor/owner/target IDs, and source-path IDs.
- Added popup/push notification and Facebook email notification ID tagging for `fbid`, target/source/profile IDs, and notification URL parameters.
- Added owner identity crosscheck outputs with confirmed-owner-first roster, first-contact identity/variant timeline, unassigned-ID appendix, and text report.
- Added optional alias-map support plus master identity alias cluster and master first-contact timeline outputs for case-reviewed variant groupings.
- Added contact, device/session/app, engagement, location/place, social-graph, commerce/payment, and relabeled numeric-ID variant summaries.
- Added per-variant timeline outputs that list dated interactions by identified variant ID.
- Added identity observation and variant summary outputs in JSONL, JSON, and CSV.
- Added synthetic identity variant sample data and tests.

## 0.2.0

- Added `facebook_ip_correlation` initial runnable module.
- Added HTML and JSON extraction for Facebook IP, login, device, session, and location-adjacent records.
- Added IP observation outputs in JSONL and CSV.
- Added same-IP and same-subnet correlation summaries in JSON and CSV.
- Added confidence labels and source provenance for IP observations.
- Added synthetic IP correlation sample data and tests.
- Updated public-readiness scanning to include HTML fixtures.

## 0.1.0

- Established Project Recovery Modules as the optional extension repository.
- Added `facebook_interactions` as the first implemented module.
- Added timestamped JSON and zip scanning.
- Added JSONL and CSV outputs.
- Added entity interaction summaries with counts, first timestamps, and last timestamps.
- Added synthetic sample data and tests.
