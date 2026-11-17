# Contributing to DPC Alert

Thank you for helping! DPC Alert brings the alerts of the Italian Civil
Protection Department (DPC) to Home Assistant, and every report, translation
and fix makes it more useful for the people who rely on it.

You don't need to write code to contribute. This guide shows the ways you can
help and what makes a contribution easy to accept.

- [Ways to contribute](#ways-to-contribute)
- [Reporting a problem](#reporting-a-problem)
- [Suggesting an improvement](#suggesting-an-improvement)
- [Translating](#translating)
- [Contributing code](#contributing-code)
- [Pull requests](#pull-requests)

## Ways to contribute

- **Report a problem** you found, with what you expected and what happened.
- **Suggest an improvement**: an entity, a card option, a better text.
- **Improve a translation**, or add a language.
- **Improve the documentation**: the README and its translations are the page
  users see in Home Assistant before installing.
- **Fix a bug or build a feature**, with its tests.
- **Answer questions** of other users in the
  [issues](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues).

Please be kind and patient: this project is maintained by volunteers in their
free time.

## Reporting a problem

Before opening an issue, check the
[Troubleshooting](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert#troubleshooting)
section of the README and the
[open issues](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues):
someone may have found it already.

Then [open an issue](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues/new/choose)
with:

1. **What happened**, and what you expected instead.
2. **How to reproduce it**, step by step.
3. **The versions** of DPC Alert and of Home Assistant (**Settings → About**).
4. **The diagnostics** of the place: on the integration, **⋮ → Download
   diagnostics**. They leave out the coordinates of the place and the positions
   of the phenomena, but they show its municipality and DPC zones: remove them
   if you prefer to keep them private.
5. **A debug log**, if the problem is an error: on the integration, choose
   **Enable debug logging** in the **⋮** menu, reproduce the problem, then
   disable it to download the log.
6. **Screenshots**, for a problem in the dashboard, the cards or a form.

A problem in the data itself, such as a text of a bulletin that DPC Alert
shows wrong, may belong to [aiodpc](https://github.com/webysther/aiodpc), the
library that reads the DPC bulletins. Report it here anyway if you are not
sure: we will move it.

## Suggesting an improvement

[Open an issue](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues/new/choose)
that describes what you want to do and why: the use case matters more than
the solution. For a large change, please discuss it in an issue before writing
code, so that your work fits the project.

## Translating

DPC Alert speaks thirteen languages: English, Italian, French, German,
Spanish, Brazilian Portuguese, Romanian, Albanian, Arabic, Simplified Chinese,
Ukrainian, Bengali and Hindi. The texts live in a few places:

| What | Where |
| --- | --- |
| The forms, options, errors and entity names | `custom_components/dpc/translations/<language>.json`; `strings.json` is the English source, identical to `translations/en.json` |
| The levels, risks, criticalities, precipitation, phenomena and directions | [aiodpc](https://github.com/webysther/aiodpc) (`aiodpc/i18n`), the same words in the library and the integration: change them there, and `python -m scripts.translations` writes them here |
| The dashboard, the cards and their editor | `TEXTS` in `custom_components/dpc/frontend/dpc-dashboard.js` |
| The README | `README.<language>.md`, next to `README.md` |

Some advice:

- Use the words Home Assistant itself uses in your language for its menus and
  buttons, such as **Settings** or **Add dashboard**, so that users find them.
- In Italian, the levels, risks and phenomena are those DPC writes in its
  bulletins.
- A new language needs its file in `translations/`, its texts in `TEXTS`, and
  its language in aiodpc.

## Contributing code

### Set up

You need Python 3.14 (required by the version of Home Assistant the tests
pin) and Node.js for the tests of the dashboard.

```bash
git clone https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert.git
cd Home-Assistant-custom-components-DPC-Alert
python3.14 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt ruff
```

### Run the checks

```bash
ruff format custom_components tests scripts
ruff check custom_components tests scripts
mypy                                       # strict
pytest --cov --cov-report=term-missing     # keep custom_components/dpc at 100%
node --test "tests/frontend/*.test.mjs"    # the dashboard and the cards
```

The continuous integration runs the same checks, plus hassfest and the HACS
validation.

### Try it in Home Assistant

Copy `custom_components/dpc` into the `custom_components` folder of the
configuration of a Home Assistant used for testing, and restart it. After a
change to the dashboard or the cards (`frontend/`), reload the browser page
clearing its cache (Ctrl+F5); after a change to Python, restart Home
Assistant.

### Where things are

- `custom_components/dpc/`: the integration. `config_flow.py` is the setup
  and the options, `bulletins.py` and `coordinator.py` download and read the
  bulletins, and each platform (`sensor.py`, `binary_sensor.py`, `image.py`,
  `geo_location.py`) has its entities.
- `custom_components/dpc/frontend/`: the dashboard strategy and the cards,
  plain JavaScript without a build step, made of the cards of Home Assistant.
- `tests/`: the tests, with the DPC bulletins served from `tests/fixtures`,
  never from the network.

Downloading and parsing the DPC files belongs to
[aiodpc](https://github.com/webysther/aiodpc); this repository holds the Home
Assistant side only. [AGENTS.md](AGENTS.md) describes the conventions in
detail: read it before a larger change.

### Some rules that protect the users

Automations and dashboards depend on what the integration exposes, so:

- Never change the unique ID of an entity, nor the name or the values of an
  attribute. A change users must act on is a breaking change, and goes in the
  changelog with what to do.
- Support every version of Home Assistant from the one in `hacs.json` to the
  latest.
- A new entity has its icon in `icons.json` and its texts in every
  language.

## Pull requests

1. Fork the repository and create a branch from `main`.
2. Make your change, small and focused: one fix or feature per pull request
   is easier to review.
3. Add or update the tests, and run the checks above.
4. Update the documentation the change affects: the README and its
   translations, and `quality_scale.yaml` if a rule of the integration
   quality scale changes.
5. Add an entry for the users under `## [Unreleased]` in
   [CHANGELOG.md](CHANGELOG.md): Breaking changes, Added, Changed or Fixed.
6. Open the pull request against `main` of
   [caiosweet/Home-Assistant-custom-components-DPC-Alert](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert),
   saying what it changes and why, and linking the issue it closes.

Code, comments, documentation and commit messages are in English. Don't
change the version: the maintainers set it when they release.

By contributing, you agree that your contribution is released under the
[MIT License](LICENSE.md) of the project.

Thank you! 🇮🇹
