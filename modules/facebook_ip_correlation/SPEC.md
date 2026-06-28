# Facebook IP Correlation Specification

Status: planned

## Scope

The module will ingest Facebook export surfaces that contain account activity,
login, session, device, IP, or location-adjacent records.

It will not be part of the Facebook Reader v1 model and will remain optional.

The module must distinguish IP-derived approximate location from precise
device-location records, such as GPS/location-history style data when those
records are explicitly present in an export.

## Planned Record Fields

- `timestamp`
- `timestamp_raw`
- `ip_address`
- `ip_version`
- `location_signal_type`
- `source_path`
- `source_sha256`
- `raw_payload_path`
- `device_label`
- `session_label`
- `approximate_location`
- `precise_location`
- `time_window_seconds`
- `related_interaction_ids`
- `confidence`
- `explanation`

## Planned Correlation Labels

- `same_ip`
- `same_subnet`
- `same_asn_or_isp`
- `same_geo_area`
- `precise_location_nearby`
- `close_timestamp`
- `device_or_session_overlap`

## Interpretation Rule

Every result must be labeled as correlation, not proof of shared physical
location.

## Confidence Guidance

- `high`: exact IP plus close timestamp and supporting device/session evidence,
  or explicit precise-location evidence.
- `medium`: exact IP or same narrow network range with close timestamps.
- `low`: same broad region, same ISP, or weak IP-derived geolocation only.

The explanation field must state why the confidence was assigned and identify
the source records used.
