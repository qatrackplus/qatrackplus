"""Settings for the Docker deployment, read from environment variables.

qatrack/settings.py calls apply() instead of importing local_settings when
USE_DOCKER is set. Every variable is optional: an unset or empty variable keeps
the default from settings.py. deploy/docker/.env.example documents each one.
"""
import datetime
import json
import os
import secrets
import tempfile
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from qatrack.qatrack_core.hosts import LOOPBACK_HOSTS

DEFAULT_SECRET_KEY_FILE = '/usr/src/qatrackplus/deploy/docker/user-data/secret_key.txt'

_TRUE = {'1', 'true', 'yes', 'on'}
_FALSE = {'0', 'false', 'no', 'off'}

WEEKDAYS = ('sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday')

USERNAME_CLEANING = {
    'none': lambda username: username,
    'lower': lambda username: username.lower(),
    'strip_domain': lambda username: username.split('\\')[-1],
    'lower_strip_domain': lambda username: username.split('\\')[-1].lower(),
    'strip_upn': lambda username: username.split('@')[0],
    'lower_strip_upn': lambda username: username.split('@')[0].lower(),
}


def parse_bool(value):
    normalized = value.strip().lower()
    if normalized in _TRUE:
        return True
    if normalized in _FALSE:
        return False
    raise ValueError("expected one of 1/0, true/false, yes/no, on/off")


def parse_csv(value):
    return [item.strip() for item in value.split(',') if item.strip()]


def parse_json(value):
    return json.loads(value)


def parse_hours(value):
    return datetime.timedelta(hours=float(value))


class Env:
    """Reads typed values from an environment mapping. Empty values count as unset."""

    def __init__(self, environ):
        self.environ = environ

    def raw(self, name):
        value = self.environ.get(name, '')
        return value.strip() or None

    def get(self, name, parse=str, default=None):
        value = self.raw(name)
        if value is None:
            return default
        try:
            return parse(value)
        except (TypeError, ValueError) as e:
            raise ImproperlyConfigured(f"Invalid value for the {name} environment variable: {e}") from e

    def override(self, g, name, parse=str):
        """Set setting `name` in `g` from the variable of the same name, if it is set."""
        value = self.get(name, parse)
        if value is not None:
            g[name] = value
        return value


def load_secret_key(env):
    """SECRET_KEY from the environment, else from a file kept in a volume.

    The file is created with a new key the first time, so the key survives
    container rebuilds instead of logging every user out on each upgrade.
    """
    key = env.raw('SECRET_KEY')
    if key:
        return key

    path = Path(env.raw('QATRACK_SECRET_KEY_FILE') or DEFAULT_SECRET_KEY_FILE)
    if path.exists():
        key = path.read_text(encoding='utf-8').strip()
        if not key:
            raise ImproperlyConfigured(f"The secret key file {path} is empty. Delete it to generate a new key.")
        return key

    key = secrets.token_urlsafe(64)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write the key to a private temporary file, then link it into place, so a
        # process starting at the same moment never reads a half-written key. If
        # another process published one first, use theirs.
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(key)
            os.link(tmp, path)
        except FileExistsError:
            return load_secret_key(env)
        finally:
            os.unlink(tmp)
    except OSError as e:
        raise ImproperlyConfigured(
            f"Could not save a new secret key to {path} ({e}). Set SECRET_KEY in deploy/docker/.env, "
            "or make that folder writable by the QATrack+ user."
        ) from e
    return key


