"""
S48: `Site.domain` holding something that is not a bare host.

Django documents the field as a fully qualified domain name and does not
validate it. QATrack+ interpolates it into every absolute link it generates, so
a wrong value produces links that are well formed and point somewhere else -
nothing raises, nothing is logged, and the only symptom is a link that did not
go where the user expected. A value also survives a restore from another
deployment, which is the likeliest way a wrong one arrives.

The path case is the one worth naming: `<host>/<appname>` looks like a
reasonable way to say "served under /<appname>", but `FORCE_SCRIPT_NAME` is the
setting for that, and putting the prefix in the domain bypasses it while
corrupting the host too.
"""

from django.contrib.sites.models import Site
from django.test import TestCase

from qatrack.qatrack_core.checks import check_site_domain

DATABASES = ['default']


def run_check():
    return check_site_domain(app_configs=None, databases=DATABASES)


def ids(warnings):
    return sorted(w.id for w in warnings)


class TestGoodDomainsAreQuiet(TestCase):

    def test_a_bare_host_produces_nothing(self):
        Site.objects.all().update(domain='qatrack.example.com', name='QATrack+')
        assert run_check() == []

    def test_a_host_with_a_port_is_accepted(self):
        """Not documented by Django, but it is a host:port authority, not a path."""

        Site.objects.all().update(domain='qatrack.example.com:8080')
        assert run_check() == []

    def test_a_bare_hostname_with_no_dots_is_accepted(self):
        """An intranet short name is a legitimate host."""

        Site.objects.all().update(domain='qatrack')
        assert run_check() == []


class TestTheReportedShape(TestCase):
    """`<host>/<appname>`, which is what S48 found in a live database."""

    def setUp(self):
        Site.objects.all().update(domain='shorthost/qatrack')
        self.warnings = run_check()

    def test_it_is_reported(self):
        assert ids(self.warnings) == ['qatrack.W006'], ids(self.warnings)

    def test_it_names_the_host_and_the_spurious_segment(self):
        message = self.warnings[0].msg
        assert "'shorthost'" in message, message
        assert "'/qatrack'" in message, message

    def test_it_points_at_force_script_name(self):
        """
        The hint has to say where the prefix belongs, or the obvious repair is to
        put it back in the domain.
        """

        assert 'FORCE_SCRIPT_NAME' in self.warnings[0].hint


class TestTheOtherMalformedShapes(TestCase):

    def test_a_scheme_is_reported(self):
        Site.objects.all().update(domain='https://qatrack.example.com')
        assert ids(run_check()) == ['qatrack.W005']

    def test_a_scheme_is_reported_once_not_twice(self):
        """
        A URL contains a slash, so a naive path test fires on it as well. One
        report per problem.
        """

        Site.objects.all().update(domain='https://qatrack.example.com/qatrack')
        assert ids(run_check()) == ['qatrack.W005']

    def test_whitespace_is_reported(self):
        Site.objects.all().update(domain=' qatrack.example.com ')
        assert ids(run_check()) == ['qatrack.W003']

    def test_an_empty_domain_is_reported(self):
        Site.objects.all().update(domain='')
        assert ids(run_check()) == ['qatrack.W004']

    def test_a_trailing_slash_alone_is_not_a_path(self):
        """`site_url` strips it already; reporting it would be noise."""

        Site.objects.all().update(domain='qatrack.example.com/')
        assert run_check() == []


class TestItIsSafeToRun(TestCase):

    def test_it_does_nothing_when_no_database_is_being_checked(self):
        """
        Registered under Tags.database, so it must no-op unless a database is in
        scope. Without this it would query on every management command.
        """

        Site.objects.all().update(domain='shorthost/qatrack')
        assert check_site_domain(app_configs=None, databases=None) == []
        assert check_site_domain(app_configs=None, databases=[]) == []

    def test_a_database_problem_is_not_re_raised(self):
        """
        This runs during `migrate`, and on a fresh install django_site is created
        by that very run - so the table may not exist when it is called.
        """

        from unittest import mock

        with mock.patch(
            'django.contrib.sites.models.Site.objects.values_list',
            side_effect=Exception('no such table: django_site'),
        ):
            assert run_check() == []

    def test_every_site_is_checked_not_only_the_current_one(self):
        Site.objects.all().update(domain='qatrack.example.com')
        Site.objects.create(domain='other/prefix', name='Other')
        assert ids(run_check()) == ['qatrack.W006']
