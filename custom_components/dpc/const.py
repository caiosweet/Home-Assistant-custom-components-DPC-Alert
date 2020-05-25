"""Constants"""

ATTRIBUTION = "Information provided by protezionecivilepop.tk"

BASE_URL = "http://www.protezionecivilepop.tk/allerte?citta={}&rischio={}&allerta=verde&giorno={}&formato=json"
FEED_URL = "http://www.protezionecivile.gov.it/web/guest/dettaglio/-/journal/rss/351565?doAsGroupId=20182&refererPlid=42041&controlPanelCategory=current_site.content&_15_groupId=20182"
BULLETTIN_URL = "http://www.protezionecivile.gov.it/attivita-rischi/meteo-idro/attivita/previsione-prevenzione/centro-funzionale-centrale-rischio-meteo-idrogeologico/previsionale/bollettini-criticita/bollettino-odierno"
CONF_ALERT = "alert"
CONF_ISTAT = "istat"
CONF_WARNINGS = "warnings"

DEFAULT_DEVICE_CLASS = "safety"
DEFAULT_NAME = "dpc"

WARNING_TYPES = {
    "temporali_oggi": [
        "temporali_oggi",
        "Rischio Temporali Oggi",
        "mdi:weather-lightning",
    ],
    "idraulico_oggi": ["idraulico_oggi", "Rischio Idraulico Oggi", "mdi:home-flood"],
    "idrogeologico_oggi": [
        "idrogeologico_oggi",
        "Rischio Idrogeologico Oggi",
        "mdi:waves",
    ],
    "temporali_domani": [
        "temporali_domani",
        "Rischio Temporali Domani",
        "mdi:weather-lightning",
    ],
    "idraulico_domani": [
        "idraulico_domani",
        "Rischio Idraulico Domani",
        "mdi:home-flood",
    ],
    "idrogeologico_domani": [
        "idrogeologico_domani",
        "Rischio Idrogeologico Domani",
        "mdi:waves",
    ],
}

WARNING_ALERT = {
    "BIANCA": 0,
    "VERDE": 1,
    "GIALLA": 2,
    "ARANCIONE": 3,
    "ROSSA": 4,
}
