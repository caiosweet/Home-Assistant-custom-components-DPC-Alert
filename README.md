# Home Assistant - Custom Components DPC Alert

<img src="https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/blob/main/assets/brand/icon.png" width="150px">

###### ITALY METEO-HYDRO ALERT - To get more detailed information about parameters of warnings visit [_Civil Protection Department_](https://rischi.protezionecivile.gov.it/en/meteo-hydro/alert). [_Dipartimento Protezione Civile_](https://rischi.protezionecivile.gov.it/it/meteo-idro/allertamento)

[![hacs][hacsbadge]][hacs] [![Validate](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/actions/workflows/validate.yaml/badge.svg)](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/actions/workflows/validate.yaml)

[![GitHub latest release]][githubrelease] ![GitHub Release Date] [![Maintenancebadge]][maintenance] [![GitHub issuesbadge]][github issues]

[![Websitebadge]][website] [![Forum][forumbadge]][forum] [![telegrambadge]][telegram] [![facebookbadge]][facebook]

[![Don't buy me a coffee](https://img.shields.io/static/v1.svg?label=Don't%20buy%20me%20a%20coffee&message=🔔&color=black&logo=buy%20me%20a%20coffee&logoColor=white&labelColor=6f4e37)](https://paypal.me/hassiohelp)

---

## Information

> The state of the sensor will be the highest alert level.

The Vigilance sensor will also report in attributes the values of all other meteo alerts and/or forecasts from next 12-48 hours, if there are any.

The Criticality sensor (DPC Alert) will also report in attributes the values of all other warning and/or forecasts from next 12-24 hours, if there are any.

## Installation

### Using [Home Assistant Community Store](https://hacs.xyz/) (recommended)

1. Click on HACS in the Home Assistant menu
2. Click on `Integrations`
3. Click the `EXPLORE & ADD REPOSITORIES` button
4. Search for `Dpc`
5. Click the `INSTALL THIS REPOSITORY IN HACS` button
6. Restart Home Assistant

## Configuration

### Config flow

To configure this integration go to: `Configurations` -> `Integrations` -> `ADD INTEGRATIONS` button, search for `Dpc` and configure the component.

You can also use following [My Home Assistant](http://my.home-assistant.io/) link

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=dpc)

### Setup

Now the integration is added to HACS and available in the normal HA integration installation

1. In the HomeAssistant left menu, click `Configuration`
2. Click `Integrations`
3. Click `ADD INTEGRATION`
4. Type `Dpc` and select it
5. Enter the details:
   1. **Name**: Your location name or name of sensor
   2. **Latitude**: Latitude of monitored point
   3. **Longitude**: Longitude of monitored point
6. Optional:
   1. Binary sensor enable/disable
   2. Sensor enabled/disable
   3. Update interval (minutes, default 30)
   4. Minimum level of warning. (int, default 2)

> :warning: **Multiple instance are possible, but... for the moment the updates are independent, it is advisable not to exceed more than two / three locations.**

## Preview [From my Natural Events project.][guide]

<p align="center">
<img src="https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/blob/main/assets/images/example-card-auto-entities.png" width="350px" /> 
<br><br>
Cards: card-mod, auto-entities
<br><br>
</p>

<p align="center">
<img src="https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/blob/main/assets/images/example-card-markdown.png" width="350px" />
<br><br>
Cards: card-mod, markdown
</p>

<p align="center">
<img src="https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/blob/main/assets/images/example-map.png" width="350px" />
<br><br>
Cards: card-mod, auto-entities, config-template-card
</p>

## Here are some advanced examples of using the entities created with this component

### Representation of the attributes present in the sensor (DPC Alert)

```yaml
attribution: Data provided by Civil Protection Department
integration: dpc
id: "20210805_1513"
publication_date: "2021-08-05T15:13:00"
last_update: "2021-08-05T19:48:05.000855"
max_level: 3
total_alerts: 2
today:
  info: Moderata per rischio temporali
  alert: ALLERTA ARANCIONE
  level: 3
  image_url: >-
    https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/files/preview/20210805_1513_oggi.png
  expires: "2021-08-05T00:00:00"
events_today:
  - risk: Temporali
    info: Moderata
    alert: ALLERTA ARANCIONE
    level: 3
    icon: mdi:weather-lightning
  - risk: Idrogeologico
    info: Moderata
    alert: ALLERTA ARANCIONE
    level: 3
    icon: mdi:waves
tomorrow:
  info: Assenza di fenomeni significativi prevedibili
  alert: NESSUNA ALLERTA
  level: 1
  image_url: >-
    https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/files/preview/20210805_1513_domani.png
  expires: "2021-08-06T00:00:00"
zone_name: Lario e Prealpi occidentali
friendly_name: DPC Alert
icon: mdi:hazard-lights
```

### Representation of the attributes present in the binary sensor

```yaml
attribution: Data provided by Civil Protection Department
integration: dpc
aftertomorrow:
  phenomena:
    - id: 202108053
      date: 2021-08-04Z
      id_event: 1
      event: Precipitazioni
      value: piogge sparse o intermittenti
      latitude: 45.926239089165264
      longitude: 9.31893208546803
      distance: 8
      direction: NNE
      degrees: 27
      icon: mdi:water
  icon: mdi:numeric-3-circle
  image_url: null
  level: 3
  precipitation: Moderati
tomorrow:
  phenomena: []
  icon: mdi:numeric-1-circle
  image_url: >-
    https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Vigilanza-Meteorologica/master/files/preview/20210805_domani.png
  level: 1
  precipitation: Assenti o non rilevanti
today:
  phenomena: []
  icon: mdi:numeric-1-circle
  image_url: >-
    https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Vigilanza-Meteorologica/master/files/preview/20210805_oggi.png
  level: 1
  precipitation: Assenti o non rilevanti
id: "20210805"
zone_name: Piemonte settentrionale e Lombardia nord-occidentale
last_update: "2021-08-05T20:48:05.002004"
max_level: 3
total_phenomena: 1
total_alerts: 1
friendly_name: DPC Vigilance
icon: mdi:hazard-lights
```

### Lovelace markdown card example sensor

```yaml
type: markdown
content: |-

  ___

  {% set entity = 'sensor.dpc_alert' %}

  #### PROTEZIONE CIVILE - [CRITICITA](https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-criticita)

  ##### ZONA {{state_attr(entity, 'zone_name')}}


  {% set color = {0:'White', 1:'Green', 2:'Gold', 3:'Orange', 4:'Red'} %}
  {% set days_map = {'today':'Oggi.', 'tomorrow':'Domani.', 'aftertomorrow': 'Dopodomani.'} %} 
  {%- for day in ['today', 'tomorrow'] %}
  {% set d = state_attr(entity, day) %}
  {%- set events = state_attr(entity, 'events_'+day) %}
  {%- if d %} 
  {%- if  d['level'] >= 1 %}

  |   |   |
  |:--|:--|
  | <font color="{{ color.get(d['level']) }}"/> <ha-icon icon="{{ 'mdi:numeric-' ~ d['level'] ~ '-box'}}"/></ha-icon> | {{ days_map[day] }} {{d['info']}} {{d['alert']}}</font> |
  {% endif %}
  {%- endif %}
  {%- if events %} 
  {%- for ev in events %}

  |   |   |   |
  |:--|:--|:--|
  | <font color="{{ color.get(ev['level']) }}"/> <ha-icon icon="{{ 'mdi:numeric-' ~ ev['level'] }}"/> | <font color="{{ color.get(ev['level']) }}"/> <ha-icon icon="{{ ev['icon'] }}"/> | {{ ev['alert'] }} {{ ev['info'] }} criticità per rischio {{ ev['risk'] }} |

  {%- endfor %} 
  {%- endif %}
  {%- endfor %}

  ___

  {% set entity = 'sensor.dpc_vigilance' %}

  #### PROTEZIONE CIVILE - [VIGILANZA METEO](https://mappe.protezionecivile.it/it/mappe-rischi/bollettino-di-vigilanza)

  ##### ZONA {{state_attr(entity, 'zone_name')}}

  {% set color = {0:'White', 1:'Green', 2:'Gold', 3:'Orange', 4:'Red', 5: 'BlueViolet'} %}
  {# set color_vigilance = {0:'#FFFFFF', 1:'#008000', 2:'#C3FFFE', 3:'#50FFFF', 4:'#508BFF', 5: '#A040FF'} #}
  {% set color_v = {0:'White', 1:'Green', 2:'LightCyan', 3:'BabyBlue', 4:'CornflowerBlue', 5: 'BlueViolet'} %}
  {% set day = {'today':'Oggi.', 'tomorrow':'Domani.', 'aftertomorrow': 'Dopodomani.'} %} 
  {%- for status in ['today', 'tomorrow','aftertomorrow'] %}
  {% set v = state_attr(entity, status) %}
  {%- if v %} 
  {%- if v['level'] >= 1 %}
  <font color="{{ color_v.get(v['level']) }}"/> <ha-icon icon="{{ v['icon'] }}"/></ha-icon> {{ day[status] }} Quantitativi previsti {{ v['precipitation'] }} </font>
  {%- endif %}
  {%- if v.phenomena %} 
  {% for d in v.phenomena %}

  |   |   |
  |:--|:--|
  | <ha-icon icon="{{ d['icon'] }}"/> |{{ d['event'] }} {{ d['value'] }} [{{ d['distance'] }} Km {{ d['direction'] }}] |

  {%- endfor %}
  {%- endif %}
  {%- endif %}
  {%- endfor %}

  [Sito Web Protezione Civile](https://www.protezionecivile.gov.it/it/) ~ [Radar](https://mappe.protezionecivile.it/it/mappe-rischi/piattaforma-radar)
```

### Lovelace markdown card example Binary Sensor

```yaml
type: markdown
card_mod:
  style: |
    ha-card {background: none; border-radius: 0px; box-shadow: none;}
content: >
  ___

  #### PROTEZIONE CIVILE

  {% set color = {0:'White', 1:'Green', 2:'Yellow', 3:'Orange', 4:'Red'} %} 
  {% for state in states.binary_sensor %} 
  {%- if is_state_attr(state.entity_id, 'integration', 'dpc') and state.state == 'on' %} 

  <font color= {{color[state.attributes.level|int]}}> <ha-icon icon="{{ 'mdi:numeric-' ~ state.attributes.level|int ~ '-box'}}" style="width: 36px; height: 36px;"></ha-icon>  
  {{state.name}} - {{state.attributes.alert}} {{state.attributes.info}}</font> 
  {%- endif -%} {% endfor %}

  [Protezione Civile](https://www.protezionecivile.gov.it/it/) ~ [Vigilanza Meteo](https://mappe.protezionecivile.it/it/mappe-rischi/bollettino-di-vigilanza)
  ~ [Criticità Idro](https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-criticita) ~ [Radar](https://mappe.protezionecivile.it/it/mappe-rischi/piattaforma-radar)
```

### Lovelace config-template-card example to display maps

```yaml
type: custom:config-template-card
entities:
  - sensor.date
card:
  type: iframe
  card_mod:
    style: |
      ha-card {
        border-radius: var(--ha-card-border-radius);
        margin-top: 8px;
      }
  aspect_ratio: 100%
  url: >-
    ${'https://servizio-mappe.protezionecivile.it/#/view/dashboard?x=11.756&y=41.495&
    zoom=5.8&basemap=OPEN_STREET_MAP&appname=Bollettino di Vigilanza&file=
    https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Vigilanza-Meteorologica/master/files/'
    +states['sensor.dpc_vigilance'].attributes.id+'.json&hidden=minimap,info&fase=today'}
```

```yaml
type: custom:config-template-card
entities:
  - sensor.time
card:
  type: iframe
  card_mod:
    style: |
      ha-card {
        border-radius: var(--ha-card-border-radius);
        margin-top: 8px;
      }
  aspect_ratio: 100%
  #maps...GOOGLE_SATELLITE, GOOGLE_HYBRID, GOOGLE_NORMAL OPEN_STREET_MAP, BING_AERIAL, , ORTHO_MAP, DARK_BASE_MAP
  url: >-
    ${'https://servizio-mappe.protezionecivile.it/#/view/dashboard?x=11.756&y=41.495&
    zoom=5.8&basemap=BING_AERIAL&appname=BollettinodiCriticità&file=
    https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/files/'
    +states['sensor.dpc_alert'].attributes.id+'.json&hidden=switch,info,minimap&fase=tomorrow'}
```

### Automation example using the sensors (Compatible with UI Automation Editor)

```yaml
alias: protezione_civile_notifications_criticita_sensor
trigger:
  - platform: state
    entity_id:
      - sensor.dpc_alert
condition:
  - condition: template
    value_template: >-
      {{ not trigger.from_state.state in ["unavailable","unknown"]  and (
      trigger.from_state.attributes.total_alerts !=
      trigger.to_state.attributes.total_alerts or
          ( trigger.to_state.attributes.id != trigger.from_state.attributes.id and trigger.to_state.attributes.total_alerts > 0 )) }}
action:
  - variables:
      BULLETIN: >-
        https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-criticita
      WARNING_SIGN:
        "0": ⚪
        "1": 🟢
        "2": 🟡
        "3": 🟠
        "4": 🔴
      WARN_DPC:
        none: ❌
        Temporali: ⚡
        Idraulico: 💧
        Idrogeologico: 🌊
      ENTITY: "{{ trigger.entity_id |default('sensor.dpc', true) }}"
      DAYS:
        "1": today
        "2": tomorrow
      GIORNI:
        "1": oggi
        "2": domani
  - repeat:
      while:
        - condition: template
          value_template: "{{ repeat.index <= DAYS|length }}"
      sequence:
        - variables:
            giorno: "{{ GIORNI[repeat.index|string] }}"
            day: "{{ DAYS[repeat.index|string] }}"
            event: "{{ 'events_' + day }}"
        - choose:
            - conditions:
                - condition: template
                  value_template: "{{ state_attr(ENTITY, event) is not none }}"
              sequence:
                - service: notify.discord
                  data:
                    title: DPC Criticità
                    message: >
                      {% set attr = state_attr(ENTITY, event) %}

                      Criticità per {{giorno}}

                      {%- for d in attr %}

                      {{WARNING_SIGN[d['level']|string]}} {{ WARN_DPC[d['risk']]
                      }} {{ d['info'] }} {{ d['alert'] }} per rischio {{
                      d['risk'] }}.

                      {%- endfor %}

                      Zona: {{ state_attr(ENTITY, 'zone_name') }}
mode: queued
max_exceeded: silent
max: 10
```

```yaml
alias: protezione_civile_notifications_vigilance_sensor
trigger:
  - platform: state
    entity_id:
      - sensor.dpc_vigilance
condition:
  - condition: template
    value_template: >-
      {{ trigger.from_state.state not in ["unavailable","unknown"]  and (
      trigger.from_state.attributes.total_alerts !=
      trigger.to_state.attributes.total_alerts or
          ( trigger.to_state.attributes.id != trigger.from_state.attributes.id and
          ( trigger.to_state.attributes.total_phenomena > 0 or trigger.to_state.attributes.total_alerts > 0 ))) }}
action:
  - variables:
      BULLETIN: >-
        https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-vigilanza
      ENTITY: "{{ trigger.entity_id |default('sensor.dpc_vigilance', true) }}"
      DAYS:
        "1": today
        "2": tomorrow
        "3": aftertomorrow
      GIORNI:
        "1": oggi
        "2": domani
        "3": dopodomani
      WARNING_SIGN:
        "0": ⚪
        "1": 🟢
        "2": 🟡
        "3": 🟠
        "4": 🔴
  - repeat:
      while:
        - condition: template
          value_template: "{{ repeat.index <= DAYS|length }}"
      sequence:
        - variables:
            giorno: "{{ GIORNI[repeat.index|string] }}"
            day: "{{ DAYS[repeat.index|string] }}"
        - choose:
            - conditions:
                - condition: template
                  value_template: "{{ state_attr(ENTITY, day) is not none }}"
                - condition: template
                  value_template: "{{ state_attr(ENTITY, day).level|default|int > 1 }}"
              sequence:
                - service: notify.pushover
                  data:
                    title: DPC Vigilanza Meteo
                    message: >
                      {% set attr = state_attr(ENTITY, day) %}

                      Vigilanza meteo per {{giorno}}

                      {{WARNING_SIGN[attr['level']|string]}} Quantitativi
                      previsti {{attr['precipitation']}}

                      {% if 'phenomena' in attr %}

                      Fenomeni nelle vicinanze:

                      {% for f in attr['phenomena'] %}

                      ➡️ {{f.event}}: {{f.value}} in direzione {{f.direction}}
                      alla distanza di {{f.distance}}km.

                      {% endfor %}

                      {% endif %}


                      Zona: {{ state_attr(ENTITY, 'zone_name') }}
mode: queued
max_exceeded: silent
max: 10
```

### Automation example using the binary sensor (Compatible with UI Automation Editor)

```yaml
automation:
  - alias: Protezione Civile Notifications
    mode: queued
    max_exceeded: silent
    max: 10
    trigger:
      - platform: state
        entity_id:
          - binary_sensor.dpc_idrogeologico_oggi
          - binary_sensor.dpc_idraulico_oggi
          - binary_sensor.dpc_temporali_oggi
          - binary_sensor.dpc_idrogeologico_domani
          - binary_sensor.dpc_idraulico_domani
          - binary_sensor.dpc_temporali_domani
    condition:
      - condition: template
        value_template: >-
          {{ trigger.to_state.state == 'on' and (trigger.from_state.state == 'off'
          or (trigger.to_state.attributes != trigger.from_state.attributes))}}
    action:
      - variables:
          BULLETIN: "https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-criticita"
          dpc_tts_msg: >-
            {% set attr = trigger.to_state.attributes if trigger.to_state is defined else ({}) %}
            Attenzione. {{ attr.get('friendly_name','Test DPC') }}.
            Allerta {{ attr.get('allerta','Bianca') }} {{ attr.get('info','Nessuna info') }}.
      - service: notify.pushover
        data:
          title: >-
            {% set attr = trigger.to_state.attributes if trigger.to_state is defined else ({}) %}
            Protezione Civile - {{ attr.get(''rischio'') }}
          message: |
            {% set attr = trigger.to_state.attributes if trigger.to_state is defined else ({}) %}
            {% set alert = {'0': '⚪', '1':'🟢', '2':'🟡', '3':'🟠', '4': '🔴'} %}
            {% set risk = {none: '❌', 'Temporali':'⚡', 'Idraulico':'💧', 'Idrogeologico':'🌊'} %}
            {{ risk[attr.get('rischio')] }} {{ attr.get('friendly_name','Test DPC') }}.
            {{ alert[attr.get('level', 0)|string] }} Allerta {{ attr.get('allerta','Bianca') }}
            {{ attr.get('info','No info') }}.

            Bollettino di criticità {{ attr.get('link', BULLETIN) }}
      - service: tts.google_translate_say
        data:
          message: "{{ dpc_tts_msg }}"
          entity_id: media_player.red
      - service: notify.alexa_media
          data:
            message: "{{ dpc_tts_msg }}"
            data:
              type: tts
            target: "media_player.studio"
```

## Other Lovelace Examples [HA Card weather conditions](https://github.com/r-renato/ha-card-weather-conditions#display-the-alert-layer) [@r-renato](https://github.com/r-renato)

## License

_Information provided by [*Department of Civil Protection - Presidency of the Council of Ministers*](https://www.protezionecivile.gov.it/en/) Creative Commons Licenses [*CC-BY-SA 4.0.*](https://creativecommons.org/licenses/by-sa/4.0/)_

_Dati forniti dal servizio [*Dipartimento della Protezione Civile-Presidenza del Consiglio dei Ministri*](https://www.protezionecivile.gov.it/it/) Licenza Creative Commons [*CC-BY-SA 4.0.*](https://creativecommons.org/licenses/by-sa/4.0/deed.it)_

## Contributions are welcome

---

## Trademark Legal Notices

All product names, trademarks and registered trademarks in the images in this repository, are property of their respective owners.
All images in this repository are used by the author for identification purposes only.
The use of these names, trademarks and brands appearing in these image files, do not imply endorsement.

[guide]: https://hassiohelp.eu/2019/10/06/home-assistant-package-eventi-naturali/
[hacs]: https://github.com/custom-components/hacs
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
