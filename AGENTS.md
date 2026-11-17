# AGENTS.md: DPC Alert

Guidance for AI coding agents and contributors working on this repository.
`CLAUDE.md` imports this file.

DPC Alert is a Home Assistant custom integration (domain `dpc`), installed
through HACS. It turns the bulletins of the Italian Civil Protection Department
(DPC) into entities for places in Italy:

- the criticality bulletin (hydraulic, hydrogeological and thunderstorm risk,
  today and tomorrow): `sensor.<place>_alert` and one binary sensor per risk
  and day;
- the vigilance bulletin (precipitation and weather phenomena, three days):
  `sensor.<place>_vigilance`;
- for dashboards, translated without templates: a sensor of the alert or the
  precipitation of each day, the maps of the bulletins (`image`), and the
  phenomena within the radius (`geo_location`, source `dpc`);
- the DPC Alert dashboard, a strategy listed under Community dashboards;
- the DPC Alert cards, in the card picker with a visual editor: the alert and
  the precipitation of each day (`custom:dpc-card`), the bulletins
  (`custom:dpc-bulletin-card`) and the maps (`custom:dpc-map-card`).

Everything that talks to DPC or parses its files lives in
[aiodpc](https://github.com/webysther/aiodpc) (PyPI `aiodpc`), maintained
alongside this repository. This repository holds the Home Assistant side only.

## Ground rules

- **Do not commit, amend, push, tag, release or move branches** (`reset`,
  `branch -f`, `rebase`). Leave every change uncommitted in the working tree;
  the maintainer reviews and commits it. Read-only git commands are fine. When
  work has to be split across branches or PRs, stop and ask.
- Ask before anything that leaves the machine: releases, opening or editing
  PRs and issues, comments.
- Reply in the language the person writes in. Code, comments, docstrings,
  docs, the changelog and commit messages are in English.
- Check instead of guessing. For Home Assistant behaviour, read its source in
  the test environment (`site-packages/homeassistant`). For DPC data
  questions, measure the live data with a throwaway script outside the
  repository.
- DPC parsing and HTTP fixes belong in aiodpc. Here, only Home Assistant code.

## Layout

```text
custom_components/dpc/
  __init__.py        setup, unload, migration of config entries (to version 2.2)
  config_flow.py     menu (map or zone), DPC alert zone, municipality, what to
                     show, alerts; the options are a menu of the same steps
  bulletins.py       one download of each bulletin for all places, read at each
                     place in an executor
  coordinator.py     DpcDataUpdateCoordinator, one per place (entry.runtime_data)
  entity.py          DpcEntity, the devices of the place and of its days,
                     place_entity_id()
  sensor.py          the place (highest alert and precipitation, zones,
                     bulletins) and each day (alert, criticality, risk levels,
                     precipitation, nearby phenomena)
  binary_sensor.py, image.py, geo_location.py
  dashboard.py       serves frontend/ and has the frontend load its modules
  frontend/          the dashboard strategy (dpc-dashboard.js) and the cards
                     (dpc-card.js): plain JavaScript, no build, native cards only
  diagnostics.py     redacts everything that locates a place
  const.py, icons.json, strings.json, translations/, quality_scale.yaml
  manifest.json, version.py
tests/               pytest-homeassistant-custom-component, DPC mocked with fixtures
tests/frontend/      node:test tests of the dashboard strategy and the cards
scripts/translations.py  writes the texts of aiodpc into the translations
release.sh           releases, run by the maintainer
CONTRIBUTING.md      the guide for contributors: keep its checks and rules in
                     step with this file
```

## Checks

Python 3.14, as required by the pinned `pytest-homeassistant-custom-component`
(which also pins the Home Assistant version of the tests):

```bash
python3.14 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt ruff
ruff format custom_components tests scripts
ruff check custom_components tests scripts
mypy                                   # strict, configured in pyproject.toml
pytest --cov --cov-report=term-missing
node --test "tests/frontend/*.test.mjs"   # the dashboard strategy and the cards
npx prettier --check .                    # the JavaScript and the YAML
```

The dotfiles say how each file is written: `.editorconfig` (LF, UTF-8,
indentation, the JSON with 4 spaces or tabs), `.prettierrc` (Prettier for the
JavaScript and the YAML, `printWidth` 100; `.prettierignore` leaves out the
Markdown and the JSON), `.gitattributes` (LF) and `.python-version` (3.14).

CI runs mypy, pytest and the tests of the frontend (`tests.yaml`),
hassfest and the HACS action (`validate.yaml`). Keep the coverage of `custom_components/dpc` at 100%.

## Compatibility

Users' automations and dashboards depend on what the integration exposes.

- Never change unique IDs: entries are `"{lat:.6f}_{lon:.6f}"`; the highest
  alert and precipitation keep `"{name}_criticality_{lat}_{lon}"` and the
  vigilance equivalent; binary sensors `"{entry.unique_id}-{key}"` with their
  Italian keys (`idraulico_oggi`). New entities of the place are
  `"{entry.unique_id}-{key}"`, of a day `"{entry.unique_id}-{key}_{day}"`,
  and phenomena `"{entry.unique_id}-{day}-{phenomenon.key}"`.
- Never rename attributes or change their values. A change that users must
  act on goes under "Breaking changes" in the changelog, with what to do.
- Entities suggest their ID with `DpcEntity.suggest_entity_id()`:
  `<platform>.dpc_<place>[_<day>]_<key>` (`place_entity_id()`), with the
  translation key as `<key>`, so IDs are English whatever the language
  (`binary_sensor.dpc_torino_today_hydraulic_risk`). Home Assistant keeps
  the IDs of existing entities in its registry (such as
  `binary_sensor.dpc_torino_idraulico_oggi`, from before), adds `_2` to a
  repeated ID, and **Recreate entity IDs** gives users the suggested one.
- A place is a device; each day it shows is a device linked to it
  (`via_device_id` from Home Assistant 2026.8, `via_device` before; see
  `VIA_DEVICE_ID_VERSION`), identified by `"{entry.unique_id}-{day}"`.
- Changing the shape of config entry data or options needs a step in
  `async_migrate_entry`. A change that older versions can still load bumps
  `ConfigFlow.MINOR_VERSION` (the days of a place, 2.2); only one they cannot
  bumps `VERSION`: since Home Assistant 2026.7, an entry of a higher major
  version fails to load, so going back to an older release would break it.
- Supported Home Assistant: from the `homeassistant` version in `hacs.json`
  (2025.2.0) to the latest. Use APIs available in that whole range, or import
  both ways with a comment, like the validation library:
  `try: import probatio as vol` / `except ImportError: import voluptuous as vol`
  (Home Assistant 2026.9 and newer validate with probatio).

## How a place works

- A place is identified by its coordinates (the entry unique ID). The setup
  shows its DPC alert zone, which names the entry, and asks for its
  municipality among those of the zone, as DPC lists them. The municipality
  is required and names the device.
- Each municipality can be added once, whatever name is typed ("Bozen" is
  "Bolzano/Bozen"). Places with the same municipality name more than
  `SAME_MUNICIPALITY_KM` apart are homonyms (Peglio in Lombardy and in the
  Marche) and are both allowed.
- A place shows at least one entity: the setup and the options check the days
  and the kinds of entities chosen (`shows_entities` in `const.py`). Without
  days, only the sensors of the place give it entities.
- Every scan interval (30 minutes by default) only the IDs of the latest
  bulletins are checked; a new bulletin (about 18 MB) is downloaded once for
  all places. Never block the event loop: reading a bulletin at each place
  runs in an executor.
- The maps of the days are downloaded once for all places too
  (`DpcBulletins.preview`, with `DpcClient.get_preview`). DPC often publishes
  them blank: a map entity is unavailable until its map is downloaded and not
  blank, and tries again at every update of its place.

## Home Assistant conventions

- `strings.json` is the source of the texts and `translations/en.json` is
  identical to it. Every key exists in each language of aiodpc, with the tag
  Home Assistant names its file with: en, it, pt-BR, fr, de, es, zh-Hans, ro,
  ar, uk, sq, bn, hi. The top-level `title` is the translated name of the
  integration, and the dashboard and the cards (`TEXTS` in
  `frontend/dpc-dashboard.js`) have the same languages, with that name. A new
  language of aiodpc needs its file here, the risk level template of
  `scripts/translations.py`, and its texts in `TEXTS`.
- Data is an entity, not an attribute: a level, a zone, a bulletin is an
  entity of the place or of its day. Attributes are left for what is not an
  entity of its own (`risks`, `total_alerts`, `image_url`, the `id` of a
  bulletin).
- What DPC gives as a fixed list (levels, risks, criticalities, phenomena,
  directions) is an `enum` state or an attribute value that Home Assistant
  translates: the keys of the aiodpc enums.
- The texts of those values, and the names of what DPC defines (risks, days,
  bulletins, precipitation, phenomena), come only from the data dictionary of
  aiodpc (`aiodpc.i18n`): `scripts/translations.py` writes them and
  `tests/test_translations.py` checks them. Never write them by hand; to
  change a word, change aiodpc. The names only Home Assistant has (Highest
  alert, Alert zone...) are written in `strings.json`, as short as possible.
- Entity names follow the language of Home Assistant; a phenomenon is named
  with the template of aiodpc and its texts in that language.
- Errors shown to users use translation keys: `config.error`,
  `options.error`, `exceptions`.
- Every entity has an icon in `icons.json`; the levels have `state` icons.
  `tests/test_icons.py` checks it.
- The dashboard and the cards color the levels by state with the colors of the
  DPC alert map (`ALERT_COLORS` in `frontend/dpc-dashboard.js`), and the
  precipitation in the same scale, light to very heavy, none in the blue of
  the icons of the theme (`PRECIPITATION_COLORS`). They find the entities by
  translation key and the day of their device, never by entity ID, and name
  them and the days in the language of the user with the texts of the
  integration (`withTexts`): Home Assistant names them in the language of the
  server.
- The cards draw nothing of their own: an `ha-card` with native cards inside,
  created with `loadCardHelpers`, without their own background. Their visual
  editor is an `ha-form`, which the frontend defines only with the editor of
  one of its cards: the cards load the editor of a tile first. The editor
  writes only the options that differ from what a card shows without them.
- The frontend is served at `/dpc/frontend/<version>/` (`FRONTEND_URL`), so
  that browsers load it again after an update, and its modules import each
  other by relative path. A new module goes in `FRONTEND_MODULES`.
- Diagnostics must not reveal where a place is: coordinates, positions,
  distances and directions of phenomena, the entity IDs and names of the
  phenomena (they carry the direction), and entity IDs made of coordinates
  are redacted. `async_redact_data` does not walk tuples: turn them into lists
  first.
- `quality_scale.yaml` states each rule of the integration quality scale (up
  to platinum). Keep it true when a change affects a rule.
- `hacs.json` accepts only the keys HACS knows. The README is the HACS store
  page and holds the sections the quality scale asks for (installation,
  configuration, options, removal, data update, known limitations,
  troubleshooting, use cases, examples): keep them current.
- The README is translated: `README.<language>.md` at the root, with the tag
  Home Assistant names the language with (`README.it.md`, `README.fr.md`,
  `README.es.md`, `README.de.md`), and the same line of language links at the
  top of each. A change to `README.md` changes every translation, in the same
  commit. The translations use the texts of the integration in their language
  (`translations/<language>.json`) for what it shows, and keep the entity IDs,
  YAML, URLs and images of `README.md`. The Marketplace shows `README.md`;
  [home-assistant/core#189842](https://github.com/home-assistant/core/pull/189842)
  would show the translation of the language of the user, by these names.
- Images of the README are in `assets/images/`, linked with absolute
  `raw.githubusercontent.com` URLs: the Marketplace and HACS show the README
  outside GitHub, where relative paths break. The screenshots show Torino.

## Tests

- Never reach the network: serve the fixtures with `aioclient_mock` (the
  first matching route wins, so register a failing route first) or patch
  `DpcClient` methods.
- Never depend on the clock: freeze it (`freezer`). Bulletin days end at
  midnight in Europe/Rome.

## aiodpc

The version is pinned exactly in `custom_components/dpc/manifest.json`
(`requirements`) and in `requirements_test.txt`. Bump both together, and only
once the release is on PyPI: check `https://pypi.org/simple/aiodpc/`, as the
JSON API stays cached for a while. Then write its texts into the translations:
`python -m scripts.translations`.

## Changelog and releases

- `CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
  Add entries under `## [Unreleased]` (Breaking changes, Added, Changed,
  Fixed), written for the users of the integration, with the PR reference,
  e.g. `([#90])`, and its link at the end of the file. PR descriptions link to
  the changelog instead of listing the changes.
- Versions are CalVer, `YEAR.MONTH.PATCH`. A beta `YEAR.MONTH.PATCHbN` is a
  GitHub pre-release, which HACS offers to those who turn on betas.
- The maintainer releases with `./release.sh VERSION [--dry-run]`. The version
  lives in the git tag only: leave `"version": "0.0.0"` in `manifest.json` and
  `"develop"` in `version.py`; the release workflow writes them and attaches
  `dpc.zip`, the file HACS installs.
- `origin` is the maintainer's fork; pull requests go from its branches to
  `main` of `caiosweet/Home-Assistant-custom-components-DPC-Alert`.

## Code style

- Readable, descriptive code over clever code: descriptive names, typed models
  and enums instead of raw dicts, small focused helpers, docstrings that say
  what and why.
- No magic numbers: a `Final` constant whose docstring says where its value
  comes from (see `SAME_MUNICIPALITY_KM`).
- mypy strict. A `# type: ignore[code]` needs a comment saying why.
- Comments explain why, not what.
