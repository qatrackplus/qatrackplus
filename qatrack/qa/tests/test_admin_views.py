from django.conf import settings
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils.translation import gettext as _

from qatrack.qa import models
from qatrack.qa.tests import utils


class TestListAdminViewsTest(TestCase):
    """Tests for TestList admin views"""

    def setUp(self):
        self.user = utils.create_user(is_superuser=True)
        self.client.force_login(self.user)
        self.test_list = utils.create_test_list()
        self.test = utils.create_test()
        utils.create_test_list_membership(self.test_list, self.test)

    def test_changelist_view_contains_export_import_buttons(self):
        """Test that the changelist view contains export and import buttons"""
        response = self.client.get(reverse('admin:qa_testlist_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('admin:qa_export_testpack'))
        self.assertContains(response, reverse('admin:qa_import_testpack'))
        self.assertContains(response, _("Export Test Pack"))
        self.assertContains(response, _("Import Test Pack"))

    def test_export_testpack_view_requires_permission(self):
        """Test that export testpack view requires proper permission"""
        # Remove superuser status and permissions
        self.user.is_superuser = False
        self.user.save()
        response = self.client.get(reverse('admin:qa_export_testpack'))
        self.assertEqual(response.status_code, 403)

        # Add permission
        perm = Permission.objects.get(codename='change_testlist')
        self.user.user_permissions.add(perm)
        response = self.client.get(reverse('admin:qa_export_testpack'))
        self.assertEqual(response.status_code, 200)

    def test_import_testpack_view_requires_permission(self):
        """Test that import testpack view requires proper permission"""
        # Remove superuser status and permissions
        self.user.is_superuser = False
        self.user.save()
        response = self.client.get(reverse('admin:qa_import_testpack'))
        self.assertEqual(response.status_code, 403)

        # Add permission
        perm = Permission.objects.get(codename='change_testlist')
        self.user.user_permissions.add(perm)
        response = self.client.get(reverse('admin:qa_import_testpack'))
        self.assertEqual(response.status_code, 200)

    def test_export_testpack_view_renders_correctly(self):
        """Test that export testpack view renders correctly"""
        response = self.client.get(reverse('admin:qa_export_testpack'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/qa/testpack/export.html')
        self.assertContains(response, self.test_list.name)
        self.assertContains(response, self.test.name)

    def test_import_testpack_view_renders_correctly(self):
        """Test that import testpack view renders correctly"""
        response = self.client.get(reverse('admin:qa_import_testpack'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/qa/testpack/import.html')

    def test_export_import_integration(self):
        """Test that export and import work together"""
        # First export
        response = self.client.post(
            reverse('admin:qa_export_testpack'), {
                'name': 'test-export',
                'description': 'Test export',
                'testlists': str(self.test_list.id),
                'testlistcycles': '',
                'tests': '',
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=test-export.tpk')

        # Delete the test list and test
        models.TestList.objects.all().delete()
        models.Test.objects.all().delete()

        # Now import
        testpack_data = response.content.decode('utf-8')
        response = self.client.post(
            reverse('admin:qa_import_testpack'),
            {
                'testpack_data': testpack_data,
                'testlists': '[["' + self.test_list.slug + '"]]',  # Natural key format
                'testlistcycles': '[]',
                'tests': '[]',
            }
        )
        self.assertEqual(response.status_code, 302)  # Redirect on success

        # Verify the test list and test were imported
        self.assertTrue(models.TestList.objects.filter(slug=self.test_list.slug).exists())
        self.assertTrue(models.Test.objects.filter(slug=self.test.slug).exists())


class TestListMembershipLabelTest(TestCase):
    """The test name shown beside the raw id field in the Test List admin.

    The field itself holds a test's id. Its name is fetched over AJAX from
    dynamic_raw_id's label view, which QATrack+ mounts under `admin/`.

    Since Django 3.2 the admin site ends its own urlconf with a catch-all
    (`AdminSite.final_catch_all_view`), so anything under `admin/` that the
    admin does not recognise raises Http404 there rather than falling through to
    later patterns. With the mount listed after `admin.site.urls` the label view
    was unreachable, and a Test List's memberships showed an id and a macro name
    - which are rendered server-side - with no test name at all.
    """

    label_url_name = 'dynamic_raw_id:dynamic_raw_id_label'

    def setUp(self):
        self.user = utils.create_user(is_superuser=True)
        self.client.force_login(self.user)

    def label_url(self, model_name):
        return reverse(
            self.label_url_name, kwargs={'app_name': 'qa', 'model_name': model_name}
        )

    def test_the_label_url_is_not_shadowed_by_the_admin_catch_all(self):
        """Asserted on the resolver, because the symptom is a plain 404.

        A 404 from the admin's catch-all and a 404 from a missing object look
        identical to the caller, so this names which view answered.
        """
        match = resolve(self.label_url('test'))
        self.assertEqual(
            match.func.__module__,
            'dynamic_raw_id.views',
            "%s answered instead - the admin catch-all is shadowing the mount" % (
                match.func.__module__,
            ),
        )

    def test_the_label_view_returns_the_test_name(self):
        test = utils.create_test(name="Output Constancy")
        response = self.client.get(self.label_url('test'), {'id': test.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Output Constancy")
        self.assertContains(response, reverse('admin:qa_test_change', args=[test.pk]))

    def test_the_label_view_returns_a_sublists_test_list_name(self):
        """The Sublist inline uses the same mechanism for its child test list."""
        test_list = utils.create_test_list(name="Daily Linac QC")
        response = self.client.get(self.label_url('testlist'), {'id': test_list.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Daily Linac QC")

    def test_the_label_view_still_requires_a_staff_user(self):
        """Moving the mount out from under `admin/` must not open it up.

        The view brings its own `is_staff` test, so this holds either way - but
        the admin's position in the urlconf used to be the only reason a request
        was refused at all, so the refusal is worth attributing. Asserted on the
        redirect target: the admin sends a non-staff user to its own login page,
        and the label view sends them to LOGIN_URL.
        """
        self.user.is_staff = False
        self.user.is_superuser = False
        self.user.save()
        test = utils.create_test(name="Output Constancy")
        response = self.client.get(self.label_url('test'), {'id': test.pk})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.url.startswith(settings.LOGIN_URL),
            "redirected to %s, so something other than the label view refused it"
            % response.url,
        )


class TestRawIdWrapperIconTest(TestCase):
    """The view and change icons beside a raw id field in the admin.

    `RelatedFieldWidgetWrapper` renders them with a `data-href-template` and no
    `href`, and Django fills the href in from `updateRelatedObjectLinks`, which
    it wires to `select` elements alone. A dynamic_raw_id field is a text input,
    so the eye and the pencil appeared beside it and did nothing.
    """

    def setUp(self):
        self.user = utils.create_user(is_superuser=True)
        self.client.force_login(self.user)

    def test_a_raw_id_field_still_renders_the_icons_without_an_href(self):
        """The premise, asserted rather than assumed.

        If Django ever starts filling these in itself, this fails and the script
        below can go.
        """
        test_list = utils.create_test_list()
        utils.create_test_list_membership(test_list, utils.create_test())
        response = self.client.get(
            reverse('admin:qa_testlist_change', args=[test_list.pk])
        )
        self.assertContains(response, 'related-widget-wrapper-link view-related')
        self.assertContains(response, 'data-href-template')

    def test_the_change_form_asks_django_to_fill_the_icons_in(self):
        test_list = utils.create_test_list()
        utils.create_test_list_membership(test_list, utils.create_test())
        response = self.client.get(
            reverse('admin:qa_testlist_change', args=[test_list.pk])
        )
        self.assertContains(response, 'updateRelatedObjectLinks')
        self.assertContains(response, 'vForeignKeyRawIdAdminField')

    def test_the_change_form_prints_no_template_comment(self):
        """Django's `{# #}` cannot span lines, and a multi-line one is printed.

        The first version of the script above explained itself in a seven-line
        `{# ... #}`. That is not a comment: the engine rendered it as text, below
        the Save buttons of **every** admin add and change page, because this
        template is the one they all extend. crane found it in a browser on
        Windows; nothing here would have failed.

        Asserted on the delimiter rather than on the wording, so it holds for
        whatever the next comment says. `{% comment %}` leaves no trace, and the
        `{# ... #}` one-liners elsewhere in this file are consumed normally.
        """
        test_list = utils.create_test_list()
        utils.create_test_list_membership(test_list, utils.create_test())
        for url in (
            reverse('admin:qa_testlist_change', args=[test_list.pk]),
            reverse('admin:qa_testlist_add'),
            reverse('admin:auth_user_change', args=[self.user.pk]),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertNotContains(
                response,
                '{#',
                msg_prefix=(
                    "%s renders a template comment as text - a multi-line "
                    "{# #} is not a comment, use {%% comment %%}" % url
                ),
            )
