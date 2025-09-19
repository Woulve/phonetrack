import re

DOMAIN = "phonetrack"

CONF_DEVICE_NAME = "device_name"
CONF_MAX_GPS_ACCURACY = "max_gps_accuracy"
CONF_UPDATE_INTERVAL = "update_interval"


def redact_url(url: str) -> str:
    url = re.sub(r"([?&]token=)[^&]*", r"\1[REDACTED]", url)
    url = re.sub(r"(/getlastpositions/)[a-f0-9]{32,}", r"\1[REDACTED]", url)
    return url
