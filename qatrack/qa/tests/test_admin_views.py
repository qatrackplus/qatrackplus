from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
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
