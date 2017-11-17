
import re

from django.conf import settings as qat_settings

ACCEL_DB_LOCATION = ''
ACCEL_PARTS_DB_LOCATION = ''

DB_USER = ''
DB_PASS = ''

PARTS_DB_USER = ''
PARTS_DB_PASS = ''

USE_LDAP = False

TIME_ZONE = qat_settings.TIME_ZONE

FIND_RELATED_IN_PROBLEM = True
RELATED_EVENT_REGEX = re.compile(r'(SR|sr|[rR]eport) ?#? ?([0-9]+)')

from .local_accel_settings import *
