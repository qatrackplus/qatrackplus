NOTIFICATIONS_ON = False
DEBUG = False
SELENIUM_VIRTUAL_DISPLAY = True
AD_CLEAN_USERNAME = None
USE_SERVICE_LOG = True
USE_PARTS = True

try:
    from .local_test_settings import *
except ImportError:
    pass
