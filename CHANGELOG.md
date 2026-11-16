# Changelog

All notable changes to DPC Alert. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Since 2021.3.1,
versions follow calendar versioning (YEAR.MONTH.PATCH); earlier versions were
numbered 1.x. Pre-releases are not listed: their changes are in the release
that followed them.

## [Unreleased]

### Added

- **Cards for your own dashboards**, in the card picker as soon as the
  integration is installed, each a single card made of the cards of Home
  Assistant, in the colors of the DPC maps and the language of the user. They
  find the entities of the place even after they are renamed; set the
  `device_id` of the place (the first place without it):
  - `custom:dpc-card`: the alert and the precipitation of each day, with the
    highest alert and precipitation of the place;
  - `custom:dpc-bulletin-card`: the criticality and vigilance bulletins side
    by side: their zones, when they were published, until when they cover;
  - `custom:dpc-map-card`: the map of a day, beside a block for each day with
    a map, which shows its map; `map: vigilance` for the vigilance map rather
    than the criticality map.

  A visual editor chooses the place, whether to show the title and the highest
  alert and precipitation, the days, the data of the bulletins, and one or two
  columns.

### Changed

- The DPC Alert dashboard names the days and the entities in the language of
  each user, as the states, rather than in the language of the system.
- The dashboard shows the zones and the bulletins of a place in the section of
  the place, rather than in a section of their own, and the maps of a day
  right after its criticality, where they no longer leave gaps between them.
- The precipitation is colored in the scale of the alerts, green to red, light
  to very heavy, rather than in the blues and purples of the vigilance map, so
  that a level reads the same whatever it measures; no precipitation in the
  blue of the icons of the theme, rather than in a white that a light theme
  does not show.

### Fixed

- The DPC Alert dashboard of a place that shows the binary sensors of the
  risks without the sensors showed nothing while the risks were off: it shows
  them whether they are on or off. Sections with nothing to show are left out.
- The setup and the options accepted a place that shows nothing, such as no
  day without the sensors, or only the day after tomorrow with only its risks
  or maps: they ask for something the place shows.
- The README: installing and uninstalling with the Marketplace of Home
  Assistant 2026.11, or with HACS before; the diagnostics show the
  municipality and the DPC zones of the place, in the names of its devices
  and entities; the versions of Home Assistant that recreate entity IDs
  (2025.6) and list the risks in the Security dashboard (2025.11).

## [2026.11.1] - 2026-11-16

### Breaking changes

- **The data of the bulletins moved from attributes to entities**, which Home
  Assistant translates and dashboards show without templates. The binary
  sensors of the risks keep only their state; the alert and vigilance sensors
  keep their state and `total_alerts`. Templates and automations that read the
  other attributes use the new entities instead:

  | Before | Now |
  | --- | --- |
  | `state_attr('sensor.<place>_alert', 'today').level` | `states('sensor.dpc_<place>_today_alert')`: green, yellow, orange or red |
  | `level`, `alert`, `risk` of a binary sensor | `states('sensor.dpc_<place>_today_hydraulic_risk_level')`, and so on for each risk and day: green to red |
  | `info` of a binary sensor, `….today.info` | `states('sensor.dpc_<place>_today_criticality')`, e.g. `moderate_hydrogeological` |
  | `events_today`, `events_tomorrow` | the binary sensors of the risks, or the `risks` of `sensor.dpc_<place>_today_alert` |
  | `image_url` of a binary sensor, `….today.image_url` | the `image_url` of `image.dpc_<place>_today_criticality_map` |
  | `state_attr('sensor.<place>_vigilance', 'today').precipitation` | `states('sensor.dpc_<place>_today_precipitation')` |
  | `total_phenomena`, `….today.phenomena` | `sensor.dpc_<place>_today_nearby_phenomena`, and the entities `geo_location.dpc_<place>_today_…` |
  | `expires`, `….today.expires` | `sensor.dpc_<place>_criticality_valid_until`, `sensor.dpc_<place>_vigilance_valid_until` |
  | `zone_name` | `sensor.dpc_<place>_alert_zone`, `sensor.dpc_<place>_vigilance_zone` |
  | `id`, `publication_date`, `link`, `last_update` | `sensor.dpc_<place>_criticality_bulletin`: its state is the publication, with `id`, `link` and `last_check` |
  | `max_level` | the state of the sensor itself |
  | `integration` | `integration_entities('dpc')` |

### Added

- **A device for each day** (Milano · Today, Milano · Tomorrow, Milano ·
  Day after tomorrow), part of the device of the place, with the entities of
  that day, named without the day: **Milano · Today Hydraulic risk**. The setup
  and the options choose them: a new place shows today; the places added
  before show today and tomorrow, as their binary sensors did. Unchecking a day
  removes its device and its entities.
