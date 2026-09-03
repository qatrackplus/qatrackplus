DATETIME_FORMAT = "Y-m-d H:i"
DATE_FORMAT = "Y-m-d"
TIME_FORMAT = "H:i"
DATE_INPUT_FORMATS = ["%d %b %Y", "%d/%m/%Y", "%Y-%m-%d"]
DATETIME_INPUT_FORMATS = [
    "%d %b %Y %H:%M",
    "%d %b %Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%fZ",
]
TIME_INPUT_FORMATS = ["%H:%M", "%H:%M:%S", "%H:%M:%S.%f"]

# JavaScript formats
MOMENT_DATE_DATA_FMT = "DD-MM-YYYY"
MOMENT_DATE_FMT = "DD MMM YYYY"
MOMENT_DATETIME_FMT = 'DD MMM YYYY HH:mm'
FLATPICKR_DATE_FMT = 'd M Y'
FLATPICKR_DATETIME_FMT = 'd M Y H:i'
DATERANGEPICKER_DATE_FMT = 'DD MMM YYYY'
