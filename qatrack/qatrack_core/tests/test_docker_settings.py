"""qatrack/docker_settings.py turns deploy/docker/.env into settings.

apply() is called with a fake environment and a copy of the defaults it reads,
so these tests never touch the real settings or environment.
"""
import ast
import contextlib
import datetime
import io
import os
import re
import sys
import tempfile
from pathlib import Path, PureWindowsPath
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from qatrack import docker_settings

REPO_ROOT = Path(__file__).resolve().parents[3]


def defaults():
    return {
        'TIME_ZONE': 'America/Toronto',
        'ADMINS': (('Admin Name', 'YOUR_EMAIL_ADDRESS_GOES_HERE'),),
        'MANAGERS': (('Admin Name', 'YOUR_EMAIL_ADDRESS_GOES_HERE'),),
        'DEBUG': False,
        'USE_SQL_REPORTS': False,
        'HTTP_OR_HTTPS': 'http',
        'SESSION_COOKIE_SECURE': False,
        'CSRF_COOKIE_SECURE': False,
        'EMAIL_PORT': 587,
        'DEFAULT_AVAILABLE_TIMES': {
            f'hours_{day}': datetime.timedelta(hours=0 if day in ('sunday', 'saturday') else 8)
            for day in docker_settings.WEEKDAYS
        },
        'AD_DNS_NAME': '',
        'AD_LDAP_PORT': 389,
        'AD_LU_ACCOUNT_NAME': 'sAMAccountName',
        'AD_LU_MAIL': 'mail',
        'AD_LU_SURNAME': 'sn',
        'AD_LU_GIVEN_NAME': 'givenName',
        'AD_LU_MEMBER_OF': 'memberOf',
        'AD_CLEAN_USERNAME': None,
        'REST_FRAMEWORK': {'PAGE_SIZE': 50, 'DEFAULT_VERSION': 'v1'},
    }