- **Sensors of each day**, translated by Home Assistant, which dashboards show
  without templates: the alert of the day (no alert, yellow, orange or red)
  with the risks at that level in `risks`, the criticality DPC states for the
  zone ("Moderate criticality for hydrogeological risk"), the level of each
  risk, the expected precipitation (none to very heavy), and the number of
  phenomena near the place.
- **Diagnostic sensors of the place**: its alert and vigilance zones, when each
  bulletin was published, and until when each covers.
- The criticality and vigilance maps of today and tomorrow as images
  (`image.dpc_<place>_today_criticality_map` and so on), for a picture card
  instead of an iframe. A map is unavailable while its day has none.
- The weather phenomena within the radius as geolocation entities of the
  source `dpc`, such as `geo_location.dpc_<place>_today_gale_nw`, when the
  options turn them on: the map card shows them with
  `geo_location_sources: [dpc]`. Each is named after its type,
  distance and direction in the language of Home Assistant ("Gale, 12.4 km
  NW"), and its `phenomenon` and `direction` are translated.
- **The DPC Alert dashboard**: in **Settings → Dashboards → Add dashboard**,
  under Community dashboards. It has a tab for each place: its highest alert
  and precipitation; a section for each day, with a banner for each risk at
  or above the warning level, the alert, the criticality, the level of each
  risk, the precipitation, the phenomena on a map, each with the icon of its
  kind, and the maps of the bulletins; and its zones and bulletins. Levels and precipitation have the
  colors of the DPC maps. All with the cards of Home Assistant; what has no
  data, such as the maps of tomorrow after midnight, is hidden. Adding a place
  now ends with a pointer to it.
- Seven languages: Simplified Chinese, Romanian, Arabic, Ukrainian, Albanian,
  Bengali and Hindi, for the setup, the options, the entities and the
  dashboard, with the texts of aiodpc for the levels, risks and phenomena.
- The options can turn off the maps and the phenomena, like the sensors.
  Turning off a kind of entities removes them, instead of leaving them
  unavailable.

### Changed

- **The setup goes step by step**: the place and its municipality; what to
  show, the days and the kinds of entities; and the alerts, the minimum level
  of warning chosen among the named alerts ("Yellow alert", "Orange alert",
  "Red alert"), the radius of the phenomena and the update interval. Each
  field says what it does. **The options are a menu of the same steps**: the
  one chosen saves on its own.
- **The alert and vigilance sensors are named Highest alert and Highest
  precipitation**, what they are: the highest level of the zones of the place
  over the days. Their states are still 1 to 4 and 1 to 5, so automations
  that compare them keep working, and Home Assistant shows them as levels:
  "Orange alert", "Heavy".
- **Entity IDs of new places** start with `dpc_`, then the place, the day and
  the entity, in English whatever the language:
  `binary_sensor.dpc_milano_today_hydraulic_risk`,
  `sensor.dpc_milano_highest_alert`. Existing entities keep their IDs, such
  as `binary_sensor.dpc_milano_idraulico_oggi`; **Recreate entity IDs**, in
  **Settings → Entities** (Home Assistant 2025.6 or newer), now gives them the
  new ones.
- The texts of the levels, risks, criticalities, precipitation, phenomena,
  directions, days and bulletins come from aiodpc, the same in the library
  and in the integration; in Italian, they are those DPC writes.
- The README shows the dashboard and the cards of Home Assistant, instead of
  layouts that needed other cards (card-mod, auto-entities,
  config-template-card, card-templater), and its automation examples use the
  translated states.
- The `attribution` of the entities is the one the CC BY 4.0 license of the
  DPC data asks for: "Dipartimento della Protezione Civile – Presidenza del
  Consiglio dei Ministri".
- Requires aiodpc 0.8.0.

### Fixed

- The diagnostics leave out the distances and directions of the phenomena,
  and the IDs and names that carry them: with their positions, public in the
  bulletins, they located the place.
- The README gives the license of the DPC data as DPC publishes it, CC BY
  4.0, instead of CC BY-SA 4.0.

## [2026.11.0] - 2026-11-15

The DPC data now comes from the [aiodpc](https://pypi.org/project/aiodpc/)
library, entity names follow the language of Home Assistant, and `expires`
marks the end of the day it refers to.

### Breaking changes

- **`expires` is one day later.** It pointed to the start of the day it refers
  to, so it was always in the past; it now marks the end of the day (see
  Fixed). If your templates add a day to compensate, remove it.
- **Dates include their time zone.** `expires` and `publication_date` are in
  Italian time (e.g. `2026-11-16T00:00:00+01:00`), and `last_update` is in the
  Home Assistant time zone. Templates can now compare them with `now()`
  directly; where a date is shown as text, it ends with the offset.
- **Entity names are translated.** The device is named after the location you
  configured (`DPC` instead of `Dipartimento Protezione Civile DPC`), and
  entity names follow the language of Home Assistant: `DPC Rischio idraulico
  oggi` in Italian, `DPC Hydraulic risk today` in English. Notifications that
  use `friendly_name` show the new names; names you set yourself are kept.
- **Home Assistant 2025.2 or newer is required.** Older versions stay on
  2026.2.0.

Entity IDs, states and the other attributes do not change.

### Added

- Translations of the configuration, the options, and the names of the
  entities and of their attributes: English, Italian and Brazilian Portuguese
  ([#87]), French, German and Spanish ([#90]).
- The integration is named in the language of Home Assistant, such as Civil
  Protection Department in English ([#90]).
- Automated tests with a CI workflow ([#90]).
- The place is picked on a map, which starts at home, or taken from a zone
  such as Home ([#90]).
- The setup shows the DPC alert zone of the place, after which the place is
  named, and asks for its municipality among those of the zone. The options
  ask for it too, also for the places added before ([#90]).
- Each municipality can be added once: two places in it would get the same
  bulletins. Municipalities of the same name far apart, such as Peglio, in
  Lombardy and in the Marche, are different ones ([#90]).
- The errors of the setup are translated, and the device links to the page
  of the DPC bulletin.
- The integration follows the Home Assistant integration quality scale up to
  platinum; `quality_scale.yaml` gives the status of each rule.

### Changed

- The DPC bulletins are read with aiodpc instead of the integration's own
  client ([#90]).
- The places share the downloads: each bulletin is downloaded once for all of
  them, instead of about 18 MB for each place, and read outside the event
  loop ([#90]).
- When DPC cannot be reached at startup, Home Assistant retries the setup
  within seconds, instead of adding the place with unavailable entities for 10
  minutes. A place outside every DPC alert zone fails to set up, with an
  error ([#90]).
- Entities are unavailable, instead of empty, while their bulletin has never
  been fetched ([#90]).
- The radius option cannot be negative ([#90]).
- The icons of the alert and vigilance sensors come from icon translations:
  they show a warning from level 2 (yellow) up, whatever the warning level of
  the options.
- The device of a place is named after its municipality, or after its entry
  when it has none, so that renaming the entry renames it. The entities of new
  places get IDs from their municipality, like `sensor.dpc_milano_alert`
  and `binary_sensor.dpc_milano_idraulico_oggi`; binary sensors no longer get
  IDs from the coordinates. Existing entities keep their IDs ([#90]).
- HACS lists the integration as "DPC Alert (Protezione Civile)", and Home
  Assistant lists it under Weather & alerts, as a public warnings service
  ([#90]).

### Fixed

- `expires` pointed to the start of the day it refers to, so it was always in
  the past. It now marks the end of the day: DPC states that the bulletin
  covers "fino alle 24.00 del giorno di emissione (oggi) e nelle 24 ore del
  giorno seguente (domani)" ([#90]).
- Today and tomorrow change at midnight in Italian time, instead of the time
  zone of the host ([#90]).
- Config entries of version 1 could not be migrated ([#90]).
- The municipality option finds the municipalities of South Tyrol by their
  Italian or German name ("Bolzano" or "Bozen"); before, it used the
  coordinates instead ([#90]).
- A municipality with the name of another one far away got the highest alert
  of both: Peglio, in Lombardy, showed the alerts of the Peglio of the Marche.
  Only the alert zones near the place count now ([#90]).
- The integration imported `async_timeout`, which recent Home Assistant
  versions do not install ([#90]).
- Deprecation warning of the `CONNECTION_CLASS` constant ([#85]).
- The diagnostics revealed where a place is: the positions of the weather
  phenomena near it, with their distance and direction, and the entity IDs
  made of its coordinates are now redacted ([#90]).

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

### Breaking changes

| 2021.06.1 | 2021.7.0 |
| --- | --- |
| YAML configuration | Configuration from the UI |
| Attribute `allerta` | `alert` |
| Attribute `data` | `date` |
| Attribute `rischio` | `risk` |
| Attribute `zona_info` | `zone_name` |

### Added

- The `sensor` platform, with the criticality sensor.
- Attributes of the binary sensors: `id`, `publication_date`, `expires`,
  `last_update` and `image_url`.

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

[Unreleased]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2026.11.1...HEAD
[2026.11.1]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2026.11.0...v2026.11.1
[2026.11.0]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/compare/v2026.2.0...v2026.11.0
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