def apply(g, environ=os.environ):
    """Update the settings namespace `g` from the environment."""
    env = Env(environ)

    # Hosts. The containers reach Django themselves through the loopback names
    # (the compose health check), so those are always allowed. CSRF origins are
    # derived from the site's own hosts before they are added, so localhost never
    # becomes a trusted origin.
    hosts = env.get('ALLOWED_HOSTS', parse_csv, default=list(LOOPBACK_HOSTS))
    csrf_origins = env.get('CSRF_TRUSTED_ORIGINS', parse_csv)
    if csrf_origins is None:
        csrf_origins = [scheme + host for host in hosts for scheme in ('http://', 'https://') if host != '*']
    g['CSRF_TRUSTED_ORIGINS'] = csrf_origins
    g['ALLOWED_HOSTS'] = hosts + [h for h in LOOPBACK_HOSTS if h not in hosts]

    g['SECRET_KEY'] = load_secret_key(env)

    # Database
    g['DATABASES'] = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.get('POSTGRES_DB', default='qatrackplus'),
            'USER': env.get('POSTGRES_USER', default='postgres'),
            'PASSWORD': env.get('POSTGRES_PASSWORD', default='postgres'),
            'HOST': env.get('POSTGRES_HOST', default='postgres'),
            'PORT': env.get('POSTGRES_PORT', int, default=5432),
        }
    }
    env.override(g, 'USE_SQL_REPORTS', parse_bool)
    if g.get('USE_SQL_REPORTS'):
        g['DATABASES']['readonly'] = g['DATABASES']['default']

    # General
    if env.override(g, 'ADMINS', parse_json) is not None:
        g['MANAGERS'] = g['ADMINS']
    for name in ('SITE_NAME', 'TIME_ZONE', 'LANGUAGE_CODE'):
        env.override(g, name)
    for name in ('USE_TZ', 'DEBUG', 'DEBUG_TOOLBAR'):
        env.override(g, name, parse_bool)

    # HTTPS behind the nginx proxy
    protocol = env.override(g, 'HTTP_OR_HTTPS')
    if protocol is not None and protocol not in ('http', 'https'):
        raise ImproperlyConfigured("HTTP_OR_HTTPS must be 'http' or 'https'.")
    if g.get('HTTP_OR_HTTPS') == 'https':
        g['SECURE_PROXY_SSL_HEADER'] = ('HTTP_X_FORWARDED_PROTO', 'https')
        g['SESSION_COOKIE_SECURE'] = True
        g['CSRF_COOKIE_SECURE'] = True
    for name in ('SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE', 'USE_X_FORWARDED_HOST'):
        env.override(g, name, parse_bool)

    # Sessions
    env.override(g, 'SESSION_COOKIE_AGE', int)
    env.override(g, 'SESSION_SAVE_EVERY_REQUEST', parse_bool)
    env.override(g, 'SESSION_EXPIRE_AT_BROWSER_CLOSE', parse_bool)

    # Email
    for name in (
        'EMAIL_HOST',
        'EMAIL_HOST_USER',
        'EMAIL_HOST_PASSWORD',
        'EMAIL_NOTIFICATION_SENDER',
        'EMAIL_NOTIFICATION_SUBJECT',
        'EMAIL_NOTIFICATION_TEMPLATE',
        'EMAIL_NOTIFICATION_SUBJECT_TEMPLATE',
    ):
        env.override(g, name)
    env.override(g, 'EMAIL_PORT', int)
    env.override(g, 'EMAIL_USE_TLS', parse_bool)
    env.override(g, 'EMAIL_FAIL_SILENTLY', parse_bool)

    # QC display
    for name in ('DEFAULT_WARNING_MESSAGE', 'ORDER_UNITS_BY'):
        env.override(g, name)
    for name in ('NHIST', 'PING_INTERVAL_S'):
        env.override(g, name, int)
    for name in ('CATEGORY_FIRST_OF_GROUP_ONLY', 'CHOOSE_UNIT_CATEGORY_DROPDOWN', 'REVIEW_DIFF_COL', 'REVIEW_BULK'):
        env.override(g, name, parse_bool)
    for name in ('ICON_SETTINGS', 'TEST_STATUS_DISPLAY', 'TEST_STATUS_DISPLAY_SHORT'):
        env.override(g, name, parse_json)
    available = dict(g['DEFAULT_AVAILABLE_TIMES'])
    for day in WEEKDAYS:
        hours = env.get(f'DEFAULT_AVAILABLE_HOURS_{day.upper()}', parse_hours)
        if hours is not None:
            available[f'hours_{day}'] = hours
    g['DEFAULT_AVAILABLE_TIMES'] = available

    # Accounts and authentication
    env.override(g, 'AUTHENTICATION_BACKENDS', parse_csv)
    env.override(g, 'ACCOUNTS_SELF_REGISTER', parse_bool)
    env.override(g, 'ACCOUNTS_PASSWORD_RESET', parse_bool)
    env.override(g, 'ACCOUNT_ACTIVATION_DAYS', int)
    env.override(g, 'AUTH_ADFS', parse_json)

    # Active Directory / LDAP
    for name in (
        'AD_DNS_NAME',
        'AD_LDAP_USER',
        'AD_LDAP_PW',
        'AD_LU_ACCOUNT_NAME',
        'AD_LU_MAIL',
        'AD_LU_SURNAME',
        'AD_LU_GIVEN_NAME',
        'AD_LU_MEMBER_OF',
        'AD_SEARCH_DN',
        'AD_NT4_DOMAIN',
        'AD_CERT_FILE',
        'CLEAN_USERNAME_STRING',
        'AD_CLEAN_USERNAME_STRING',
    ):
        env.override(g, name)
    env.override(g, 'AD_LDAP_PORT', int)
    env.override(g, 'AD_MIRROR_GROUPS', parse_bool)
    ldap_protocol = env.get('AD_LDAP_PROTOCOL', default='ldap')
    if ldap_protocol not in ('ldap', 'ldaps'):
        raise ImproperlyConfigured("AD_LDAP_PROTOCOL must be 'ldap' or 'ldaps'.")
    g['AD_LDAP_URL'] = env.get('AD_LDAP_URL', default=f"{ldap_protocol}://{g['AD_DNS_NAME']}:{g['AD_LDAP_PORT']}")
    g['AD_SEARCH_FIELDS'] = env.get(
        'AD_SEARCH_FIELDS',
        parse_csv,
        default=[g['AD_LU_MAIL'], g['AD_LU_SURNAME'], g['AD_LU_GIVEN_NAME'], g['AD_LU_ACCOUNT_NAME'], g['AD_LU_MEMBER_OF']],
    )
    cleaning = env.get('AD_USERNAME_CLEANING')
    if cleaning is not None:
        try:
            g['AD_CLEAN_USERNAME'] = USERNAME_CLEANING[cleaning.lower()]
        except KeyError:
            raise ImproperlyConfigured(
                f"AD_USERNAME_CLEANING must be one of: {', '.join(USERNAME_CLEANING)}."
            ) from None

    # REST API: keys given here are merged over the defaults
    rest = env.get('REST_FRAMEWORK', parse_json)
    if rest is not None:
        g['REST_FRAMEWORK'] = {**g['REST_FRAMEWORK'], **rest}
