NOTIFICATIONS_ON = False
DEBUG = False
USE_PARTS = True
SELENIUM_VIRTUAL_DISPLAY = True
AD_CLEAN_USERNAME = None

try:
    from .local_test_settings import *
except ImportError:
    pass
