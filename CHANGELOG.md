# Changelog

All notable changes to DPC Alert. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Since 2021.3.1,
versions follow calendar versioning (YEAR.MONTH.PATCH); earlier versions were
numbered 1.x. Pre-releases are not listed: their changes are in the release
that followed them.

## [Unreleased]

The DPC data now comes from the [aiodpc](https://pypi.org/project/aiodpc/)
library, entity names follow the language of Home Assistant, and `expires`
marks the end of the day it refers to.

### Added

- Translations in English, Italian and Brazilian Portuguese of the
  configuration, the options, and the names of the entities and of their
  attributes ([#87]).
- Automated tests with a CI workflow ([#90]).

### Changed

These changes can affect automations, templates and dashboards made for
2026.2.0:

| 2026.2.0 | Now |
| --- | --- |
| `expires` at the start of its day (`2026-11-14T00:00:00` for today) | At the end of its day, with time zone (`2026-11-15T00:00:00+01:00`) |
| `expires`, `publication_date` and `last_update` without time zone | `expires` and `publication_date` in Italian time, `last_update` in the Home Assistant time zone |
| Device `Dipartimento Protezione Civile DPC` | Device named after the location (`DPC`) |
| Entity names in Italian (`Dipartimento Protezione Civile DPC Rischio Idraulico Oggi`) | Names in the Home Assistant language (`DPC Rischio idraulico oggi`, `DPC Hydraulic risk today`) |
| No minimum Home Assistant version | Home Assistant 2025.2 or newer |

Entity IDs, states and the other attributes do not change, and names you set
yourself are kept. Notifications that use `friendly_name` show the new names.

- The DPC bulletins are read with aiodpc instead of the integration's own
  client ([#90]).
- Entities are unavailable, instead of empty, while their bulletin has never
  been fetched ([#90]).
- The radius option cannot be negative ([#90]).

### Fixed

- `expires` pointed to the start of the day it refers to, so it was always in
  the past. It now marks the end of the day: DPC states that the bulletin
  covers "fino alle 24.00 del giorno di emissione (oggi) e nelle 24 ore del
  giorno seguente (domani)" ([#90]).
- Today and tomorrow change at midnight in Italian time, instead of the time
  zone of the host ([#90]).
- Config entries of version 1 could not be migrated ([#90]).
- The integration imported `async_timeout`, which recent Home Assistant
  versions do not install ([#90]).
- Deprecation warning of the `CONNECTION_CLASS` constant ([#85]).

## [2026.2.0] - 2026-02-01

Stability, validation and automatic releases.

### Added

- A GitHub workflow packages each release and writes its version in
  `manifest.json` and `version.py`.
- The device shows the version of the integration.
- The location is validated when the integration is added: a location outside
  the DPC alert zones is refused with an error.

### Changed

- The unique ID of an entry is based on its coordinates, so the same location
  cannot be added twice.
- Clearer description of the Municipality option and shorter texts in the UI.
- Documentation and HACS metadata for zip releases.

### Fixed

- Parsing of the DPC data: missing keys and cleanup of the responses.
- Sensor entity classes, with `native_value` as Home Assistant requires.
- A typo in the unique ID of the binary sensors and in the Italian
  translation.

## [2026.1.2] - 2026-01-13

### Fixed

- The options flow failed with an `AttributeError` on newer Home Assistant
  versions, because it assigned the read-only `config_entry` property.

## [2026.1.1] - 2026-01-09

### Changed

- Version number of the integration ([#81]).

## [2026.1.0] - 2026-01-09

### Changed

- README: Radius option (km, default 50) ([#73]).

### Fixed

- Typing of the setup and mapping of the icons ([#71], [#79]).
- Icon of phenomenon 40, rough sea ([#72]).
- Frost descriptions: "ghiaggio" is now "ghiaccio" ([#70], [#71]).

## [2024.7.1] - 2024-07-08

### Fixed

- Platforms are set up with `async_forward_entry_setups`, which replaces the
  deprecated `async_forward_entry_setup`.

## [2024.7.0] - 2024-07-06

### Fixed

- `async_forward_entry_setup` is awaited, as Home Assistant 2024.7 requires.
  Thanks to [micium](https://github.com/micium).

## [2024.5.0] - 2024-05-25

### Fixed

- Replaced `async_add_job`, deprecated and removed in Home Assistant 2025.4.
  Thanks to [micium](https://github.com/micium).

## [2023.10.0] - 2023-10-09

### Fixed

- The ID of the vigilance bulletin was not found, causing "Error fetching dpc
  data: 'vigilance'".

## [2023.5.0] - 2023-05-29

### Fixed

- Error fetching the criticality bulletin ([#56]).
- Longer timeout for slow connections ([#54]).

## [2022.3.0] - 2022-03-22

### Added

- Diagnostics (partial).
- Municipality option: the alert zone is looked up by the name of the
  municipality.
- When part of a bulletin is missing, only that part is requested again later.

## [2022.02.0] - 2022-02-04

### Added

- `publication_date` attribute of the vigilance sensor.
- Lovelace example with a custom templater card.

### Changed

- Requires Home Assistant 2021.12.0 or newer.

### Fixed

- URL of the DPC API ([#46]).

## [2021.12.0] - 2021-12-12

### Changed

- Compatibility with Home Assistant 2021.12.

### Fixed

- Broken link in the README.

## [2021.8.2] - 2021-08-16

First published as 2021.8.1b.

### Changed

- The bulletin IDs are read from the DPC repository on GitHub, and from the
  DPC site when GitHub does not answer. GitHub allows 60 requests per hour
  without authentication, so keep the update interval long enough.

## [2021.8.1] - 2021-08-06

### Fixed

- Base URL of the bulletins ([#40]).

## [2021.8.0] - 2021-08-05

When upgrading from an earlier version, remove the integration and install it
again, otherwise orphan entities may be created.

### Added

- Vigilance sensor, from the weather vigilance bulletin.

### Changed

- Asynchronous web requests, with a longer timeout for slow connections.

## [2021.7.0] - 2021-07-14

The integration is set up from the UI. Remove its YAML configuration, as
described in the README.

### Added

- The `sensor` platform, with the criticality sensor.
- Attributes of the binary sensors: `id`, `publication_date`, `expires`,
  `last_update` and `image_url`.

### Changed

These changes break configurations made for 2021.06.1:

| 2021.06.1 | 2021.7.0 |
| --- | --- |
| YAML configuration | Configuration from the UI |
| Attribute `allerta` | `alert` |
| Attribute `data` | `date` |
| Attribute `rischio` | `risk` |
| Attribute `zona_info` | `zone_name` |

## [2021.06.1] - 2021-06-09

### Added

- `image_url` attribute: preview of the national map of the alerts.

### Changed

- The location is given by its coordinates (latitude and longitude). The ISTAT
  code is no longer required, and still accepted for compatibility.
- Third-party services are no longer used.

### Removed

- Some attributes; see the README.

Known issue: the entities get their data only at the second update.

## [2021.4.0] - 2021-04-29

### Added

- `iot_class` in `manifest.json`.

## [2021.3.1] - 2021-03-28

### Changed

- Longer timeout of the requests, for slow connections.
- Versions follow the format YEAR.MONTH.PATCH.

## [1.2.9] - 2021-02-18

### Added

- Version in `manifest.json`.

## [1.2.8] - 2021-01-11

### Added

- A warning, with the link to report the problem, when the DPC resource does
  not return the requested data ([#22]).

## [1.2.7] - 2020-11-22

### Changed

- feedparser 6.0.2 ([#20]).
- Automation example updated for Home Assistant 0.118.

## [1.2.6] - 2020-10-30

### Changed

- The default branch is `main`, with the assets folder.
- README updated.

### Removed

- The unneeded `dependencies` key of `manifest.json`.

### Fixed

- Debug, warning and error log messages.

## [1.2.5] - 2020-05-25

### Added

- Lovelace and automation examples, DPC brand icons and logos, and the URL of
  today's bulletin in the documentation.

### Fixed

- `No module named 'feedparser'` ([#14]).

## [1.2.4] - 2020-05-21

### Added

- RSS feed, for the link to the warning page in the sensor attributes.

### Removed

- The unavailable status added in 1.2.2.

### Fixed

- Entity class names for Home Assistant 0.110.

## [1.2.3] - 2020-05-11

### Fixed

- A warning missing from the feed was reset on the wrong day, today or
  tomorrow.

## [1.2.2] - 2020-05-10

### Added

- Unavailable status.

## [1.2.1] - 2020-05-02

### Fixed

- Blocking I/O inside the event loop, reported by Home Assistant 0.109.

## [1.1] - 2019-11-23

### Fixed

- `level` attribute.

### Changed

- Documentation updated.

## [1.0] - 2019-11-02

First release: a binary sensor of the DPC meteo-hydro alerts, configured in
YAML for a municipality given by its ISTAT code, for the thunderstorm,
hydraulic and hydrogeological risks of today and tomorrow, at or above a
chosen alert level.

[Unreleased]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2026.2.0...HEAD
[2026.2.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2026.1.2...v2026.2.0
[2026.1.2]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2026.1.1...v2026.1.2
[2026.1.1]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2026.1.0...v2026.1.1
[2026.1.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2024.7.1...v2026.1.0
[2024.7.1]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2024.7.0...v2024.7.1
[2024.7.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2024.5.0...v2024.7.0
[2024.5.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2023.10.0...v2024.5.0
[2023.10.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2023.5.0...v2023.10.0
[2023.5.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2022.3.0...v2023.5.0
[2022.3.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2022.02.0...v2022.3.0
[2022.02.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2021.12.0...v2022.02.0
[2021.12.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/2021.8.2...v2021.12.0
[2021.8.2]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/2021.8.1...2021.8.2
[2021.8.1]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/2021.8.0...2021.8.1
[2021.8.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/2021.7.0...2021.8.0
[2021.7.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/2021.06.1...2021.7.0
[2021.06.1]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/2021.4.0...2021.06.1
[2021.4.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/2021.3.1...2021.4.0
[2021.3.1]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v1.2.9...2021.3.1
[1.2.9]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v1.2.8...v1.2.9
[1.2.8]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v1.2.7...v1.2.8
[1.2.7]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v1.2.6...v1.2.7
[1.2.6]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v1.2.5...v1.2.6
[1.2.5]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v.1.2.4...v1.2.5
[1.2.4]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v1.2.3...v.1.2.4
[1.2.3]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v1.1...v1.2.1
[1.1]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v1.0...v1.1
[1.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/releases/tag/v1.0
[#14]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues/14
[#20]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues/20
[#22]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues/22
[#40]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues/40
[#46]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues/46
[#54]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues/54
[#56]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues/56
[#70]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/pull/70
[#71]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/pull/71
[#72]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/pull/72
[#73]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/pull/73
[#79]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/pull/79
[#81]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/pull/81
[#85]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues/85
[#87]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/pull/87
[#90]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/pull/90