class DockerSettingsTestCase(SimpleTestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.key_file = Path(self.tmp.name, 'user-data', 'secret_key.txt')

    def apply(self, **environ):
        environ.setdefault('QATRACK_SECRET_KEY_FILE', str(self.key_file))
        g = defaults()
        docker_settings.apply(g, environ)
        return g


class TestDefaults(DockerSettingsTestCase):

    def test_unset_and_empty_variables_keep_defaults(self):
        for value in (None, '', '   '):
            environ = {} if value is None else {'DEBUG': value, 'EMAIL_PORT': value, 'ADMINS': value}
            g = self.apply(**environ)
            self.assertIs(g['DEBUG'], False)
            self.assertEqual(g['EMAIL_PORT'], 587)
            self.assertEqual(g['ADMINS'], defaults()['ADMINS'])

    def test_database_defaults_match_compose(self):
        db = self.apply()['DATABASES']['default']
        self.assertEqual(db['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual((db['NAME'], db['USER'], db['PASSWORD']), ('qatrackplus', 'postgres', 'postgres'))
        self.assertEqual((db['HOST'], db['PORT']), ('postgres', 5432))

    def test_time_zone_from_environment(self):
        self.assertEqual(self.apply(TIME_ZONE='Asia/Kolkata')['TIME_ZONE'], 'Asia/Kolkata')
        # Empty counts as unset, as it does for the backup service's ${TIME_ZONE:-...}.
        for value in ('', '   '):
            self.assertEqual(self.apply(TIME_ZONE=value)['TIME_ZONE'], 'America/Toronto')

    def test_backup_time_zone_default_matches_settings(self):
        """With TIME_ZONE unset, the backup service runs in QATrack+'s default zone.

        compose.yaml gives the backup service TZ from TIME_ZONE, falling back to a
        default of its own, which must stay the same as settings.py's, or the
        nightly backup's 4 AM and its file names drift from QATrack+'s clock.
        """
        settings_py = ast.parse((REPO_ROOT / 'qatrack' / 'settings.py').read_text(encoding='utf-8'))
        settings_default = [
            node.value.value for node in settings_py.body
            if isinstance(node, ast.Assign) and [getattr(t, 'id', None) for t in node.targets] == ['TIME_ZONE']
        ]
        compose = (REPO_ROOT / 'deploy' / 'docker' / 'compose.yaml').read_text(encoding='utf-8')
        compose_default = re.findall(r'^ +TZ: \$\{TIME_ZONE:-([^}]+)\}$', compose, re.MULTILINE)
        # start-cron.sh warns when the backups' zone differs from QATrack+'s default.
        start_cron = (REPO_ROOT / 'deploy' / 'docker' / 'backup' / 'start-cron.sh').read_text(encoding='utf-8')
        start_cron_default = re.findall(r'^default_zone=(\S+)$', start_cron, re.MULTILINE)
        self.assertEqual(len(settings_default), 1)
        self.assertEqual(compose_default, settings_default)
        self.assertEqual(start_cron_default, settings_default)

    def test_database_from_environment(self):
        g = self.apply(
            POSTGRES_DB='qa', POSTGRES_USER='u', POSTGRES_PASSWORD='p', POSTGRES_HOST='db', POSTGRES_PORT='6543'
        )
        db = g['DATABASES']['default']
        self.assertEqual((db['NAME'], db['USER'], db['PASSWORD'], db['HOST'], db['PORT']), ('qa', 'u', 'p', 'db', 6543))
        self.assertNotIn('readonly', g['DATABASES'])

    def test_sql_reports_adds_readonly_alias(self):
        g = self.apply(USE_SQL_REPORTS='true')
        self.assertIs(g['DATABASES']['readonly'], g['DATABASES']['default'])


class TestParsing(DockerSettingsTestCase):

    def test_booleans(self):
        for value in ('1', 'true', 'True', 'YES', 'on'):
            self.assertIs(self.apply(DEBUG=value)['DEBUG'], True, value)
        for value in ('0', 'false', 'No', 'OFF'):
            self.assertIs(self.apply(DEBUG=value)['DEBUG'], False, value)

    def test_invalid_value_names_the_variable(self):
        cases = {'DEBUG': 'maybe', 'EMAIL_PORT': 'smtp', 'ADMINS': '[not json', 'POSTGRES_PORT': 'x'}
        for name, value in cases.items():
            with self.assertRaisesRegex(ImproperlyConfigured, name):
                self.apply(**{name: value})

    def test_admins_json_also_sets_managers(self):
        g = self.apply(ADMINS='[["Jane Physicist", "jane@example.com"]]')
        self.assertEqual(g['ADMINS'], [['Jane Physicist', 'jane@example.com']])
        self.assertEqual(g['MANAGERS'], g['ADMINS'])

    def test_available_hours(self):
        g = self.apply(DEFAULT_AVAILABLE_HOURS_SATURDAY='4', DEFAULT_AVAILABLE_HOURS_MONDAY='7.5')
        self.assertEqual(g['DEFAULT_AVAILABLE_TIMES']['hours_saturday'], datetime.timedelta(hours=4))
        self.assertEqual(g['DEFAULT_AVAILABLE_TIMES']['hours_monday'], datetime.timedelta(hours=7.5))
        self.assertEqual(g['DEFAULT_AVAILABLE_TIMES']['hours_tuesday'], datetime.timedelta(hours=8))

    def test_rest_framework_is_merged(self):
        g = self.apply(REST_FRAMEWORK='{"PAGE_SIZE": 10}')
        self.assertEqual(g['REST_FRAMEWORK'], {'PAGE_SIZE': 10, 'DEFAULT_VERSION': 'v1'})


class TestHosts(DockerSettingsTestCase):

    def test_internal_hosts_are_allowed_but_not_trusted_origins(self):
        g = self.apply(ALLOWED_HOSTS='qatrack.clinic.ca, 10.0.0.5')
        self.assertEqual(g['ALLOWED_HOSTS'], ['qatrack.clinic.ca', '10.0.0.5', 'localhost', '127.0.0.1'])
        self.assertEqual(
            g['CSRF_TRUSTED_ORIGINS'],
            ['http://qatrack.clinic.ca', 'https://qatrack.clinic.ca', 'http://10.0.0.5', 'https://10.0.0.5'],
        )

    def test_wildcard_is_not_a_trusted_origin(self):
        g = self.apply(ALLOWED_HOSTS='*')
        self.assertIn('*', g['ALLOWED_HOSTS'])
        self.assertEqual(g['CSRF_TRUSTED_ORIGINS'], [])

    def test_explicit_trusted_origins(self):
        g = self.apply(ALLOWED_HOSTS='qatrack.clinic.ca', CSRF_TRUSTED_ORIGINS='https://qatrack.clinic.ca')
        self.assertEqual(g['CSRF_TRUSTED_ORIGINS'], ['https://qatrack.clinic.ca'])

    def test_default_hosts_unchanged_for_old_env_files(self):
        self.assertEqual(self.apply()['ALLOWED_HOSTS'], ['localhost', '127.0.0.1'])


class TestHttps(DockerSettingsTestCase):

    def test_https_trusts_proxy_header_and_secures_cookies(self):
        g = self.apply(HTTP_OR_HTTPS='https')
        self.assertEqual(g['SECURE_PROXY_SSL_HEADER'], ('HTTP_X_FORWARDED_PROTO', 'https'))
        self.assertIs(g['SESSION_COOKIE_SECURE'], True)
        self.assertIs(g['CSRF_COOKIE_SECURE'], True)

    def test_http_leaves_cookies_and_proxy_header_alone(self):
        g = self.apply(HTTP_OR_HTTPS='http')
        self.assertNotIn('SECURE_PROXY_SSL_HEADER', g)
        self.assertIs(g['SESSION_COOKIE_SECURE'], False)

    def test_cookie_settings_can_be_overridden(self):
        g = self.apply(HTTP_OR_HTTPS='https', SESSION_COOKIE_SECURE='false')
        self.assertIs(g['SESSION_COOKIE_SECURE'], False)

    def test_invalid_protocol(self):
        with self.assertRaisesRegex(ImproperlyConfigured, 'HTTP_OR_HTTPS'):
            self.apply(HTTP_OR_HTTPS='ftp')


class TestSecretKey(DockerSettingsTestCase):

    def test_environment_variable_wins(self):
        g = self.apply(SECRET_KEY='from-env')
        self.assertEqual(g['SECRET_KEY'], 'from-env')
        self.assertFalse(self.key_file.exists())

    def test_generated_once_then_reused(self):
        first = self.apply()['SECRET_KEY']
        self.assertTrue(self.key_file.exists())
        self.assertGreaterEqual(len(first), 50)
        self.assertEqual(self.apply()['SECRET_KEY'], first)

    def test_generated_file_is_private(self):
        if sys.platform == 'win32':
            self.skipTest("POSIX file modes")
        self.apply()
        self.assertEqual(os.stat(self.key_file).st_mode & 0o777, 0o600)

    def test_leaves_no_temporary_files(self):
        self.apply()
        self.assertEqual(os.listdir(self.key_file.parent), ['secret_key.txt'])

    def test_key_file_has_one_name(self):
        # The key is linked into place from a temporary file, which is then
        # removed. The Docker init service never re-owns a file with more than
        # one name (a hard link), so a second name left behind would leave the
        # key as it is on every start.
        self.apply()
        self.assertEqual(os.stat(self.key_file).st_nlink, 1)

    def test_key_published_by_another_process_first_is_used(self):
        # Another container process publishes its key between our check for the
        # file and our link: both must end up with the same key.
        real_link = os.link

        def other_process_wins(src, dst):
            Path(dst).write_text('published-first', encoding='utf-8')
            return real_link(src, dst)

        with mock.patch.object(docker_settings.os, 'link', side_effect=other_process_wins):
            g = self.apply()
        self.assertEqual(g['SECRET_KEY'], 'published-first')
        self.assertEqual(self.key_file.read_text(encoding='utf-8'), 'published-first')
        self.assertEqual(os.listdir(self.key_file.parent), ['secret_key.txt'])

    def test_empty_file_is_an_error(self):
        self.key_file.parent.mkdir(parents=True)
        self.key_file.write_text('  \n')
        with self.assertRaisesRegex(ImproperlyConfigured, 'empty'):
            self.apply()

    def test_unwritable_folder_is_a_clear_error(self):
        blocker = Path(self.tmp.name, 'not-a-folder')
        blocker.write_text('')
        with self.assertRaisesRegex(ImproperlyConfigured, 'SECRET_KEY'):
            self.apply(QATRACK_SECRET_KEY_FILE=str(blocker / 'secret_key.txt'))


class TestSecretKeyNotice(DockerSettingsTestCase):
    """The notice the entrypoint prints when the key is kept in a file, not in .env."""

    def notice(self, **environ):
        environ.setdefault('QATRACK_SECRET_KEY_FILE', str(self.key_file))
        return docker_settings.secret_key_notice(environ)

    def test_generated_key_names_its_file_and_how_to_keep_it(self):
        key = self.apply()['SECRET_KEY']
        notice = self.notice()
        self.assertIn(self.key_file.as_posix(), notice)
        self.assertIn('backup', notice)
        self.assertIn(
            f'printf \'\\nSECRET_KEY=%s\\n\' "$(docker compose exec -T django cat {self.key_file.as_posix()})" >> .env',
            notice,
        )
        self.assertNotIn(key, notice)

    def test_key_read_back_from_the_file_is_never_shown(self):
        self.key_file.parent.mkdir(parents=True)
        self.key_file.write_text('kept-in-the-volume', encoding='utf-8')
        self.assertEqual(self.apply()['SECRET_KEY'], 'kept-in-the-volume')
        self.assertNotIn('kept-in-the-volume', self.notice())

    def test_no_notice_when_set_in_env(self):
        self.assertIsNone(self.notice(SECRET_KEY='from-env'))

    def test_blank_secret_key_counts_as_unset(self):
        self.assertIsNotNone(self.notice(SECRET_KEY='   '))

    def test_default_file_is_named_as_the_volume(self):
        notice = docker_settings.secret_key_notice({})
        self.assertIn(docker_settings.DEFAULT_SECRET_KEY_FILE, notice)
        self.assertIn('user-data-volume', notice)
        self.assertIn(f'cat {docker_settings.DEFAULT_SECRET_KEY_FILE})', notice)

    def test_default_file_in_a_folder_on_the_server(self):
        # QATRACK_USER_DATA_DIR in .env puts the default file in a folder on the
        # server instead of the volume; the notice names that folder.
        notice = docker_settings.secret_key_notice({'QATRACK_USER_DATA_DIR': '/srv/qatrack/user-data'})
        self.assertIn(f'{docker_settings.DEFAULT_SECRET_KEY_FILE}, in the folder /srv/qatrack/user-data', notice)
        self.assertNotIn('user-data-volume', notice)
        self.assertIn(f'cat {docker_settings.DEFAULT_SECRET_KEY_FILE})', notice)

    def test_blank_user_data_dir_means_the_volume(self):
        notice = docker_settings.secret_key_notice({'QATRACK_USER_DATA_DIR': '  '})
        self.assertIn('user-data-volume', notice)

    def test_default_file_keeps_forward_slashes_on_windows(self):
        # On Windows, Path renders /usr/src/... with backslashes; the file is in
        # the Linux container, so the notice must not.
        with mock.patch.object(docker_settings, 'Path', PureWindowsPath):
            notice = docker_settings.secret_key_notice({})
        self.assertIn(docker_settings.DEFAULT_SECRET_KEY_FILE, notice)
        self.assertIn('user-data-volume', notice)
        self.assertNotIn('\\usr', notice)

    def test_notice_does_not_create_the_file(self):
        self.notice()
        self.assertFalse(self.key_file.exists())

    def test_settings_stay_quiet(self):
        # Every process imports the settings; only the entrypoint prints the notice.
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), self.assertNoLogs(level='DEBUG'):
            self.apply()
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))


