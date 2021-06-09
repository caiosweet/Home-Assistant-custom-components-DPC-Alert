"""Constants"""

ATTRIBUTION = "Information provided by Civil Protection Department"

BASE_URL = (
    "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/files"
    "/geojson/{}_{}.json"
)
BULLETTIN_URL = (
    "https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-criticita"
)
IMAGE_URL = "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/files/preview/{}_{}.png"
CONF_ALERT = "alert"
CONF_ISTAT = "istat"
CONF_WARNINGS = "warnings"
ISSUES_RESOURCE_URL = "https://github.com/gpirrotta/protezionecivilepop/issues"

DEFAULT_DEVICE_CLASS = "safety"
DEFAULT_NAME = "dpc"

WARNING_TYPES = {
    "idraulico_oggi": ["Rischio Idraulico Oggi", "mdi:home-flood"],
    "temporali_oggi": ["Rischio Temporali Oggi", "mdi:weather-lightning"],
    "idrogeologico_oggi": ["Rischio Idrogeologico Oggi", "mdi:waves"],
    "idraulico_domani": ["Rischio Idraulico Domani", "mdi:home-flood"],
    "temporali_domani": ["Rischio Temporali Domani", "mdi:weather-lightning"],
    "idrogeologico_domani": ["Rischio Idrogeologico Domani", "mdi:waves"],
}

WARNING_ALERT = {
    "BIANCA": 0,
    "VERDE": 1,
    "GIALLA": 2,
    "ARANCIONE": 3,
    "ROSSA": 4,
}
