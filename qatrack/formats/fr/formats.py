DATETIME_FORMAT = "Y-M-j H:i"
DATE_FORMAT = "Y-M-j"
TIME_FORMAT = "H:i"
DATE_INPUT_FORMATS = [
    "%Y-%m-%d", 
    "%Y %m %d"
]
DATETIME_INPUT_FORMATS = [
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y %m %d %H:%M",
    "%Y %m %d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%fZ",
]
TIME_INPUT_FORMATS = ["%H:%M", "%H:%M:%S", "%H:%M:%S.%f"]

# JavaScript formats
# https://momentjs.com/docs/#/displaying/format/
MOMENT_DATE_DATA_FMT = "YYYY-MM-DD"
MOMENT_DATE_FMT = "YYYY-MM-DD"
MOMENT_DATETIME_FMT = 'YYYY-MM-DD HH:mm'
# https://flatpickr.js.org/formatting/
FLATPICKR_DATE_FMT = 'Y-m-d'
FLATPICKR_DATETIME_FMT = 'Y-m-d H:i'
# https://api.jqueryui.com/datepicker/
DATERANGEPICKER_DATE_FMT = 'YYYY-MM-DD'

# For using in local_settings.py, to translate DATETIME_HELP.
# Ensure this gives same result as MOMENT_DATETIME_FMT
# https://docs.python.org/3.9/library/datetime.html#strftime-and-strptime-format-codes
PYTHON_DATETIME_FORMAT = "%Y-%m-%d %H:%M"
