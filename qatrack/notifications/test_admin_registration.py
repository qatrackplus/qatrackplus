"""Every notification admin module must be imported, or its page does not exist.

`qatrack/notifications/admin/__init__.py` exists only for its side effects: each
`import` runs a module whose bottom line calls `admin.site.register(...)`. Nothing
reads the names, which is why the file carries `# ruff: noqa: F401` - and why a
dropped line is invisible to both the linter and the application.

`qatrack.notifications.service_log_scheduling.admin` was dropped by `77f7a343`
(2025-07-11), a `make yapf` PEP8 pass. The module still existed and still ended in
`admin.site.register([ServiceEventSchedulingNotice], ...)`, but nothing imported
it, so that line never ran: Service Event Scheduling Notices had no admin page for
over a year and nobody could create one. The documentation at
`notifications/guide.rst:361-419` described a page that was not there.

**Why the existing tests did not catch it.** `service_log_scheduling/test_sls.py`
imports that admin module *directly* and exercises the admin class, so the class
was well covered. Importing it directly is exactly what hides the bug: the test
makes the registration happen itself, so it cannot notice that nothing else does.
These tests go through `qatrack.notifications.admin` and the real
`admin.site` registry instead.

This is the same shape as the bug in `test_apps.py` - a reference by name that
nothing resolves until something tries to use it - so it is guarded the same way:
assert the invariant over whatever is on disk, not over a copy of the list.
"""

import pathlib

from django.contrib import admin as django_admin
from django.test import SimpleTestCase

import qatrack.notifications.admin  # noqa: F401  (registers the admin pages)
from qatrack.notifications.models import ServiceEventSchedulingNotice


def _packages_with_an_admin_module():
    """Every `qatrack/notifications/<name>/admin.py` on disk."""
    root = pathlib.Path(qatrack.notifications.__file__).parent
    return sorted(
        p.parent.name
        for p in root.glob('*/admin.py')
    )


class TestEveryAdminModuleIsImported(SimpleTestCase):

    def test_packages_were_found_at_all(self):
        """Guard the guard: a layout change must not make this file vacuous."""
        found = _packages_with_an_admin_module()
        assert found, (
            'no qatrack/notifications/*/admin.py found - if the admin modules have '
            'moved, move this test with them rather than deleting it'
        )

    def test_no_admin_module_is_left_unimported(self):
        source = pathlib.Path(qatrack.notifications.admin.__file__).read_text(encoding='utf-8')
        missing = [
            name for name in _packages_with_an_admin_module()
            if 'qatrack.notifications.%s.admin' % name not in source
        ]
        assert not missing, (
            'these packages have an admin.py that qatrack/notifications/admin/__init__.py '
            'never imports, so their admin pages do not exist: %r' % missing
        )


class TestSchedulingNoticeHasAnAdminPage(SimpleTestCase):
    """The specific regression, named so a failure says what broke."""

    def test_the_notice_model_is_registered(self):
        assert ServiceEventSchedulingNotice in django_admin.site._registry, (
            'ServiceEventSchedulingNotice is not registered with the admin site, so '
            'there is no page on which to create a Service Event Scheduling Notice'
        )
