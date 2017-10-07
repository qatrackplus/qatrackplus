NOTIFICATIONS_ON = False
DEBUG = False

try:
    from .local_test_settings import *
except ImportError:
    pass
