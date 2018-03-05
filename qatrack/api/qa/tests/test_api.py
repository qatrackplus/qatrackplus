from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from qatrack.qa import models
from qatrack.qa.tests import utils


class TestTestListInstanceAPI(APITestCase):

    def setUp(self):

        self.unit = utils.create_unit()
        self.simple_test_list = utils.create_test_list("simple")
        self.t1 = utils.create_test(name="test1")
        self.t2 = utils.create_test(name="test2")

        # self.tc = utils.create_test(name="testc", test_type=models.COMPOSITE)
        # self.tc.calculation_procedure = "result = test1 + test2"
        # self.tc.save()
        for t in [self.t1, self.t2]:
            utils.create_test_list_membership(self.simple_test_list, t)

        self.unit_test_list = utils.create_unit_test_collection(test_collection=self.simple_test_list, unit=self.unit)

        self.create_url = reverse('testlistinstance-list')
        self.utc_url = reverse("unittestcollection-detail", kwargs={'pk': self.unit_test_list.pk})

        self.simple_data = {
            'unit_test_collection': self.utc_url,
            'work_completed': '2019-07-25 10:49:47',
            'work_started': '2019-07-25 10:49:00',
            'tests': {
                'test1': {'value': 1},
                'test2': {'value': 2},
            },
        }

        self.client.login(username="user", password="password")
        self.status = utils.create_status()

    def test_create_no_status(self):
        models.TestInstanceStatus.objects.all().delete()
        response = self.client.post(self.create_url, self.simple_data)
        assert response.data == ['No test instance status available']

    def test_create_simple(self):
        response = self.client.post(self.create_url, self.simple_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(models.TestListInstance.objects.count(), 1)
        self.assertEqual(models.TestInstance.objects.count(), 2)
