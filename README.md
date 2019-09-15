# Home-Assistant-custom-components-DPC-Alert
Italy METEO-HYDRO ALERT
To get more detailed information about parameters of warnings visit [*Civil Protection Department*](http://www.protezionecivile.gov.it/risk-activities/meteo-hydro/activities/prediction-prevention/central-functional-centre-meteo-hydrogeological/meteo-hydro-alert).


## Configuration options

| Key | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | `string` | `False` | `dpc` | Name of sensor |
| `latitude` | `float` | `False` | Latitude of home | Latitude of monitored point |
| `longitude` | `float` | `False` | Longitude of home | Longitude of monitored point |
| `istat` | `string` | `False` | Self with local coordinates | Number data warehouse I.Stat |
| `alert` | `string` | `False` | GIALLA | (Verde,Gialla,Arancione,Rossa) |
| `warnings` | `list` | `False` | - | List of monitored warnings |

### Possible monitored warnings

| Key | Description |
| --- | --- | 
| `temporali_oggi` | Enables thunderstorms risk monitoring today |
| `idraulico_oggi` | Enables Hydraulic risk monitoring today |
| `idrogeologico_oggi` | Enables Hydrogeological risk monitoring today |
| `temporali_domani` | Enables thunderstorms risk monitoring tomorrow |
| `idraulico_domani` | Enables Hydraulic risk monitoring tomorrow |
| `idrogeologico_domani` | Enables Hydrogeological risk monitoring tomorrow |

## Example usage (minimal)

```
binary_sensor:
  - platform: dpc
    warnings:
      - temporali_oggi
      - idraulico_oggi
      - idrogeologico_oggi
      - temporali_domani
      - idraulico_domani
      - idrogeologico_domani
```

## Example usage (complete)

```
binary_sensor:
  - platform: dpc
    latitude: 41.9109
    longitude: 12.4818
    name: DPC Roma
    istat: '58091'
    alert: 'gialla'
    warnings:
      - temporali_oggi
      - idraulico_oggi
      - idrogeologico_oggi
      - temporali_domani
      - idraulico_domani
      - idrogeologico_domani
```

# Notice
_Information provided by [*protezionecivilepop.tk*](http://www.protezionecivilepop.tk/) Giovanni Pirrotta's Creative Commons Licenses [*CC-BY-SA 4.0.*](https://creativecommons.org/licenses/by-sa/4.0/)_

_Dati forniti dal servizio protezionecivilepop.tk di Giovanni Pirrotta - Licenza Creative Commons [*CC-BY-SA 4.0.*](https://creativecommons.org/licenses/by-sa/4.0/deed.it)_

_Thanks to PiotrMachowski for inspiration._ 

[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
