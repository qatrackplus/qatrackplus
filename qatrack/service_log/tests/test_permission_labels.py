"""`view_serviceevent` and `review_serviceevent` must not read the same.

Both were declared with the text "Can review service event", so the admin's
permission list showed two identical rows for two different rights. An
administrator granting "view" was choosing by position - and the account that
makes this concrete is a service technician who may raise service events but not
review them, which is precisely the distinction the two permissions draw.
"""

from importlib import import_module

from django.apps import apps
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase

from qatrack.accounts.tests.utils import create_user
from qatrack.service_log import forms, models
from qatrack.service_log.tests import utils as sl_utils

MIGRATION = 'qatrack.service_log.migrations.0029_v4_0_2_final'


class _SchemaEditor:
    """The one attribute a data migration reads from a schema editor: the alias.

    The migration's `RunPython` functions take the database to write to from
    `schema_editor.connection.alias`, as a data migration must - so these tests
    hand them something that carries one, rather than the `None` they used to
    pass. Not a real schema editor, because none of this issues DDL and opening
    one inside a `TestCase` would need the atomic block these tests rely on.

    What it does not prove: that a *second* alias is honoured. The suite
    configures one database, so the routing itself is unverified here - this
    asserts only that the alias is read from the editor and used.
    """

    connection = connection


class TestServiceEventPermissionLabels(TestCase):

    def permission(self, codename):
        return Permission.objects.get(
            content_type__app_label='service_log', codename=codename)

    def test_view_and_review_read_differently(self):
        view = self.permission('view_serviceevent')
        review = self.permission('review_serviceevent')
        assert view.name == 'Can view service event', view.name
        assert review.name == 'Can review service event', review.name
        assert view.name != review.name

    def test_the_data_migration_renames_an_upgraded_row(self):
        """A fresh database gets the right text from Meta; an upgrade needs the RunPython.

        `create_permissions` only creates permissions that are missing - it
        compares on (content_type, codename) and never updates `name` - so
        without the data migration a site upgrading from 4.0.x would keep the old
        wording however many times it migrated. This reproduces that row and runs
        the migration's own function against it.
        """
        migration = import_module(MIGRATION)

        view = self.permission('view_serviceevent')
        view.name = migration.OLD
        view.save()
        assert self.permission('view_serviceevent').name == migration.OLD

        migration.rename_view_serviceevent(apps, _SchemaEditor())
        assert self.permission('view_serviceevent').name == migration.NEW

        # Reversible, as the migration claims by supplying `backwards`.
        migration.restore_view_serviceevent_label(apps, _SchemaEditor())
        assert self.permission('view_serviceevent').name == migration.OLD

    def test_the_rename_leaves_a_hand_corrected_site_alone(self):
        """Scoped to the stale text, so it cannot overwrite a site's own wording."""
        migration = import_module(MIGRATION)

        view = self.permission('view_serviceevent')
        view.name = 'Can look at service events'
        view.save()

        migration.rename_view_serviceevent(apps, _SchemaEditor())
        assert self.permission('view_serviceevent').name == 'Can look at service events'


class TestReviewGatesTheServiceStatus(TestCase):
    """Reviewing includes setting the status, which is what distinguishes the two rights.

    Tested through the form's queryset rather than by reading the view's source:
    it is a ModelChoiceField, so the queryset is what is enforced on submit.
    """

    def setUp(self):
        self.needs_review = sl_utils.create_service_event_status(
            name="Needs review", is_review_required=True)
        self.reviewed = sl_utils.create_service_event_status(
            name="Reviewed", is_review_required=False)

    def statuses_offered(self, user):
        form = forms.ServiceEventForm(user=user)
        return set(form.fields['service_status'].queryset.values_list('pk', flat=True))

    def test_a_reviewer_may_choose_any_status(self):
        # is_superuser=False, or has_perm() answers True for everything and
        # both tests below pass without the gate doing anything.
        user = create_user(uname="reviewer", is_superuser=False, is_staff=False)
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label='service_log',
                                   codename='review_serviceevent'))
        user = type(user).objects.get(pk=user.pk)

        offered = self.statuses_offered(user)
        assert self.reviewed.pk in offered
        assert self.needs_review.pk in offered

    def test_a_technician_may_not_choose_a_reviewed_status(self):
        user = create_user(uname="technician", is_superuser=False, is_staff=False)
        for codename in ('view_serviceevent', 'add_serviceevent'):
            user.user_permissions.add(
                Permission.objects.get(content_type__app_label='service_log',
                                       codename=codename))
        user = type(user).objects.get(pk=user.pk)

        offered = self.statuses_offered(user)
        assert self.needs_review.pk in offered
        assert self.reviewed.pk not in offered, (
            "a user without review_serviceevent was offered a status that closes review")

    def test_all_statuses_exist_so_the_test_above_is_not_vacuous(self):
        assert models.ServiceEventStatus.objects.count() >= 2
