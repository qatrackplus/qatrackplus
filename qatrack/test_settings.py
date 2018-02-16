NOTIFICATIONS_ON = False
DEBUG = False
USE_PARTS = True
VERBOSE_TESTING = False
SELENIUM_VIRTUAL_DISPLAY = True

try:
    from .local_test_settings import *
except ImportError:
    pass
