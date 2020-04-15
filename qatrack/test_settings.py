NOTIFICATIONS_ON = False
DEFAULT_NUMBER_FORMAT = None
DEBUG = False
SELENIUM_VIRTUAL_DISPLAY = True
AD_CLEAN_USERNAME = None
USE_SERVICE_LOG = True
USE_PARTS = True
HTTP_OR_HTTPS = "http"
REVIEW_BULK = True

try:
    from .local_test_settings import *
except ImportError:
    pass
