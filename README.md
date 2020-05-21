[![hacs][hacsbadge]][hacs]
![hacs_validate](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/workflows/Validate%20with%20HACS/badge.svg)
![Validate with hassfest](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/workflows/Validate%20with%20hassfest/badge.svg)

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/caiosweet/Home-Assistant-custom-components-DPC-Alert)](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/releases)
![GitHub Release Date](https://img.shields.io/github/release-date/caiosweet/Home-Assistant-custom-components-DPC-Alert)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-Yes-brightgreen.svg)](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/graphs/commit-activity)
[![GitHub issues](https://img.shields.io/github/issues/caiosweet/Home-Assistant-custom-components-DPC-Alert)](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues)

# Home-Assistant-custom-components-DPC-Alert
Italy METEO-HYDRO ALERT
To get more detailed information about parameters of warnings visit [*Civil Protection Department*](http://www.protezionecivile.gov.it/risk-activities/meteo-hydro/activities/prediction-prevention/central-functional-centre-meteo-hydrogeological/meteo-hydro-alert).

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show METEO-HYDRO ALERT `on` or `off`.


## Configuration options

| Key | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | `string` | `False` | `dpc` | Name of sensor |
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


## Contributions are welcome!

_Thanks to PiotrMachowski for inspiration._ 


***

[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg

![Validate with hassfest](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/workflows/Validate%20with%20hassfest/badge.svg)


![hacs_validate](https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/workflows/Validate%20with%20HACS/badge.svg)
