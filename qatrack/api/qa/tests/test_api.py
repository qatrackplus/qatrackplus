import base64
import os

from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from qatrack.attachments.models import Attachment
from qatrack.qa import models
from qatrack.qa.tests import utils


class TestTestListInstanceAPI(APITestCase):

    def setUp(self):

        self.unit = utils.create_unit()
        self.simple_test_list = utils.create_test_list("simple")
        self.t1 = utils.create_test(name="test1")
        self.t2 = utils.create_test(name="test2")
        self.t3 = utils.create_test(name="test3", test_type=models.STRING)
        self.t4 = utils.create_test(name="test4", test_type=models.BOOLEAN)
        self.t5 = utils.create_test(name="test5", test_type=models.MULTIPLE_CHOICE, choices="choice1,choice2,choice3")

        self.tc = utils.create_test(name="testc", test_type=models.COMPOSITE)
        self.tc.calculation_procedure = "result = test1 + test2"
        self.tc.save()

        self.tsc = utils.create_test(name="testsc", test_type=models.STRING_COMPOSITE)
        self.tsc.calculation_procedure = "result = 'hello %s' % test3"
        self.tsc.save()
        self.default_tests = [self.t1, self.t2, self.t3, self.t4, self.t5]
        self.ntests = len(self.default_tests)

        for t in self.default_tests:
            utils.create_test_list_membership(self.simple_test_list, t)

        self.unit_test_list = utils.create_unit_test_collection(test_collection=self.simple_test_list, unit=self.unit)

        self.create_url = reverse('testlistinstance-list')
        self.utc_url = reverse("unittestcollection-detail", kwargs={'pk': self.unit_test_list.pk})

        self.simple_data = {
            'unit_test_collection': self.utc_url,
            'work_completed': '2019-07-25 10:49:47',
            'work_started': '2019-07-25 10:49:00',
            'tests': {
                'test1': {
                    'value': 1
                },
                'test2': {
                    'value': 2
                },
                'test3': {
                    'value': "test three"
                },
                'test4': {
                    'value': True
                },
                'test5': {
                    'value': "choice2"
                },
            },
        }

        self.client.login(username="user", password="password")
        self.status = utils.create_status()

    def tearDown(self):
        for a in Attachment.objects.all():
            if os.path.isfile(a.attachment.path):
                os.remove(a.attachment.path)

    def test_create_no_status(self):
        models.TestInstanceStatus.objects.all().delete()
        response = self.client.post(self.create_url, self.simple_data)
        assert response.data == ['No test instance status available']

    def test_create_user_status(self):
        s2 = utils.create_status(name="user status", slug="user_status", is_default=False, requires_review=False)
        s2_url = reverse("testinstancestatus-detail", kwargs={'pk': s2.pk})
        self.simple_data['status'] = s2_url
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestInstance.objects.filter(status=s2).count() == self.ntests
        assert models.TestListInstance.objects.all().count() == 1
        assert models.TestListInstance.objects.unreviewed().count() == 0

    def test_create_simple(self):
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.unreviewed().count() == 1
        assert models.TestInstance.objects.count() == self.ntests
        for t in self.default_tests:
            ti = models.TestInstance.objects.get(unit_test_info__test=t)
            v = ti.value if t.type not in models.STRING_TYPES else ti.string_value
            assert v == self.simple_data['tests'][t.slug]['value']

    def test_create_simple_with_txt_attachments(self):
        self.simple_data['attachments'] = [{'filename': 'test.txt', 'value': 'hello text', 'encoding': 'text'}]
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_201_CREATED
        tli = models.TestListInstance.objects.first()
        assert tli.attachment_set.count() == 1
        a = tli.attachment_set.first()
        assert a.finalized
        assert "uploads/testlistinstance" in a.attachment.path

    def test_create_simple_with_b64_attachments(self):
        f = open(os.path.join(settings.PROJECT_ROOT, "qa", "static", "qa", "img", "tux.png"), 'rb')
        b64 = base64.b64encode(f.read()).decode()
        self.simple_data['attachments'] = [{'filename': 'test.txt', 'value': b64, 'encoding': 'base64'}]
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_201_CREATED
        tli = models.TestListInstance.objects.first()
        assert tli.attachment_set.count() == 1
        a = tli.attachment_set.first()
        assert a.finalized
        assert "uploads/testlistinstance" in a.attachment.path

    def test_create_simple_with_b64_attachments_invalid(self):
        f = open(os.path.join(settings.PROJECT_ROOT, "qa", "static", "qa", "img", "tux.png"), 'rb')
        b64 = str(base64.b64encode(f.read()))
        self.simple_data['attachments'] = [{'filename': 'test.txt', 'value': b64, 'encoding': 'base64'}]
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_composite(self):
        """
        Add a composite test to our simple test list.  Submitting without data
        included should result in it being calculated.
        """

        utils.create_test_list_membership(self.simple_test_list, self.tc)
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.count() == 1
        assert models.TestInstance.objects.count() == self.ntests + 1
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tc)
        assert tic.value == self.simple_data['tests']['test1']['value'] + self.simple_data['tests']['test2']['value']

    def test_create_composite_with_user_attached(self):
        """
        Add a composite test to our simple test list.  Submitting without data
        included should result in it being calculated.
        """
        self.tc.calculation_procedure += ";UTILS.write_file('test_user_attached.txt', 'hello user')"
        self.tc.save()

        utils.create_test_list_membership(self.simple_test_list, self.tc)
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tc)
        assert tic.attachment_set.count() == 1
        assert tic.attachment_set.first().finalized

    def test_create_composite_with_data(self):
        """
        Add a composite test to our simple test list.  Submitting with data
        that matches the calculated data should not result in error.
        """

        utils.create_test_list_membership(self.simple_test_list, self.tc)
        data = self.simple_data.copy()
        data['tests']['testc'] = {'value': 3}
        response = self.client.post(self.create_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.count() == 1
        assert models.TestInstance.objects.count() == self.ntests + 1

    def test_create_composite_with_null_data(self):
        """
        Add a composite test to our simple test list.  Submitting with null data
        value should not result in error.
        """

        utils.create_test_list_membership(self.simple_test_list, self.tc)
        data = self.simple_data.copy()
        data['tests']['testc'] = {'value': ""}
        response = self.client.post(self.create_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        data['tests']['testc'] = {'value': None}
        response = self.client.post(self.create_url, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_composite_with_comment(self):
        """
        Add a composite test to our simple test list.  Submitting with comment
        form composite test should result in comment being saved with composite test.
        """

        utils.create_test_list_membership(self.simple_test_list, self.tc)
        data = self.simple_data.copy()
        data['tests']['testc'] = {'comment': "hello testc"}
        response = self.client.post(self.create_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tc)
        assert tic.value == self.simple_data['tests']['test1']['value'] + self.simple_data['tests']['test2']['value']
        assert tic.comment == "hello testc"

    def test_create_composite_with_invalid_data(self):
        """
        Add a composite test to our simple test list.  Submitting with data
        that does not match the calculated data should result in error.
        """

        utils.create_test_list_membership(self.simple_test_list, self.tc)
        data = self.simple_data.copy()
        data['tests']['testc'] = {'value': 999}
        response = self.client.post(self.create_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert models.TestListInstance.objects.count() == 0
        assert models.TestInstance.objects.count() == 0

    def test_create_composite_invalid(self):
        """
        Add a composite test to our simple test list.  If composite can't be
        calculated correctly, test list instance should not be created.
        """
        utils.create_test_list_membership(self.simple_test_list, self.tc)
        data = self.simple_data.copy()
        data['tests'].pop('test1')
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert models.TestListInstance.objects.count() == 0

    def test_create_composite_with_constant(self):
        """
        Add a composite test which depends on a constant value to our simple test list.
        Test list instance should be created if constant value not provided.
        """
        models.Test.objects.filter(pk=self.t2.pk).update(
            type=models.CONSTANT,
            constant_value=99
        )

        utils.create_test_list_membership(self.simple_test_list, self.tc)
        self.simple_data['tests'].pop("test2")
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tc)
        assert tic.value == 1 + 99

    def test_create_composite_with_invalid_constant(self):
        """
        Add a composite test which depends on a constant value to our simple test list.
        Test list instance should not be created if constant value provided doesn't match expected value.
        """
        models.Test.objects.filter(pk=self.t2.pk).update(
            type=models.CONSTANT,
            constant_value=99
        )

        utils.create_test_list_membership(self.simple_test_list, self.tc)
        self.simple_data['tests']['test2'] = 100
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_with_string_composite(self):
        """
        Add a composite test which depends on a constant value to our simple test list.
        Test list instance should be created if constant value not provided.
        """
        utils.create_test_list_membership(self.simple_test_list, self.tsc)
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tsc)
        assert tic.string_value == "hello test three"

    def test_file_upload(self):
        """
        Add a file upload test and ensure we can upload, process and have
        composite tests depend on it being processed correctly.
        """
        self.tsc.calculation_procedure = "result = file_upload['baz']['baz1']"
        self.tsc.save()
        utils.create_test_list_membership(self.simple_test_list, self.tsc)

        upload = utils.create_test(name="file_upload", test_type=models.UPLOAD)
        upload.calculation_procedure = "import json; result=json.load(FILE)"
        upload.save()
        utils.create_test_list_membership(self.simple_test_list, upload)

        filepath = os.path.join(settings.PROJECT_ROOT, "qa", "tests", "TESTRUNNER_test_file.json")
        upload_data = open(filepath, 'rb').read()
        self.simple_data['tests']['file_upload'] = {
            'value': base64.b64encode(upload_data),
            'filename': "tmp.json",
            'comment': "test comment",
        }
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tsc)
        assert tic.string_value == "test"
        tiu = models.TestInstance.objects.get(unit_test_info__test=upload)

        assert tiu.attachment_set.count() == 1
        assert tiu.attachment_set.first().finalized
        assert tiu.comment == "test comment"

    def test_file_upload_no_filename(self):
        """
        Add a file upload test and ensure we can upload, process and have
        composite tests depend on it being processed correctly.
        """
        upload = utils.create_test(name="file_upload", test_type=models.UPLOAD)
        upload.calculation_procedure = "import json; result=json.load(FILE)"
        upload.save()
        utils.create_test_list_membership(self.simple_test_list, upload)

        filepath = os.path.join(settings.PROJECT_ROOT, "qa", "tests", "TESTRUNNER_test_file.json")
        upload_data = open(filepath, 'rb').read()
        self.simple_data['tests']['file_upload'] = {
            'value': base64.b64encode(upload_data),
            'comment': "test comment",
        }
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_file_upload_with_user_attached(self):
        """
        Add a file upload test and ensure we can upload, process and have
        composite tests depend on it being processed correctly.
        """
        self.tsc.calculation_procedure = "result = file_upload['baz']['baz1']"
        self.tsc.save()
        utils.create_test_list_membership(self.simple_test_list, self.tsc)

        upload = utils.create_test(name="file_upload", test_type=models.UPLOAD)
        upload.calculation_procedure = "import json; result=json.load(FILE);"
        upload.calculation_procedure += "UTILS.write_file('test_user_attached.txt', 'hello user')"
        upload.save()
        utils.create_test_list_membership(self.simple_test_list, upload)

        filepath = os.path.join(settings.PROJECT_ROOT, "qa", "tests", "TESTRUNNER_test_file.json")
        upload_data = open(filepath, 'rb').read()
        self.simple_data['tests']['file_upload'] = {
            'value': base64.b64encode(upload_data),
            'filename': "tmp.json",
        }
        response = self.client.post(self.create_url, self.simple_data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tsc)
        assert tic.string_value == "test"
        tiu = models.TestInstance.objects.get(unit_test_info__test=upload)

        assert tiu.attachment_set.count() == 2
        for a in tiu.attachment_set.all():
            assert a.finalized

    def test_todo(self):
        """
        Need to:
            test editing including uploads
            refactor Upload to use Upload handler
        """
        assert False
