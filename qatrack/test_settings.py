NOTIFICATIONS_ON = False
DEBUG = False
AD_CLEAN_USERNAME = None

try:
    from .local_test_settings import *
except ImportError:
    pass
