"""manage.py configure_site sets the Site record QATrack+ builds email and report links from."""
import subprocess
import sys
from io import StringIO

from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from qatrack.qatrack_core.management.commands.configure_site import first_public_host


class TestHostsModule(SimpleTestCase):

    def test_imports_without_django(self):
        # qatrack/settings.py loads qatrack_core.hosts (through docker_settings)
        # before Django is set up, so it must not import Django itself.
        code = (
            "import sys; import qatrack.qatrack_core.hosts; "
            "sys.exit(any(m == 'django' or m.startswith('django.') for m in sys.modules))"
        )
        self.assertEqual(subprocess.run([sys.executable, '-c', code]).returncode, 0)


class TestFirstPublicHost(SimpleTestCase):

    def test_skips_wildcards_and_internal_hosts(self):
        hosts = ['*', '.myclinic.ca', 'localhost', '127.0.0.1', 'qatrack.myclinic.ca', '10.0.0.5']
        self.assertEqual(first_public_host(hosts), 'qatrack.myclinic.ca')

    def test_none_when_nothing_usable(self):
        self.assertIsNone(first_public_host(['*', 'localhost', '127.0.0.1']))


class TestConfigureSite(TestCase):

    def setUp(self):
        Site.objects.clear_cache()
        self.site = Site.objects.get_current()
        self.site.domain = 'example.com'
        self.site.name = 'example.com'
        self.site.save()

    def run_command(self, **options):
        out = StringIO()
        call_command('configure_site', stdout=out, **options)
        # Read the database, not get_current(): that caches the object the
        # command edits, so it would show changes the command never saved.
        return Site.objects.get(pk=self.site.pk), out.getvalue()

    @override_settings(ALLOWED_HOSTS=['qatrack.myclinic.ca', 'localhost', '127.0.0.1'], SITE_NAME='QATrack+')
    def test_default_record_filled_from_allowed_hosts(self):
        site, _ = self.run_command()
        self.assertEqual(site.domain, 'qatrack.myclinic.ca')
        self.assertEqual(site.name, 'QATrack+')

    @override_settings(ALLOWED_HOSTS=['*', 'localhost', '127.0.0.1'])
    def test_default_record_with_no_usable_host_is_left_and_explained(self):
        site, out = self.run_command()
        self.assertEqual(site.domain, 'example.com')
        self.assertIn('SITE_DOMAIN', out)

    @override_settings(ALLOWED_HOSTS=['qatrack.myclinic.ca', 'localhost', '127.0.0.1'])
    def test_admin_changes_are_kept_without_explicit_values(self):
        self.site.domain = 'qa.hospital.org'
        self.site.name = 'Radiation Oncology QA'
        self.site.save()
        site, _ = self.run_command()
        self.assertEqual(site.domain, 'qa.hospital.org')
        self.assertEqual(site.name, 'Radiation Oncology QA')

    @override_settings(ALLOWED_HOSTS=['qatrack.myclinic.ca', 'localhost', '127.0.0.1'])
    def test_explicit_values_always_win(self):
        self.site.domain = 'qa.hospital.org'
        self.site.name = 'Old name'
        self.site.save()
        site, _ = self.run_command(domain='qatrack.example.org:8080/', name='Clinic QA')
        self.assertEqual(site.domain, 'qatrack.example.org:8080')
        self.assertEqual(site.name, 'Clinic QA')

    @override_settings(ALLOWED_HOSTS=['qatrack.myclinic.ca', 'localhost', '127.0.0.1'])
    def test_running_again_changes_nothing(self):
        self.run_command()
        _, out = self.run_command()
        self.assertEqual(out, '')
