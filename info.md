
## breaking change (2/10/2019)
ISTAT number is now required.
Rename codice to level in attributes.

# Home-Assistant-custom-components-DPC-Alert
Italy METEO-HYDRO ALERT
To get more detailed information about parameters of warnings visit [*Civil Protection Department*](http://www.protezionecivile.gov.it/risk-activities/meteo-hydro/activities/prediction-prevention/central-functional-centre-meteo-hydrogeological/meteo-hydro-alert).

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show METEO-HYDRO ALERT `True` or `False`.


## Configuration options

| Key | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | `string` | `False` | `dpc` | Name of sensor |
| `latitude` | `float` | `False` | Latitude of home | Latitude of monitored point |
| `longitude` | `float` | `False` | Longitude of home | Longitude of monitored point |
| `istat` | `string` | `True` | None | Number data warehouse I.Stat |
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
    istat: 58091
    warnings:
      - temporali_oggi
```

## Example usage (complete)

```
binary_sensor:
  - platform: dpc
    latitude: 41.9109
    longitude: 12.4818
    name: DPC Roma
    istat: '058091'
    alert: 'gialla'
    warnings:
      - temporali_oggi
      - idraulico_oggi
      - idrogeologico_oggi
      - temporali_domani
      - idraulico_domani
      - idrogeologico_domani
```

## Note

The istat number is required, you can easily find it [here](https://www.paginebianche.it/codice-istat)
or you can download the complete list [here](https://www.istat.it/storage/codici-unita-amministrative/Elenco-codici-statistici-e-denominazioni-delle-unita-territoriali.zip)
If the Istat number starts with zero, it must be entered between the quotes.

## License

_Information provided by [*protezionecivilepop.tk*](http://www.protezionecivilepop.tk/) Giovanni Pirrotta's Creative Commons Licenses [*CC-BY-SA 4.0.*](https://creativecommons.org/licenses/by-sa/4.0/)_

_Dati forniti dal servizio protezionecivilepop.tk di Giovanni Pirrotta - Licenza Creative Commons [*CC-BY-SA 4.0.*](https://creativecommons.org/licenses/by-sa/4.0/deed.it)_
