# DPC Alert (Protezione Civile)

<img src="https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/blob/main/assets/brand/icon.png" width="150px">

The alerts of the Italian Civil Protection Department (Dipartimento della Protezione Civile, DPC) in Home Assistant, for any place in Italy: the hydraulic, hydrogeological and thunderstorm risk of today and tomorrow, and the weather vigilance of the next three days with the phenomena near you.

How the alert system works: [_Civil Protection Department_](https://rischi.protezionecivile.gov.it/en/meteo-hydro/alert) · [_Dipartimento Protezione Civile_](https://rischi.protezionecivile.gov.it/it/meteo-idro/allertamento)

[![hacs][hacsbadge]][hacs] [![Validate](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/actions/workflows/validate.yaml/badge.svg)](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/actions/workflows/validate.yaml)

[![GitHub latest release]][githubrelease] ![GitHub Release Date] [![Maintenancebadge]][maintenance] [![GitHub issuesbadge]][github issues]

[![Websitebadge]][website] [![Forum][forumbadge]][forum] [![telegrambadge]][telegram] [![facebookbadge]][facebook]

[![Don't buy me a coffee](https://img.shields.io/static/v1.svg?label=Don't%20buy%20me%20a%20coffee&message=🔔&color=black&logo=buy%20me%20a%20coffee&logoColor=white&labelColor=6f4e37)](https://paypal.me/hassiohelp)

---

## Features

- **A device for each day**: Milano · Today, Milano · Tomorrow and Milano · Day after tomorrow, part of the device of the place. The setup and the options choose the days.
- **Each day**: the alert (no alert, yellow, orange or red) with the risks at that level; the criticality DPC states for the zone, such as "Moderate criticality for hydrogeological risk"; the level of the hydraulic, hydrogeological and thunderstorm risk, and a binary sensor of each, on when it reaches the alert level you choose; the expected precipitation; and the weather phenomena within the radius you choose, on a map, once the options turn them on. The criticality bulletin covers today and tomorrow, the vigilance bulletin the day after too.
- **The place**: its highest alert and highest precipitation, its DPC zones and its bulletins.
- **Maps** of the criticality and vigilance bulletins, today and tomorrow, as images.
- **A dashboard** of every place, made of the cards of Home Assistant, in the colors of the DPC alerts: see [Dashboard](#dashboard).
- **Three cards** for your own dashboards, with a visual editor: the alert and the precipitation of each day, the bulletins, and the maps: see [Cards](#cards).
- **Several places**, picked on a map or from a zone, each with its municipality. Each bulletin is downloaded once for all of them.
- **Thirteen languages**: English, Italian, French, German, Spanish and Brazilian Portuguese, and those of some of the largest foreign communities in Italy: Romanian, Albanian, Arabic, Simplified Chinese, Ukrainian, Bengali and Hindi. The texts of the levels, risks, phenomena and directions are those of the [aiodpc](https://github.com/webysther/aiodpc) library; in Italian, the levels, risks and phenomena are those DPC writes.
- **Official data**: the criticality and weather vigilance bulletins that DPC publishes every day.

Requires Home Assistant 2025.2 or newer. See the [changelog](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/blob/main/CHANGELOG.md) for what changed in each version.

## Use cases

- Get a notification when DPC issues a yellow, orange or red alert for your place, today or tomorrow, with the risk and its level.
- See the alerts of each day, the expected precipitation and the maps of the bulletins on the DPC Alert dashboard, or on your own with the DPC Alert cards or the cards of Home Assistant.
- See the weather phenomena near your places on a map.
- Announce the alerts of the day on a speaker in the morning.
- Close the shutters or bring in the garden furniture when strong wind or thunderstorms are expected nearby, from the weather phenomena near the place.
- Before a trip, add the place you are going to and follow its alerts.

## Installation

DPC Alert is in the community catalog, which both the Marketplace of Home Assistant and HACS install from.

### With the Marketplace (Home Assistant 2026.11 or newer)

1. Go to **Settings → Marketplace** and search for `DPC Alert`.
2. Open **DPC Alert (Protezione Civile)** and choose **Install**.
3. Restart Home Assistant.

### With [HACS](https://hacs.xyz/) (Home Assistant 2025.2 to 2026.10)

1. Open **HACS** in the Home Assistant menu and search for `DPC Alert`.
2. Open **DPC Alert (Protezione Civile)** and choose **Download**.
3. Restart Home Assistant.

## Configuration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=dpc)

1. In Home Assistant, go to **Settings → Devices & services → Add integration** and search for `Dpc`, or use the button above.
2. Choose how to give the place to monitor:
   - **Pick it on a map**: the map starts at your home; move the pin.
   - **Use a zone**, such as Home.
3. The integration checks the place with DPC and shows its alert zone. Choose its **municipality** among those of the zone: a municipality that spans several alert zones gets the highest alert of all of them.
4. **What to show**: the days (today by default) and the kinds of entities (all but the phenomena by default).
5. **Alerts**: the minimum level of warning, the radius of the phenomena and the update interval. Each field says what it does, and the options change them later.

Add as many places as you want, each with its own municipality: two places in the same municipality would get the same bulletins. The places share the downloads: each bulletin is downloaded once for all of them.

A place is named after its alert zone, and its device after its municipality: for a place in Milan, the device is Milano, and the device of today is Milano · Today. A new place shows today, unless you choose other days. The entity IDs start with `dpc_`, then the place, the day and the entity, in English whatever the language: `sensor.dpc_milano_highest_alert`, `binary_sensor.dpc_milano_today_hydraulic_risk`. See [Entities](#entities) for all of them.

### Options

**Configure** on the integration opens a menu of the steps of the setup: choose the one to change, which saves on its own.

1. **Municipality**: among those of the alert zone of the place; while DPC cannot be reached, any name can be typed.
2. **What to show**:
   - **Days**: today, tomorrow and the day after tomorrow, each a device with its entities. Unchecking a day removes its device and entities; the place keeps its highest alert and precipitation and its bulletins.
   - **Entities**: the binary sensors of the risks, the sensors, the maps, and the phenomena on the map (off by default). Unchecking a kind removes its entities from the place and from every day. The place has to show something: without days, only the sensors give it entities, and the day after tomorrow has no risks nor maps.
3. **Alerts**:
   - **Minimum level of warning**: yellow (default), orange or red alert. The binary sensor of each risk turns on from this level up.
   - **Radius of the phenomena** (km, default 50).
   - **Update interval** (minutes, default 30).

### Removal

1. Go to **Settings → Devices & services** and open **Civil Protection Department**, as Home Assistant names the integration in English (Dipartimento Protezione Civile in Italian).
2. For each place, open its **⋮** menu and choose **Delete**.
3. To uninstall the integration too, open **DPC Alert (Protezione Civile)** in **Settings → Marketplace** and choose **Uninstall**; before Home Assistant 2026.11, open it in **HACS** and choose **Remove** in its **⋮** menu. Then restart Home Assistant.

## Dashboard

The integration comes with a dashboard made of the cards of Home Assistant, in the language of each user, with the names of the days and of the entities; only the names of the phenomena follow the language of the system (see [Troubleshooting](#troubleshooting)):

1. Go to **Settings → Dashboards → Add dashboard**.
2. Under **Community dashboards**, choose **DPC Alert**. If it is not listed, reload the page.

It has a tab for each place, with the levels in the colors of the DPC alert map, green to red, and the precipitation in the same scale, light to very heavy (none in the blue of the icons of the theme):

- **The place**: its highest alert and highest precipitation, its zones, when each bulletin was published and until when it covers.
- **Each day** it shows: a banner for each risk at or above the warning level, in the color of its level (without the sensors, a tile of each risk, on or off); the alert, with the risks at that level; the criticality; the maps of the bulletins; the phenomena of the day on a map; the level of each risk; the expected precipitation and the number of phenomena.

The dashboard follows your places: it changes by itself when you add one, check or uncheck a day, and when a bulletin brings other phenomena. The alert, the criticality, the levels, the precipitation and the maps of a day are hidden while they have no data, such as tomorrow's after midnight, until DPC publishes the next bulletin. The colored banners of the risks need Home Assistant 2026.9 or newer; before, the risks are shown as tiles.

To show a place in another dashboard, add a view with the strategy of the dashboard and the ID of the device of the place, the end of the address of its device page:

```yaml
views:
  - title: Milano
    strategy:
      type: custom:dpc-alert
      device_id: 0123456789abcdef0123456789abcdef
```

The binary sensors of the risks are safety sensors: the **Security** dashboard of Home Assistant (2025.11 or newer) lists them too.

## Cards

The integration comes with three cards for your own dashboards, in the card picker as soon as it is installed: search for **DPC Alert**. Each is a single card made of the cards of Home Assistant, in the colors of the DPC alerts and in the language of each user, and finds the entities of the place even after you rename them.

- **DPC Alert** (`custom:dpc-card`): the highest alert and precipitation of the place, then the alert and the precipitation of each day; the day after tomorrow has its precipitation only.
- **DPC Alert · Bulletins** (`custom:dpc-bulletin-card`): the criticality bulletin and, beside it, the vigilance bulletin: their zones, when they were published and until when they cover.
- **DPC Alert · Maps** (`custom:dpc-map-card`): the map of a day and, beside it, a list as high as the map: a block for each day with a map, the zone of the map and the number of phenomena near the place. With two days, a click on a block shows its map.

The visual editor chooses what each card shows. In YAML, an option left out shows everything:

| Option | Cards | Without it |
| --- | --- | --- |
| `device_id` | all | The first place. The ID of the device of the place, the end of the address of its device page. |
| `show_title: false` | all | The name of the place, above the rest. Without it, the highest levels move to the start. |
| `show_highest_alert: false` | DPC Alert, Maps (criticality) | The highest alert of the place, beside its name. |
| `show_highest_precipitation: false` | DPC Alert, Maps (vigilance) | The highest precipitation of the place, beside its name. |
| `days` | DPC Alert, Maps | All the days of the place: `today`, `tomorrow`, `aftertomorrow`; the maps, today and tomorrow. |
| `items` | Bulletins | All six: `alert_zone`, `criticality_bulletin`, `criticality_valid_until`, `vigilance_zone`, `vigilance_bulletin`, `vigilance_valid_until`. |
| `columns: 1` | DPC Alert, Bulletins | Two columns: the alert beside the precipitation, the criticality bulletin beside the vigilance bulletin. |
| `map: vigilance` | Maps | The criticality map. |
| `show_zone: false` | Maps | The zone of the map, beside it. |
| `show_nearby_phenomena: false` | Maps | The number of phenomena near the place on the day of the map, beside it. |

```yaml
# The vigilance map of today, without the name of the place
type: custom:dpc-map-card
device_id: 0123456789abcdef0123456789abcdef
map: vigilance
show_title: false
days:
  - today
```

### With the cards of Home Assistant

The entities fit the cards of Home Assistant without templates. For a place in Milan:

```yaml
# The alert of tomorrow and the risks at its level: "Orange alert · Hydrogeological risk"
type: tile
entity: sensor.dpc_milano_tomorrow_alert
state_content:
  - state
  - risks
```

```yaml
# The same tile in the orange of the DPC map, while the alert is orange; add one
# for each level: green #90c985, yellow #f8f865, orange #f0bf01, red #fd6767
type: tile
entity: sensor.dpc_milano_tomorrow_alert
color: "#f0bf01"
visibility:
  - condition: state
    entity: sensor.dpc_milano_tomorrow_alert
    state: orange
```

```yaml
# A banner while the hydrogeological risk of tomorrow is at or above the warning
# level and orange (Home Assistant 2026.9 or newer)
type: alert
entity: binary_sensor.dpc_milano_tomorrow_hydrogeological_risk
alert_color: "#f0bf01"
visibility:
  - condition: state
    entity: binary_sensor.dpc_milano_tomorrow_hydrogeological_risk
    state: "on"
  - condition: state
    entity: sensor.dpc_milano_tomorrow_hydrogeological_risk_level
    state: orange
```

```yaml
# The criticality map of today
type: picture-entity
entity: image.dpc_milano_today_criticality_map
show_state: false
```

```yaml
# The weather phenomena near all your places
type: map
geo_location_sources:
  - dpc
```

## How the data is updated

- DPC publishes the criticality bulletin every day by 16:00 (Italian time), sometimes updated later the same day, and the weather vigilance bulletin by 15:00.
- Every 30 minutes (the **Update interval** option), each place checks whether DPC has published new bulletins. The places that update at the same time share the check.
- A new bulletin is downloaded once for all the places and read at each place: about 11 MB for a criticality bulletin, 8 MB for a vigilance bulletin.
- The maps of the days are downloaded with the bulletin, once for all the places, about 100 kB each. DPC often publishes a map blank and sometimes replaces it later at the same address: a blank map is not shown, and it is downloaded again at every update until DPC publishes the map.
- Today and tomorrow follow the Italian date: after midnight, the second day of the bulletin becomes today, until DPC publishes the next bulletin.
- When DPC cannot be reached, the places keep their bulletins, whose days stay valid, and check again after 10 minutes, or sooner with a shorter update interval.

## Known limitations

- DPC covers Italy only. San Marino and Vatican City are in no DPC alert zone.
- DPC often publishes the map of a day blank: from August to November 2026, 40% of the criticality maps and 5% of the vigilance maps, and it replaced only about a third of them later. The map is then unavailable, and the dashboards leave it out, sometimes for the whole day.
- The criticality bulletin covers today and tomorrow; the vigilance bulletin, three days. The highest alert of a place is of today and tomorrow, even when it shows only today.
- Each municipality can be added once: two places in it would get the same bulletins. Municipalities of the same name far apart, such as Peglio, in Lombardy and in the Marche, are different ones: the entity IDs of the second end in `_2`, e.g. `sensor.dpc_peglio_highest_alert_2`.
- The texts of the levels, risks, criticalities, phenomena and directions come from the aiodpc library; in Italian, the levels, risks, criticalities and phenomena are those DPC writes, while the directions are computed by aiodpc. Places, zones and municipalities keep the names DPC gives them, in Italian; in South Tyrol, the German names of the municipalities work too.
- In templates and notifications, `state_translated()` gives the translated state; `state_attr_translated()` (Home Assistant 2026.4 or newer) a translated attribute, such as the `phenomenon` of a phenomenon. Lists, such as the `risks` of the alert of a day, are translated by the dashboards only.

## Troubleshooting

- **The integration shows "Retrying setup"**: DPC cannot be reached. Home Assistant retries on its own; check that it can reach `mappe.protezionecivile.gov.it` and `raw.githubusercontent.com`.
- **"… is not inside any DPC alert zone"**: the place is outside Italy, or in San Marino or Vatican City. Delete it and add a place in Italy.
- **The entities of a day are missing**: check the **Days** option of the place. The places added before this version show today and tomorrow.
- **An automation reads an attribute that is gone**, such as `level`, `info`, `zone_name` or `expires`: the data of the bulletins became entities. The [changelog](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/blob/main/CHANGELOG.md) lists where each attribute is now.
- **After an update, texts in English or names such as `municipality_in_use` in the forms**: Home Assistant and the browser keep the texts of the previous version. Restart Home Assistant, then reload the page, clearing its cache (Ctrl+F5).
- **Entity and device names in another language**: Home Assistant names entities and devices in the language of the system, not of your profile: **Settings → System → General → Language**. So are the names of the phenomena. The states and the translated values of the attributes follow your profile, and so do the names in the DPC Alert dashboard and cards.
- **Entity IDs such as `binary_sensor.dpc_milano_idraulico_oggi`**: the entities of places added with an earlier version keep their IDs, so that automations keep working. To give them the IDs of new places, such as `binary_sensor.dpc_milano_today_hydraulic_risk` (Home Assistant 2025.6 or newer): on the page of each device, choose **⋮ → Recreate entity IDs**, or select the entities in **Settings → Entities** and choose **Recreate entity IDs of selected**. Then update the automations and dashboards that use them. The same gives the new IDs after you rename a place.
- **DPC Alert is not among the community dashboards, or its cards are not in the card picker**: the browser loads them when it opens Home Assistant. Reload the page after installing or updating the integration.
- **A place added before 2026.11 has no municipality**: it uses the alert zone of its coordinates, and its device is named after its entry. Choose its municipality in its options, under **Municipality**, among those of its alert zone.
- **Reporting a problem**: on the integration, choose **Enable debug logging** in the **⋮** menu, reproduce the problem, then disable it to download the log. Add the diagnostics (**⋮ → Download diagnostics**) to an [issue](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues). They leave out the coordinates of the place and the positions, distances and directions of the phenomena, but not the municipality and the DPC zones of the place, which the names of its devices and entities show: remove them from the file before posting it if you prefer to keep them private.

## Entities

For a place in Milan, with Home Assistant in English. The device of the place, **Milano**:

| Entity | State |
| --- | --- |
| `sensor.dpc_milano_highest_alert` | The highest alert level of today and tomorrow: 1 (no alert) to 4 (red), shown as the alert, such as "Orange alert" |
| `sensor.dpc_milano_highest_precipitation` | The highest expected precipitation of the next three days: 1 (none) to 5 (very heavy), shown as the precipitation |
| `sensor.dpc_milano_alert_zone`, `…_vigilance_zone` | The DPC zones of the place, for its diagnostics |
| `sensor.dpc_milano_criticality_bulletin`, `…_vigilance_bulletin` | When the latest bulletin was published, for its diagnostics: the time of the criticality bulletin; the day of the vigilance bulletin, at midnight |
| `sensor.dpc_milano_criticality_valid_until`, `…_vigilance_valid_until` | The end of the last day the bulletin covers, for its diagnostics |

The devices of the days, **Milano · Today** and **Milano · Tomorrow** (`today` and `tomorrow` in the IDs):

| Entity | State |
| --- | --- |
| `sensor.dpc_milano_today_alert` | The alert of the day: no alert, yellow, orange or red |
| `sensor.dpc_milano_today_criticality` | The criticality DPC states for the zone, and the risk its map shows: "Moderate criticality for hydrogeological risk" (`moderate_hydrogeological`), or "No significant phenomena expected" (`absent`) |
| `binary_sensor.dpc_milano_today_hydraulic_risk`, `…_thunderstorm_risk`, `…_hydrogeological_risk` | On when the risk reaches the minimum level of warning of the options |
| `sensor.dpc_milano_today_hydraulic_risk_level`, `…_thunderstorm_risk_level`, `…_hydrogeological_risk_level` | The level of the risk: no alert, yellow, orange or red |
| `sensor.dpc_milano_today_precipitation` | The expected precipitation of the day: none to very heavy |
| `sensor.dpc_milano_today_nearby_phenomena` | The number of weather phenomena within the radius |
| `image.dpc_milano_today_criticality_map`, `…_vigilance_map` | The national map of the bulletin, as DPC previews it; unavailable while DPC publishes it blank |
| `geo_location.dpc_milano_today_gale_nw` and so on | A weather phenomenon within the radius, once the options turn the phenomena on, named after its type, distance and direction ("Gale, 12.4 km NW"): its distance, in km |

The device of the day after tomorrow, **Milano · Day after tomorrow** (`after_tomorrow` in the IDs), has the precipitation, the number of phenomena and the phenomena: the criticality bulletin covers two days.

The alert and the levels of a day are those of the bulletin, whatever the minimum level of warning of the options. After midnight, until DPC publishes the next bulletins, the alert, the criticality, the risks and their levels of tomorrow are unknown, and its maps unavailable; the precipitation and the number of phenomena of the day after tomorrow are unknown, and its phenomena removed.

Home Assistant translates the states, and the values of the attributes in the dashboards. Templates and automations see the values below; every entity also has the `attribution` of the DPC data.

<details>
<summary>Attributes</summary>

```yaml
# sensor.dpc_milano_tomorrow_alert
state: orange # green (no alert), yellow, orange or red
risks: # the risks at that level, none when green
  - hydrogeological # hydraulic, thunderstorms or hydrogeological
```

```yaml
# sensor.dpc_milano_highest_alert, and the same for the highest precipitation
state: 3
total_alerts: 3 # the risks (the days, for the precipitation) at or above the minimum level of warning
```

```yaml
# sensor.dpc_milano_criticality_bulletin, and the same for the vigilance bulletin
state: '2026-11-14T13:30:00+00:00' # when it was published
id: '20261114_1430'
link: https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-criticita/
last_check: '2026-11-14T15:00:00+01:00' # when DPC last confirmed it is the latest
```

```yaml
# image.dpc_milano_today_criticality_map
image_url: https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/files/preview/20261114_1430_oggi.png
```

```yaml
# geo_location.dpc_milano_tomorrow_light_snow_nne
state: 44.3 # the distance from the place, in km
source: dpc
latitude: 45.83
longitude: 9.41
phenomenon: light_snow # shown as "Light or moderate snowfall"
direction: nne # from the place, shown as "NNE"
```

Weather phenomena come and go with the bulletins, each on the device of its day.

</details>

## Automation examples

The examples use Milan: replace `milano` with the place in the entity IDs of yours, and `notify.mobile_app_your_phone` with your notification. Paste an example into the YAML editor of a new automation. The messages are in the language of Home Assistant.

<details>
<summary>Notify the alert of today or tomorrow</summary>

```yaml
alias: DPC alert
triggers:
  - trigger: state
    entity_id:
      - sensor.dpc_milano_today_alert
      - sensor.dpc_milano_tomorrow_alert
    to:
      - yellow
      - orange
      - red
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "{{ state_attr(trigger.entity_id, 'friendly_name') }}"
      message: "{{ state_translated(trigger.entity_id) }}"
mode: queued
```

For example *Milano · Tomorrow Alert: Orange alert*, when the alert of a day becomes yellow, orange or red, or changes between them.

</details>

<details>
<summary>Notify a risk at the minimum level of warning</summary>

```yaml
alias: DPC risks
triggers:
  - trigger: state
    entity_id:
      - binary_sensor.dpc_milano_today_hydraulic_risk
      - binary_sensor.dpc_milano_today_thunderstorm_risk
      - binary_sensor.dpc_milano_today_hydrogeological_risk
      - binary_sensor.dpc_milano_tomorrow_hydraulic_risk
      - binary_sensor.dpc_milano_tomorrow_thunderstorm_risk
      - binary_sensor.dpc_milano_tomorrow_hydrogeological_risk
    to: "on"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "{{ state_attr(trigger.entity_id, 'friendly_name') }}"
      # The level of the same risk and day: binary_sensor.…_risk → sensor.…_risk_level
      message: >-
        {{ state_translated(trigger.entity_id | replace('binary_sensor.', 'sensor.')
        ~ '_level') }}
mode: queued
```

For example *Milano · Tomorrow Hydrogeological risk: Orange alert*. The binary sensors turn on at the minimum level of warning of the options, one risk at a time. The message finds the level from the entity ID of the binary sensor, so it needs the entity IDs of new places.

</details>

<details>
<summary>Notify heavy precipitation</summary>

```yaml
alias: DPC precipitation
triggers:
  - trigger: state
    entity_id:
      - sensor.dpc_milano_today_precipitation
      - sensor.dpc_milano_tomorrow_precipitation
      - sensor.dpc_milano_after_tomorrow_precipitation
    to:
      - moderate
      - heavy
      - very_heavy
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "{{ state_attr(trigger.entity_id, 'friendly_name') }}"
      message: "{{ state_translated(trigger.entity_id) }}"
mode: queued
```

</details>

<details>
<summary>Notify a weather phenomenon near home</summary>

```yaml
alias: DPC phenomena near home
triggers:
  - trigger: geo_location
    source: dpc
    zone: zone.around_home
    event: enter
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: DPC
      message: "{{ state_attr(trigger.to_state.entity_id, 'friendly_name') }}"
mode: queued
```

The phenomena must be on in the options. `zone.around_home` is a zone you create around home, with the radius you care about, such as 20 km, in **Settings → Areas, labels & zones → Zones**: the zone Home is usually too small. The automation runs when a phenomenon of the bulletin is inside it, for example *Milano · Tomorrow Light or moderate snowfall, 44.3 km NNE*: its day, type, distance and direction from the place.

</details>

## License

_Information provided by [_Department of Civil Protection - Presidency of the Council of Ministers_](https://www.protezionecivile.gov.it/en/) Creative Commons License [_CC BY 4.0._](https://creativecommons.org/licenses/by/4.0/)_

_Dati forniti dal servizio [_Dipartimento della Protezione Civile-Presidenza del Consiglio dei Ministri_](https://www.protezionecivile.gov.it/it/) Licenza Creative Commons [_CC BY 4.0._](https://creativecommons.org/licenses/by/4.0/deed.it)_

## Contributions are welcome

---

## Trademark Legal Notices

All product names, trademarks and registered trademarks in the images in this repository, are property of their respective owners.
All images in this repository are used by the author for identification purposes only.
The use of these names, trademarks and brands appearing in these image files, do not imply endorsement.

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg
[github latest release]: https://img.shields.io/github/v/release/caiosweet/Home-Assistant-custom-components-DPC-Alert
[githubrelease]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/releases
[github release date]: https://img.shields.io/github/release-date/caiosweet/Home-Assistant-custom-components-DPC-Alert
[maintenancebadge]: https://img.shields.io/badge/Maintained%3F-Yes-brightgreen.svg
[maintenance]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/graphs/commit-activity
[github issuesbadge]: https://img.shields.io/github/issues/caiosweet/Home-Assistant-custom-components-DPC-Alert
[github issues]: https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues
[website]: https://hassiohelp.eu/
[websitebadge]: https://img.shields.io/website?down_message=Offline&label=HssioHelp&logoColor=blue&up_message=Online&url=https%3A%2F%2Fhassiohelp.eu
[telegram]: https://t.me/HassioHelp
[telegrambadge]: https://img.shields.io/badge/Chat-Telegram-blue?logo=Telegram
[facebook]: https://www.facebook.com/groups/2062381507393179/
[facebookbadge]: https://img.shields.io/badge/Group-Facebook-blue?logo=Facebook
[forum]: https://forum.hassiohelp.eu/
[forumbadge]: https://img.shields.io/badge/HassioHelp-Forum-blue?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAA0ppVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8%2BIDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNS1jMDIxIDc5LjE1NTc3MiwgMjAxNC8wMS8xMy0xOTo0NDowMCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6ODcxMjY2QzY5RUIzMTFFQUEwREVGQzE4OTI4Njk5NDkiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6ODcxMjY2QzU5RUIzMTFFQUEwREVGQzE4OTI4Njk5NDkiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENDIDIwMTQgKFdpbmRvd3MpIj4gPHhtcE1NOkRlcml2ZWRGcm9tIHN0UmVmOmluc3RhbmNlSUQ9ImFkb2JlOmRvY2lkOnBob3Rvc2hvcDo0MWVhZDAwNC05ZWFmLTExZWEtOGY3ZS1mNzQ3Zjc1MjgyNGIiIHN0UmVmOmRvY3VtZW50SUQ9ImFkb2JlOmRvY2lkOnBob3Rvc2hvcDo0MWVhZDAwNC05ZWFmLTExZWEtOGY3ZS1mNzQ3Zjc1MjgyNGIiLz4gPC9yZGY6RGVzY3JpcHRpb24%2BIDwvcmRmOlJERj4gPC94OnhtcG1ldGE%2BIDw/eHBhY2tldCBlbmQ9InIiPz4xQPr3AAADq0lEQVR42rRVW2wMURj%2Bz5lL7V27KG26KIuUEJemdalu3VN3Ei/ipSWUuIV4FB4kHrwo8VLRROJBgkYElZCi4olG4rVoROOSbTa0u7pzO/6Z2Zmd3Z2uevBn/8zsf/7zff/tnKGMMRi/pjM6/j08oKiqCm1tbTA4OAhuoqkS8KKPVjceOcgJngkfnl%2B5JiWH0pQvcfUPhULQ0dEBPp8PDBZZlqGyshLGFKG0fHHr/QfNlxnbjFp7uOcl8VVVj%2BXu9XohkUgY2NRpdJMpc5qWN5971zu7ftsWkSAX2iKLYg3NZ/t6Kxbu2Oi2x4g8IxSKSDR2tLXh2JOn3nAkKv9GAzPtyigS%2BSdV1B3sejhv09lTxTBcCXjRK9buu96%2BZG/7dUYEryK59EXWewNcza7zl%2Br237kpessC4yIITIlGGk88666OtR6VMFKmZhZY9sGsdw1ATgFU1O7et%2Brki56JVUtqsl4kl0CVUjB57vo1Tad7X4Wj9U1S0vRj8HfRSQKVC5auPN7zctqiPTs1Rz2pBV6xcOuq%2BkOPusVAeZWxDg5wl%2Bhz1vW%2BpBFMDIYXt9y%2BF6lr2a6kR7IEmipDeFYsRkVewFcTyAXcBtNMhTxCTTErUxZdu96qLW8varhFsyrnQCQOYNXU8qBp//4TH/jkHZ3UCTXFoncQGKciP1SiN1JDVY2IJwgEjq3jYMVsZgC/HSBw9RnA8CgBjmS3MkdefE638sCV0WGQk9/QXYNRicH%2B7eWwYUGpOT4oq%2Bfq0Upw4SEPVOCLnwOWp5o%2BgskfWEoZe8Qg6CGwcp7XWFVxTc0UYdlMrLmQsP8zVuQcWFNiORFCTSvRQTWQs6W101SRXE7/xiDSBeC5BKywRLx/KqbuA44TYUQS4HHfsLHEcZyhulP32zjEUwL2ACuPt24%2BR0HhnONJBA8IoRlG/4P4/%2B57FTTyC9bUMAQk8OJ9Am69VsHjC2cOJbPaU0iQn4DxrjnSwVwp4eF2XwC63uBVLCchpXgQPAiUUrM8xBwlfeqs%2Bc7JwFn//KHKtAI8IkVejFgIgY8p2etEB7cPDbF32wSE8pwx926XTx6pAcPxxmFlzIo2o/qPy84sb4JTSMb7v3qiGFhJIaAzw1wbkmh8tu4IrqKm4v347V1qmvQGKvjJjEyf7v/pX3GmrGp%2BtT73UDyRHCPLMBDKwUj801dl4P7Fwc8fh0rLwiaBrp2dN2Do%2Bxfb%2Bd%2BE2GwEe%2BEPTYaW1gNQUiKaBP9T/ggwAJik5dEKYSC3AAAAAElFTkSuQmCC
