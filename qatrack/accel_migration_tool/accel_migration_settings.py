
from django.conf import settings as qat_settings

ACCEL_DB_LOCATION = ''
PARTS_DB_LOCATION = ''

DB_USER = ''
DB_PASS = ''

USE_LDAP = False

TIME_ZONE = qat_settings.TIME_ZONE

from .local_accel_settings import *