class TestActiveDirectory(DockerSettingsTestCase):

    def test_ldap_url_built_from_parts(self):
        g = self.apply(AD_DNS_NAME='ad.clinic.ca', AD_LDAP_PORT='636', AD_LDAP_PROTOCOL='ldaps')
        self.assertEqual(g['AD_LDAP_URL'], 'ldaps://ad.clinic.ca:636')

    def test_explicit_ldap_url_wins(self):
        g = self.apply(AD_DNS_NAME='ad.clinic.ca', AD_LDAP_URL='ldaps://other:3269')
        self.assertEqual(g['AD_LDAP_URL'], 'ldaps://other:3269')

    def test_invalid_ldap_protocol(self):
        with self.assertRaisesRegex(ImproperlyConfigured, 'AD_LDAP_PROTOCOL'):
            self.apply(AD_LDAP_PROTOCOL='http')

    def test_search_fields_follow_lookup_names(self):
        g = self.apply(AD_LU_MAIL='email')
        self.assertEqual(g['AD_SEARCH_FIELDS'], ['email', 'sn', 'givenName', 'sAMAccountName', 'memberOf'])

    def test_username_cleaning_unset_leaves_default(self):
        self.assertIsNone(self.apply()['AD_CLEAN_USERNAME'])

    def test_username_cleaning_modes(self):
        cases = {
            'none': ('HOSP\\JDoe', 'HOSP\\JDoe'),
            'lower': ('HOSP\\JDoe', 'hosp\\jdoe'),
            'strip_domain': ('HOSP\\JDoe', 'JDoe'),
            'lower_strip_domain': ('HOSP\\JDoe', 'jdoe'),
            'strip_upn': ('JDoe@hosp.ca', 'JDoe'),
            'lower_strip_upn': ('JDoe@hosp.ca', 'jdoe'),
        }
        for mode, (username, expected) in cases.items():
            clean = self.apply(AD_USERNAME_CLEANING=mode)['AD_CLEAN_USERNAME']
            self.assertEqual(clean(username), expected, mode)

    def test_unknown_username_cleaning(self):
        with self.assertRaisesRegex(ImproperlyConfigured, 'AD_USERNAME_CLEANING'):
            self.apply(AD_USERNAME_CLEANING='upper')
