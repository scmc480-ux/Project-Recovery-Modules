# Facebook IP Correlation Specification

Status: planned

## Scope

The module will ingest Facebook export surfaces that contain account activity,
login, session, device, IP, or location-adjacent records.

It will not be part of the Facebook Reader v1 model and will remain optional.

## Planned Record Fields

- `timestamp`
- `timestamp_raw`
- `ip_address`
- `ip_version`
- `source_path`
- `source_sha256`
- `raw_payload_path`
- `device_label`
- `session_label`
- `approximate_location`
- `confidence`
- `explanation`

## Planned Correlation Labels

- `same_ip`
- `same_subnet`
- `same_asn_or_isp`
- `same_geo_area`
- `close_timestamp`
- `device_or_session_overlap`

## Interpretation Rule

Every result must be labeled as correlation, not proof of shared physical
location.

