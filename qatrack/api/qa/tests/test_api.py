import base64
import datetime
import json
import os
import time

from django.conf import settings
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
import pytest
import pytz
from rest_framework import status
from rest_framework.test import APITestCase

from qatrack.attachments.models import Attachment
from qatrack.qa import models
from qatrack.qa.tests import utils
from qatrack.service_log.tests import utils as sl_utils


class TestTestListInstanceAPI(APITestCase):

    def setUp(self):

        self.unit = utils.create_unit()
        self.test_list = utils.create_test_list("test list")
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

        self.tdate = utils.create_test(name="testdate", test_type=models.DATE)
        self.tdatetime = utils.create_test(name="testdatetime", test_type=models.DATETIME)

        self.default_tests = [self.t1, self.t2, self.t3, self.t4, self.t5]
        self.ntests = len(self.default_tests)

        for order, t in enumerate(self.default_tests):
            utils.create_test_list_membership(self.test_list, t, order=order)

        frequency = utils.create_frequency(name="daily")
        self.utc = utils.create_unit_test_collection(
            test_collection=self.test_list, unit=self.unit, frequency=frequency
        )

        self.create_url = reverse('testlistinstance-list')
        self.utc_url = reverse("unittestcollection-detail", kwargs={'pk': self.utc.pk})

        self.data = {
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
                count = 0
                while True:
                    try:
                        a.attachment.close()
                        os.remove(a.attachment.path)
                        break
                    except PermissionError:

                        if count == 2:
                            break

                        count += 1
                        time.sleep(0.2)

    def test_create(self):
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.unreviewed().count() == 1
        assert models.TestInstance.objects.count() == self.ntests
        for t in self.default_tests:
            ti = models.TestInstance.objects.get(unit_test_info__test=t)
            v = ti.value if t.type not in models.STRING_TYPES else ti.string_value
            assert v == self.data['tests'][t.slug]['value']

    def test_create_order(self):
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        for tlm in self.test_list.testlistmembership_set.order_by("order"):
            ti = models.TestInstance.objects.get(unit_test_info__test=tlm.test)
            assert ti.order == tlm.order

    def test_create_no_status(self):
        models.TestInstanceStatus.objects.all().delete()
        response = self.client.post(self.create_url, self.data)
        assert response.data == ['No test instance status available']

    def test_create_user_status(self):
        s2 = utils.create_status(name="user status", slug="user_status", is_default=False, requires_review=False)
        s2_url = reverse("testinstancestatus-detail", kwargs={'pk': s2.pk})
        self.data['status'] = s2_url
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestInstance.objects.filter(status=s2).count() == self.ntests
        assert models.TestListInstance.objects.all().count() == 1
        assert models.TestListInstance.objects.unreviewed().count() == 0

    def test_create_with_sublist(self):
        sublist = utils.create_test_list(name="sublist")
        subtest = utils.create_test(name="subtest")
        utils.create_test_list_membership(test_list=sublist, test=subtest)
        models.Sublist.objects.create(parent=self.test_list, child=sublist, order=1)
        self.data['tests']['subtest'] = {'value': 123}
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.unreviewed().count() == 1
        assert models.TestInstance.objects.count() == self.ntests + 1
        assert models.TestInstance.objects.get(unit_test_info__test__slug="subtest").value == 123

    def test_create_no_work_completed(self):
        self.data['work_started'] = '2018-01-01 10:49:00'
        self.data.pop("work_completed")
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_no_work_started(self):
        self.data.pop("work_started")
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_with_rtsqa(self):

        sl_utils.create_service_event_status(is_default=True)
        rtsqa = sl_utils.create_return_to_service_qa(unit_test_collection=self.utc)
        rtsqa_url = reverse("returntoserviceqa-detail", kwargs={'pk': rtsqa.pk})
        self.data['return_to_service_qa'] = rtsqa_url
        assert rtsqa.test_list_instance is None
        self.client.post(self.create_url, self.data)
        rtsqa.refresh_from_db()
        assert rtsqa.test_list_instance is not None

    def test_create_missing_test(self):
        self.data['tests'].pop("test1")
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_constant_value(self):
        models.Test.objects.filter(pk=self.t2.pk).update(type=models.CONSTANT, constant_value=99)
        self.data['tests']['test2']['value'] = 100
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_with_txt_attachments(self):
        self.data['attachments'] = [{'filename': 'test.txt', 'value': 'hello text', 'encoding': 'text'}]
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        tli = models.TestListInstance.objects.first()
        assert tli.attachment_set.count() == 1
        a = tli.attachment_set.first()
        assert a.finalized
        assert "uploads/testlistinstance" in a.attachment.path or "uploads\\testlistinstance" in a.attachment.path

    def test_create_with_b64_attachments(self):
        f = open(os.path.join(settings.PROJECT_ROOT, "qa", "static", "qa", "img", "tux.png"), 'rb')
        b64 = base64.b64encode(f.read()).decode()
        self.data['attachments'] = [{'filename': 'test.txt', 'value': b64, 'encoding': 'base64'}]
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        tli = models.TestListInstance.objects.first()
        assert tli.attachment_set.count() == 1
        a = tli.attachment_set.first()
        assert a.finalized
        assert "uploads/testlistinstance" in a.attachment.path or "uploads\\testlistinstance" in a.attachment.path

    def test_create_with_b64_attachments_invalid(self):
        f = open(os.path.join(settings.PROJECT_ROOT, "qa", "static", "qa", "img", "tux.png"), 'rb')
        b64 = str(base64.b64encode(f.read()))
        self.data['attachments'] = [{'filename': 'test.txt', 'value': b64, 'encoding': 'base64'}]
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_with_missing_attach_value(self):
        self.data['attachments'] = [{'filename': 'test.txt', 'encoding': 'base64'}]
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_composite(self):
        """
        Add a composite test to our test list.  Submitting without data
        included should result in it being calculated.
        """

        utils.create_test_list_membership(self.test_list, self.tc)
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.count() == 1
        assert models.TestInstance.objects.count() == self.ntests + 1
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tc)
        assert tic.value == self.data['tests']['test1']['value'] + self.data['tests']['test2']['value']

    def test_create_composite_skipped_all_dependencies_comp_not_skipped(self):
        """
        Add a composite test to our test list.  Submitting with its dependencies
        skipped should result in an error and mention it is missing dependencies
        and needs to be skipped
        """

        utils.create_test_list_membership(self.test_list, self.tc)
        self.data['tests']['test1'] = {'value': None, 'skipped': True}
        self.data['tests']['test2'] = {'value': None, 'skipped': True}
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "missing dependencies" in response.json()['non_field_errors'][0]

    def test_create_composite_skipped_one_dependency_comp_not_skipped(self):
        """
        Add a composite test to our test list.  Submitting with one dependency
        skipped should result in an error and mention it is missing dependencies
        and needs to be skipped
        """

        utils.create_test_list_membership(self.test_list, self.tc)
        self.data['tests']['test1'] = {'value': None, 'skipped': True}
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "missing dependencies" in response.json()['non_field_errors'][0]

    def test_create_composite_skipped_all_dependencies_comp_skipped(self):
        """
        Add a composite test to our test list.  Submitting with one dependency
        skipped should result in an error and mention it is missing dependencies
        and needs to be skipped
        """

        utils.create_test_list_membership(self.test_list, self.tc)
        self.data['tests']['test1'] = {'value': None, 'skipped': True}
        self.data['tests']['test2'] = {'value': None, 'skipped': True}
        self.data['tests']['testc'] = {'skipped': True}
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.count() == 1
        assert models.TestInstance.objects.count() == self.ntests + 1
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tc)
        assert tic.pass_fail == models.NOT_DONE

    def test_create_date_composite(self):
        """
        Add a date composite test to our test list.  Submitting without data
        included should result in it being calculated.
        """

        td1 = utils.create_test(name="test_date_1", test_type=models.DATE)
        td2 = utils.create_test(name="test_date_2", test_type=models.DATETIME)
        tcd = utils.create_test(name="test_date_c", test_type=models.COMPOSITE)
        tcd.calculation_procedure = "result = (test_date_2.date() - test_date_1).total_seconds()"
        tcd.save()
        for t in [td1, td2, tcd]:
            utils.create_test_list_membership(self.test_list, t)

        self.data['tests']['test_date_1'] = {'value': "2019-08-01"}
        self.data['tests']['test_date_2'] = {'value': "2019-08-02 23:45:00"}

        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.count() == 1
        assert models.TestInstance.objects.count() == self.ntests + 3
        tic = models.TestInstance.objects.get(unit_test_info__test=tcd)
        assert tic.value == 86400

    def test_create_composite_invalid_proc(self):
        """
        An invalid calculation procedure should result in an error
        """

        self.tc.calculation_procedure = "1/0"
        self.tc.save()
        utils.create_test_list_membership(self.test_list, self.tc)
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_composite_with_user_attached(self):
        """
        Add a composite test to our test list.  Submitting without data
        included should result in it being calculated.
        """
        # FAILS on windows:
        #
        #   File "C:\home\code\qatrackplus\qatrack\attachments\models.py", line 50, in move_tmp_file
        #     os.rename(start_path, new_path)
        # PermissionError: [WinError 32] The process cannot access the file because it is being used by another process

        self.tc.calculation_procedure += ";UTILS.write_file('test_user_attached.txt', 'hello user')"
        self.tc.save()

        utils.create_test_list_membership(self.test_list, self.tc)
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tc)
        assert tic.attachment_set.count() == 1
        assert tic.attachment_set.first().finalized

    def test_create_composite_with_data(self):
        """
        Add a composite test to our test list.  Submitting with data
        that matches the calculated data should not result in error.
        """

        utils.create_test_list_membership(self.test_list, self.tc)
        data = self.data.copy()
        data['tests']['testc'] = {'value': 3}
        response = self.client.post(self.create_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.count() == 1
        assert models.TestInstance.objects.count() == self.ntests + 1

    @pytest.mark.skip("causing a segfault with sqlite :(")
    def test_create_composite_with_null_data(self):
        """
        Add a composite test to our test list.  Submitting with null data
        value should not result in error.
        """

        utils.create_test_list_membership(self.test_list, self.tc)
        data = self.data.copy()
        data['tests']['testc'] = {'value': ""}
        response = self.client.post(self.create_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        data['tests']['testc'] = {'value': None}
        response = self.client.post(self.create_url, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_composite_with_comment(self):
        """
        Add a composite test to our test list.  Submitting with comment
        form composite test should result in comment being saved with composite test.
        """

        utils.create_test_list_membership(self.test_list, self.tc)
        data = self.data.copy()
        data['tests']['testc'] = {'comment': "hello testc"}
        response = self.client.post(self.create_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tc)
        assert tic.value == self.data['tests']['test1']['value'] + self.data['tests']['test2']['value']
        assert tic.comment == "hello testc"

    def test_create_composite_with_invalid_data(self):
        """
        Add a composite test to our test list.  Submitting with data
        that does not match the calculated data should result in error.
        """

        utils.create_test_list_membership(self.test_list, self.tc)
        data = self.data.copy()
        data['tests']['testc'] = {'value': 999}
        response = self.client.post(self.create_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert models.TestListInstance.objects.count() == 0
        assert models.TestInstance.objects.count() == 0

    def test_create_composite_invalid(self):
        """
        Add a composite test to our test list.  If composite can't be
        calculated correctly, test list instance should not be created.
        """
        utils.create_test_list_membership(self.test_list, self.tc)
        data = self.data.copy()
        data['tests'].pop('test1')
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert models.TestListInstance.objects.count() == 0

    def test_create_composite_with_constant(self):
        """
        Add a composite test which depends on a constant value to our test list.
        Test list instance should be created if constant value not provided.
        """
        models.Test.objects.filter(pk=self.t2.pk).update(type=models.CONSTANT, constant_value=99)

        utils.create_test_list_membership(self.test_list, self.tc)
        self.data['tests'].pop("test2")
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tc)
        assert tic.value == 1 + 99

    def test_create_composite_with_invalid_constant(self):
        """
        Add a composite test which depends on a constant value to our test list.
        Test list instance should not be created if constant value provided doesn't match expected value.
        """
        models.Test.objects.filter(pk=self.t2.pk).update(type=models.CONSTANT, constant_value=99)

        utils.create_test_list_membership(self.test_list, self.tc)
        self.data['tests']['test2'] = 100
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_with_date(self):
        """
        Add a date test. Resulting TestInstance should have date_value != None
        """
        utils.create_test_list_membership(self.test_list, self.tdate)
        today = datetime.date(2019, 11, 11)

        self.data['tests']['testdate'] = {'value': today.strftime("%Y-%m-%d")}

        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tdate)
        assert tic.date_value == today

    def test_create_with_datetime(self):
        """
        Add a datetime test. Resulting TestInstance should have datetime_value != None
        """
        utils.create_test_list_membership(self.test_list, self.tdatetime)
        now = timezone.now()
        self.data['tests']['testdatetime'] = {
            'value': now.astimezone(pytz.timezone("America/Toronto")).strftime("%Y-%m-%d %H:%M:%S.%f")
        }
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tdatetime)
        assert tic.datetime_value == now

    def test_create_with_string_composite(self):
        """
        Add a composite test which depends on a constant value to our test list.
        Test list instance should be created if constant value not provided.
        """
        utils.create_test_list_membership(self.test_list, self.tsc)
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tsc)
        assert tic.string_value == "hello test three"

    def test_create_composite_of_composite(self):
        """
        Add a composite test which depends on another composite value to our test list.
        """

        tcc = utils.create_test(name="testcc", test_type=models.COMPOSITE)
        tcc.calculation_procedure = "result = 2*testc"
        tcc.save()
        utils.create_test_list_membership(self.test_list, self.tc)
        utils.create_test_list_membership(self.test_list, tcc)

        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.count() == 1
        assert models.TestInstance.objects.count() == self.ntests + 2
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tc)
        ticc = models.TestInstance.objects.get(unit_test_info__test=tcc)
        assert ticc.value == 2 * tic.value

    def test_create_composite_of_composite_string(self):
        """
        Add a string composite test which depends on another composite value to our test list.
        """

        tscc = utils.create_test(name="testscc", test_type=models.STRING_COMPOSITE)
        tscc.calculation_procedure = "result = 'composite of composite (%s)' % testsc"
        tscc.save()

        utils.create_test_list_membership(self.test_list, self.tsc)
        utils.create_test_list_membership(self.test_list, tscc)
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=tscc)
        assert tic.string_value == "composite of composite (hello test three)"

    def test_file_upload(self):
        """
        Add a file upload test and ensure we can upload, process and have
        composite tests depend on it being processed correctly.
        """
        # FAILS on windows:
        #
        #   File "C:\home\code\qatrackplus\qatrack\attachments\models.py", line 50, in move_tmp_file
        #     os.rename(start_path, new_path)
        # PermissionError: [WinError 32] The process cannot access the file because it is being used by another process

        self.tsc.calculation_procedure = "result = file_upload['baz']['baz1']"
        self.tsc.save()
        utils.create_test_list_membership(self.test_list, self.tsc)

        upload = utils.create_test(name="file_upload", test_type=models.UPLOAD)
        upload.calculation_procedure = "import json; result=json.load(FILE)"
        upload.save()
        utils.create_test_list_membership(self.test_list, upload)

        upload_data = json.dumps({"foo": 1.2, "bar": [1, 2, 3, 4], "baz": {"baz1": "test"}}).encode()
        self.data['tests']['file_upload'] = {
            'value': base64.b64encode(upload_data),
            'filename': "tmp.json",
            'comment': "test comment",
        }
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tsc)
        assert tic.string_value == "test"
        tiu = models.TestInstance.objects.get(unit_test_info__test=upload)

        assert tiu.attachment_set.count() == 1
        assert tiu.attachment_set.first().finalized
        assert tiu.comment == "test comment"

    def test_file_upload_txt(self):
        """
        Add a file upload test and ensure we can upload raw text, process and have
        composite tests depend on it being processed correctly.
        """
        self.tsc.calculation_procedure = "result = file_upload['baz']['baz1']"
        self.tsc.save()
        utils.create_test_list_membership(self.test_list, self.tsc)

        upload = utils.create_test(name="file_upload", test_type=models.UPLOAD)
        upload.calculation_procedure = "import json; result=json.load(FILE)"
        upload.save()
        utils.create_test_list_membership(self.test_list, upload)

        upload_data = json.dumps({"foo": 1.2, "bar": [1, 2, 3, 4], "baz": {"baz1": "test"}}).encode()
        self.data['tests']['file_upload'] = {
            'value': upload_data,
            'filename': "tmp.json",
            'encoding': "text",
            'comment': "test comment",
        }
        response = self.client.post(self.create_url, self.data)
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
        utils.create_test_list_membership(self.test_list, upload)

        upload_data = json.dumps({"foo": 1.2, "bar": [1, 2, 3, 4], "baz": {"baz1": "test"}}).encode()
        self.data['tests']['file_upload'] = {
            'value': base64.b64encode(upload_data),
            'comment': "test comment",
        }
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_file_upload_not_b64(self):
        """
        A text upload without specifying text encoding should raise an error.
        """
        upload = utils.create_test(name="file_upload", test_type=models.UPLOAD)
        upload.calculation_procedure = "import json; result=json.load(FILE)"
        upload.save()
        utils.create_test_list_membership(self.test_list, upload)

        self.data['tests']['file_upload'] = {
            'filename': "tmp.txt",
            'value': 'not b64 encoded',
        }
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_file_upload_invalid_proc(self):
        """
        A text upload without specifying text encoding should raise an error.
        """
        upload = utils.create_test(name="file_upload", test_type=models.UPLOAD)
        upload.calculation_procedure = "1/0"
        upload.save()
        utils.create_test_list_membership(self.test_list, upload)

        self.data['tests']['file_upload'] = {
            'filename': "tmp.txt",
            'encoding': 'text',
            'value': 'text',
        }
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_file_upload_with_user_attached(self):
        """
        Add a file upload test and ensure we can upload, process and have
        composite tests depend on it being processed correctly.
        """
        # FAILS on windows:
        #
        #   File "C:\home\code\qatrackplus\qatrack\attachments\models.py", line 50, in move_tmp_file
        #     os.rename(start_path, new_path)
        # PermissionError: [WinError 32] The process cannot access the file because it is being used by another process

        self.tsc.calculation_procedure = "result = file_upload['baz']['baz1']"
        self.tsc.save()
        utils.create_test_list_membership(self.test_list, self.tsc)

        upload = utils.create_test(name="file_upload", test_type=models.UPLOAD)
        upload.calculation_procedure = "import json; result=json.load(FILE);"
        upload.calculation_procedure += "UTILS.write_file('test_user_attached.txt', 'hello user')"
        upload.save()
        utils.create_test_list_membership(self.test_list, upload)

        upload_data = json.dumps({"foo": 1.2, "bar": [1, 2, 3, 4], "baz": {"baz1": "test"}}).encode()
        self.data['tests']['file_upload'] = {
            'value': base64.b64encode(upload_data),
            'filename': "tmp.json",
        }
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tsc)
        assert tic.string_value == "test"
        tiu = models.TestInstance.objects.get(unit_test_info__test=upload)

        assert tiu.attachment_set.count() == 2
        for a in tiu.attachment_set.all():
            assert a.finalized

    def test_basic_edit(self):
        resp = self.client.post(self.create_url, self.data)
        new_data = {'tests': {'test1': {'value': 99}}}
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 200
        assert models.TestInstance.objects.get(unit_test_info__test__slug="test1").value == 99

    def test_composite_edit(self):
        utils.create_test_list_membership(self.test_list, self.tc)
        resp = self.client.post(self.create_url, self.data)
        assert models.TestInstance.objects.get(unit_test_info__test__slug="testc").value == 3
        new_data = {'tests': {'test1': {'value': 99}, 'test2': {'value': 101}}}
        self.client.patch(resp.data['url'], new_data)
        assert models.TestInstance.objects.get(unit_test_info__test__slug="testc").value == 200

    def test_edit_work_completed(self):
        resp = self.client.post(self.create_url, self.data)
        new_data = {'work_completed': '2020-07-25 10:49:47'}
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 200
        assert models.TestListInstance.objects.first().work_completed.year == 2020

    def test_edit_user_status(self):
        s2 = utils.create_status(name="user status", slug="user_status", is_default=False, requires_review=False)
        s2_url = reverse("testinstancestatus-detail", kwargs={'pk': s2.pk})
        resp = self.client.post(self.create_url, self.data)
        new_data = {'status': s2_url}
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 200
        assert models.TestInstance.objects.filter(status=s2).count() == self.ntests
        assert models.TestListInstance.objects.all().count() == 1
        assert models.TestListInstance.objects.unreviewed().count() == 0

    def test_edit_wc_ws_error(self):
        resp = self.client.post(self.create_url, self.data)
        new_data = {
            'work_completed': '2020-07-25 10:49:47',
            'work_started': '2021-07-25 10:49:47',
        }
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 400

    def test_different_editor(self):
        """
        If a test list is created, and then modified by a different user, the
        modified_by user should be set correctly.
        """

        resp = self.client.post(self.create_url, self.data)
        new_data = {'tests': {'test1': {'value': 99}}}
        self.client.logout()
        user = utils.create_user(uname="user2")
        self.client.force_authenticate(user=user)
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 200
        tli = models.TestListInstance.objects.first()
        assert tli.created_by.username == "user"
        assert tli.modified_by.username == "user2"

    def test_edit_perms(self):
        """
        Check user with editing perms can edit tl
        If user has no edit perms, attempting to edit should return a 403.
        """

        resp = self.client.post(self.create_url, self.data)
        self.client.logout()
        user = utils.create_user(uname="user2", is_staff=False, is_superuser=False)
        user.user_permissions.add(Permission.objects.get(codename="change_testlistinstance"))
        self.client.force_authenticate(user=user)
        new_data = {'tests': {'test1': {'value': 99}}}
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 200

    def test_no_edit_perms(self):
        """
        Check user without editing perms can not edit tl
        """

        resp = self.client.post(self.create_url, self.data)
        self.client.logout()
        user = utils.create_user(uname="user2", is_staff=False, is_superuser=False)
        self.client.force_authenticate(user=user)
        new_data = {'tests': {'test1': {'value': 99}}}
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 403

    def test_tl_comments(self):
        self.data['comment'] = "test list comment"

        # origial comment
        resp = self.client.post(self.create_url, self.data)
        tli = models.TestListInstance.objects.first()
        assert tli.comments.first().comment == "test list comment"

        # add a comment with the edit and preserve  original
        new_data = {'comment': 'edit comment'}
        self.client.patch(resp.data['url'], new_data)
        assert tli.comments.count() == 2
        assert 'edit comment' in tli.comments.values_list("comment", flat=True)

    def test_comment_preserved(self):
        self.data['tests']['test1']['comment'] = 'original comment'
        resp = self.client.post(self.create_url, self.data)
        new_data = {'tests': {'test1': {'value': 99}}}
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 200
        assert models.TestInstance.objects.get(unit_test_info__test__slug="test1").comment == "original comment"

    def test_comment_updated(self):
        self.data['tests']['test1']['comment'] = 'original comment'
        resp = self.client.post(self.create_url, self.data)
        new_data = {'tests': {'test1': {'value': 99, 'comment': 'new comment'}}}
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 200
        assert models.TestInstance.objects.get(unit_test_info__test__slug="test1").comment == "new comment"

    def test_user_key_updated(self):
        self.data['user_key'] = "1234"
        resp = self.client.post(self.create_url, self.data)
        new_data = {'user_key': "5678"}
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 200
        assert models.TestListInstance.objects.latest("pk").user_key == "5678"

    def test_skip_preserved(self):
        self.data['tests']['test1'] = {'skipped': True}
        resp = self.client.post(self.create_url, self.data)
        new_data = {'tests': {'test2': {'value': 99}}}
        self.client.patch(resp.data['url'], new_data)
        assert models.TestInstance.objects.get(unit_test_info__test__slug="test1").skipped

    def test_unskip(self):
        self.data['tests']['test1'] = {'skipped': True}
        resp = self.client.post(self.create_url, self.data)
        new_data = {'tests': {'test1': {'value': 99}}}
        self.client.patch(resp.data['url'], new_data)
        ti = models.TestInstance.objects.get(unit_test_info__test__slug="test1")
        assert not ti.skipped
        assert ti.value == 99

    def test_new_skip(self):
        resp = self.client.post(self.create_url, self.data)
        new_data = {'tests': {'test1': {'skipped': True}}}
        self.client.patch(resp.data['url'], new_data)
        ti = models.TestInstance.objects.get(unit_test_info__test__slug="test1")
        assert ti.skipped
        assert ti.value is None

    def test_complete_in_progress(self):
        self.data['in_progress'] = True
        resp = self.client.post(self.create_url, self.data)
        assert models.TestListInstance.objects.all().first().in_progress
        new_data = {'in_progress': False}
        self.client.patch(resp.data['url'], new_data)
        assert not models.TestListInstance.objects.all().first().in_progress

    def test_complete_unscheduled(self):
        self.data['include_for_scheduling'] = True
        resp = self.client.post(self.create_url, self.data)
        assert models.TestListInstance.objects.all().first().include_for_scheduling
        new_data = {'include_for_scheduling': False}
        self.client.patch(resp.data['url'], new_data)
        assert not models.TestListInstance.objects.all().first().include_for_scheduling

    def test_complete_unscheduled_due_dates(self):
        utils.create_test_list_instance(
            unit_test_collection=self.utc, work_completed=timezone.now() - timezone.timedelta(days=10)
        )
        self.utc.refresh_from_db()
        expected_due_date = self.utc.due_date

        self.data['include_for_scheduling'] = False
        self.data['work_completed'] = (timezone.now() - timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        self.data['work_started'] = self.data['work_completed']
        self.client.post(self.create_url, self.data)

        # unscheduled so should be same due date
        self.utc.refresh_from_db()
        assert self.utc.due_date.date() == expected_due_date.date()

    def test_no_put(self):
        """All updates should be via patch"""
        resp = self.client.post(self.create_url, self.data)
        new_data = {'tests': {'test1': {'value': 1}}}
        edit_resp = self.client.put(resp.data['url'], new_data)
        assert edit_resp.status_code == 405

    def test_utc_due_date_updated_on_create(self):
        assert self.utc.due_date is None
        self.client.post(self.create_url, self.data)
        self.utc.refresh_from_db()
        assert self.utc.due_date is not None

    def test_utc_due_date_updated_on_edit(self):
        self.data['work_completed'] = '2019-07-25 10:49:47'
        resp = self.client.post(self.create_url, self.data)
        self.utc.refresh_from_db()
        new_data = {'work_completed': '2020-07-25 10:49:47'}
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 200
        self.utc.refresh_from_db()
        assert self.utc.due_date.year == 2020

    def test_edit_with_file_upload(self):
        """
        Ensure making a simple edit to a tli with an text upload test succeeds.
        """
        # FAILS on windows:
        #
        #   File "C:\home\code\qatrackplus\qatrack\attachments\models.py", line 50, in move_tmp_file
        #     os.rename(start_path, new_path)
        # PermissionError: [WinError 32] The process cannot access the file because it is being used by another process

        self.tsc.calculation_procedure = "result = file_upload['baz']['baz1']"
        self.tsc.save()
        utils.create_test_list_membership(self.test_list, self.tsc)

        upload = utils.create_test(name="file_upload", test_type=models.UPLOAD)
        upload.calculation_procedure = "import json; result=json.load(FILE)"
        upload.save()
        utils.create_test_list_membership(self.test_list, upload)

        upload_data = json.dumps({"foo": 1.2, "bar": [1, 2, 3, 4], "baz": {"baz1": "test"}}).encode()
        self.data['tests']['file_upload'] = {
            'value': base64.b64encode(upload_data),
            'filename': "tmp.json",
            'comment': "test comment",
        }
        resp = self.client.post(self.create_url, self.data)
        new_data = {'tests': {'test1': {'value': 99}}}
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 200
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tsc)
        assert tic.string_value == "test"

    def test_edit_with_text_file_upload(self):
        """
        Ensure making a simple edit to a tli with an upload test succeeds.
        """
        # FAILS on windows:
        #
        #   File "C:\home\code\qatrackplus\qatrack\attachments\models.py", line 52, in move_tmp_file
        #     os.rename(start_path, new_path)
        # PermissionError: [WinError 32] The process cannot access the file because it is being used by another process

        self.tsc.calculation_procedure = "result = file_upload['baz']['baz1']"
        self.tsc.save()
        utils.create_test_list_membership(self.test_list, self.tsc)

        upload = utils.create_test(name="file_upload", test_type=models.UPLOAD)
        upload.calculation_procedure = "import json; result=json.load(FILE)"
        upload.save()
        utils.create_test_list_membership(self.test_list, upload)

        upload_data = {"foo": 1.2, "bar": [1, 2, 3, 4], "baz": {"baz1": "test"}}
        upload_data['baz']['baz1'] = "edited content"
        self.data['tests']['file_upload'] = {
            'value': json.dumps(upload_data),
            'encoding': 'text',
            'filename': "tmp.json",
            'comment': "test comment",
        }
        resp = self.client.post(self.create_url, self.data)
        tiu = models.TestInstance.objects.get(unit_test_info__test=upload)
        assert tiu.attachment_set.count() == 1
        new_data = {'tests': {'test1': {'value': 99}}}
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 200
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tsc)
        assert tic.string_value == "edited content"
        tiu.refresh_from_db()
        assert tiu.attachment_set.count() == 1

    def test_edit_with_file_upload_and_user_attached(self):
        """
        Ensure making a simple edit to a tli with an upload test succeeds.
        """
        # FAILS on windows:
        #
        #   File "C:\home\code\qatrackplus\qatrack\attachments\models.py", line 50, in move_tmp_file
        #     os.rename(start_path, new_path)
        # PermissionError: [WinError 32] The process cannot access the file because it is being used by another process

        self.tsc.calculation_procedure = "result = file_upload['baz']['baz1']"
        self.tsc.save()
        utils.create_test_list_membership(self.test_list, self.tsc)

        upload = utils.create_test(name="file_upload", test_type=models.UPLOAD)
        upload.calculation_procedure = "import json; result=json.load(FILE);"
        upload.calculation_procedure += "UTILS.write_file('test_user_attached.txt', 'hello user')"
        upload.save()
        utils.create_test_list_membership(self.test_list, upload)

        upload_data = json.dumps({"foo": 1.2, "bar": [1, 2, 3, 4], "baz": {"baz1": "test"}}).encode()
        self.data['tests']['file_upload'] = {
            'value': base64.b64encode(upload_data),
            'filename': "tmp.json",
            'comment': "test comment",
        }
        resp = self.client.post(self.create_url, self.data)
        tiu = models.TestInstance.objects.get(unit_test_info__test=upload)
        assert tiu.attachment_set.count() == 2
        new_data = {'tests': {'test1': {'value': 99}}}
        edit_resp = self.client.patch(resp.data['url'], new_data)
        assert edit_resp.status_code == 200
        tic = models.TestInstance.objects.get(unit_test_info__test=self.tsc)
        assert tic.string_value == "test"
        tiu.refresh_from_db()
        assert tiu.attachment_set.count() == 2

    def test_edit_with_rtsqa(self):

        resp = self.client.post(self.create_url, self.data)
        sl_utils.create_service_event_status(is_default=True)
        rtsqa = sl_utils.create_return_to_service_qa(unit_test_collection=self.utc)
        rtsqa_url = reverse("returntoserviceqa-detail", kwargs={'pk': rtsqa.pk})
        new_data = {'return_to_service_qa': rtsqa_url}
        assert rtsqa.test_list_instance is None
        self.client.patch(resp.data['url'], new_data)
        rtsqa.refresh_from_db()
        assert rtsqa.test_list_instance is not None

    def test_edit_with_new_attachments(self):

        self.data['attachments'] = [{'filename': 'test.txt', 'value': 'hello text', 'encoding': 'text'}]
        resp = self.client.post(self.create_url, self.data)
        tli = models.TestListInstance.objects.first()
        assert tli.attachment_set.count() == 1
        new_data = {'attachments': [{'filename': 'test.txt', 'value': 'hello text', 'encoding': 'text'}]}
        self.client.patch(resp.data['url'], new_data)
        tli.refresh_from_db()
        assert tli.attachment_set.count() == 2

    def test_create_unique(self):
        self.data['user_key'] = "1234"
        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.latest("pk").user_key == "1234"

        response = self.client.post(self.create_url, self.data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "test list instance with this user key already exists." in response.json()['user_key']


class TestPerformTestListCycleAPI(APITestCase):

    def setUp(self):

        self.unit = utils.create_unit()
        self.test_list1 = utils.create_test_list("test list 1")
        self.test_list2 = utils.create_test_list("test list 2")
        self.test_list_cycle = utils.create_cycle([self.test_list1, self.test_list2], "test list cycle")

        self.t1 = utils.create_test(name="test1")
        self.t2 = utils.create_test(name="test2")

        utils.create_test_list_membership(self.test_list1, self.t1)
        utils.create_test_list_membership(self.test_list2, self.t2)

        self.utc = utils.create_unit_test_collection(test_collection=self.test_list_cycle, unit=self.unit)

        self.create_url = reverse('testlistinstance-list')
        self.utc_url = reverse("unittestcollection-detail", kwargs={'pk': self.utc.pk})

        self.day1_data = {
            'unit_test_collection': self.utc_url,
            'work_completed': '2019-07-25 10:49:47',
            'work_started': '2019-07-25 10:49:00',
            'tests': {
                'test1': {
                    'value': 1
                }
            },
            'day': 0,
        }
        self.day2_data = self.day1_data.copy()
        self.day2_data['day'] = 1
        self.day2_data['tests'] = {'test2': {'value': 2}}

        self.client.login(username="user", password="password")
        self.status = utils.create_status()

    def test_create_day_2(self):
        response = self.client.post(self.create_url, self.day2_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.unreviewed().count() == 1
        tli = models.TestListInstance.objects.first()
        assert tli.testinstance_set.values_list('value', flat=True)[0] == 2
        assert tli.test_list_id == self.test_list2.id
        assert tli.day == self.day2_data['day']

    def test_create_day_1(self):
        response = self.client.post(self.create_url, self.day1_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert models.TestListInstance.objects.unreviewed().count() == 1
        tli = models.TestListInstance.objects.first()
        assert tli.testinstance_set.values_list('value', flat=True)[0] == 1
        assert tli.test_list_id == self.test_list1.id
        assert tli.day == 0

    def test_create_no_day(self):
        """If no day is supplied, an error should be returned"""
        del self.day1_data['day']
        response = self.client.post(self.create_url, self.day1_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_invalid_day(self):
        """If incorrect day is supplied, an error should be returned"""
        self.day1_data['day'] = 'foo'
        response = self.client.post(self.create_url, self.day1_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_over_range_day(self):
        """If day is supplied but out of range, an error should be returned"""
        self.day1_data['day'] = 2
        response = self.client.post(self.create_url, self.day1_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_under_range_day(self):
        """If day is supplied but out of range, an error should be returned"""
        self.day1_data['day'] = -1
        response = self.client.post(self.create_url, self.day1_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
