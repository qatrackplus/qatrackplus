
import os

from selenium import webdriver
from .settings import PROJECT_ROOT, INSTALLED_APPS

NOTIFICATIONS_ON = False
DEBUG = False

SELENIUM_DRIVER = webdriver.Firefox
os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = 'localhost:8000'

try:
    from local_test_settings import *
except ImportError:
    pass
