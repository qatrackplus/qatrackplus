from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from qatrack.qa.tests import utils as qa_utils
from qatrack.service_log import models


class TestServiceEventStatusAdmin(TestCase):

    def setUp(self):

        self.user = qa_utils.create_user(is_superuser=True)
        self.client.login(username='user', password='password')

        self.url_add = reverse(
            'admin:%s_%s_add' % (models.ServiceEventStatus._meta.app_label, models.ServiceEventStatus._meta.model_name)
        )
        self.data = {
            'name': 'status_name',
            'is_default': True,
            'is_review_required': False,
            'rts_must_be_reviewed': False,
            'colour': settings.DEFAULT_COLOURS[0],
            'description': 'test description',
            'order': 0,
        }

    def test_clean_is_default(self):

        response = self.client.get(self.url_add)

        self.client.post(self.url_add, data=self.data)

        url_change = reverse(
            'admin:%s_%s_change' % (models.ServiceEventStatus._meta.app_label, models.ServiceEventStatus._meta.model_name),
            args=[models.ServiceEventStatus.get_default().id]
        )
        self.data['is_default'] = False
        response = self.client.post(url_change, data=self.data)
        self.assertTrue('is_default' in response.context_data['adminform'].form.errors)

    def test_new_not_default(self):

        data = self.data
        data['is_default'] = False

        self.client.post(self.url_add, data=data)
