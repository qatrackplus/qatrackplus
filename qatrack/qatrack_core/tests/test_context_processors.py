"""A cached value of the wrong type must cost one badge, not the whole site.

`get_sl_notification_total` sums three counts that come from the cache, and it runs
from a context processor - so it runs on **every page**. A string in one of those
keys made `int + str` raise, and a site-wide 500 is a disproportionate response to a
stale cache entry.

Measured on the public demo server on 2026-10-13: three tests failed this way during a
full-suite run, each one a page fetch, with the traceback ending in
`context_processors.py` rather than anywhere near the code under test.
"""

from unittest import mock

from django.contrib.auth.models import Permission, User
from django.test import RequestFactory, TestCase

# NOT imported at module level, deliberately. Importing `qatrack.context_processors`
# executes ten module-level `cache.delete(...)` calls, and the cache backend is the
# database - so the import is a database query. At collection time pytest-django
# refuses it with "Database access not allowed", and every test in the file errors
# before it runs.
#
# That is almost certainly why this module had no tests before: it cannot be imported
# from a test module's top level. The imports below happen inside tests, where
# database access is allowed.


def processors():
    """Import the module under test from inside a test, not at collection."""
    from qatrack import context_processors

    return context_processors


class TestAsCount(TestCase):

    def test_an_int_passes_through(self):
        assert processors().as_count(7, 'SOME_COUNT') == 7

    def test_zero_passes_through(self):
        assert processors().as_count(0, 'SOME_COUNT') == 0

    def test_a_string_becomes_zero(self):
        assert processors().as_count('kept', 'SOME_COUNT') == 0

    def test_none_becomes_zero(self):
        """A cache miss that was stored as None rather than recomputed."""
        assert processors().as_count(None, 'SOME_COUNT') == 0

    def test_a_bool_becomes_zero(self):
        """True is an int in Python and would sum as 1 - a plausible wrong count."""
        assert processors().as_count(True, 'SOME_COUNT') == 0
        assert processors().as_count(False, 'SOME_COUNT') == 0

    def test_a_float_becomes_zero(self):
        assert processors().as_count(3.5, 'SOME_COUNT') == 0

    def test_a_bad_value_is_logged_with_its_type_and_the_key(self):
        """A badge quietly reading 0 needs to be findable in the log."""
        with self.assertLogs('qatrack', level='WARNING') as caught:
            processors().as_count('kept', 'SE_NEEDING_REVIEW_COUNT')
        logged = '\n'.join(caught.output)
        assert 'SE_NEEDING_REVIEW_COUNT' in logged
        assert "'kept'" in logged
        assert 'str' in logged

    def test_a_good_value_is_not_logged(self):
        with mock.patch('qatrack.context_processors.logger') as log:
            processors().as_count(4, 'SOME_COUNT')
        log.warning.assert_not_called()


class TestNotificationTotal(TestCase):

    PERMS = {
        'review_serviceevent': 'service_log',
        'perform_returntoserviceqa': 'service_log',
        'can_review': 'qa',
    }

    def request_for(self, user):
        request = RequestFactory().get('/')
        request.user = user
        return request

    def user_with_all_three(self):
        user = User.objects.create_user('badges', 'b@e.com', 'pw')
        for codename, app_label in self.PERMS.items():
            user.user_permissions.add(
                Permission.objects.get(content_type__app_label=app_label, codename=codename))
        return User.objects.get(pk=user.pk)   # clear the permission cache

    def test_counts_are_summed_for_a_user_holding_every_permission(self):
        total = processors().get_sl_notification_total(self.request_for(self.user_with_all_three()), 1, 2, 4)
        assert total == 7

    def test_a_string_does_not_raise_and_drops_only_its_own_term(self):
        """The regression this exists for: previously `int + str`, on every page."""
        total = processors().get_sl_notification_total(self.request_for(self.user_with_all_three()), 1, 'kept', 4)
        assert total == 5

    def test_every_value_bad_gives_zero_rather_than_raising(self):
        total = processors().get_sl_notification_total(
            self.request_for(self.user_with_all_three()), 'a', None, True)
        assert total == 0

    def test_a_user_with_no_permissions_counts_nothing(self):
        user = User.objects.create_user('plain', 'p@e.com', 'pw')
        assert processors().get_sl_notification_total(self.request_for(user), 1, 2, 4) == 0

    def test_a_bad_value_is_ignored_for_a_user_who_cannot_see_it(self):
        """The bad value is behind a permission the user lacks, so it never matters."""
        user = User.objects.create_user('partial', 'q@e.com', 'pw')
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label='qa', codename='can_review'))
        user = User.objects.get(pk=user.pk)
        assert processors().get_sl_notification_total(self.request_for(user), 'kept', 'kept', 4) == 4

    def test_a_request_without_a_user_counts_nothing(self):
        """AnonymousUser is normal; no `user` attribute at all is not, and used to be
        evaluated once per permission rather than short-circuiting."""
        assert processors().get_sl_notification_total(RequestFactory().get('/'), 1, 2, 4) == 0
