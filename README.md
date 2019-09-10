# Home-Assistant-custom-components-DPC-Alert
Italy METEO-HYDRO ALERT (Protezione Civile)
To get more detailed information about parameters of warnings [*Dipartimento della Protezione Civile*](http://www.protezionecivile.gov.it/risk-activities/meteo-hydro/activities/prediction-prevention/central-functional-centre-meteo-hydrogeological/meteo-hydro-alert).
visit 

## Example configuration.yaml

```yaml
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
