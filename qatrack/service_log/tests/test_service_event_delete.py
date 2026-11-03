"""The delete view once somebody is allowed to use it.

Who may reach it at all is `test_permission_mixin_order.py`. This covers what
happens after that: a delete the form rejects.

`reason` is a required `ChoiceField` over `settings.DELETE_REASONS`, so a POST
without it - or with a value outside the choices - is an ordinary thing for a
client to send. It arrives from a hand-built POST, from a page left open while
`DELETE_REASONS` changed, and from any client that is not the form.
"""

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from qatrack.service_log.tests import utils as sl_utils


class TestDeleteServiceEventWithAReasonTheFormRejects(TestCase):

    def setUp(self):
        # The dashboard redirects to configuration without a default status, which would hide its messages.
        sl_utils.create_service_event_status(is_default=True)
        self.service_event = sl_utils.create_service_event()
        user = User.objects.create_user('se-deleter', 'd@example.com', 'pw')
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='service_log',
                codename='delete_serviceevent',
            )
        )
        # Re-read, so the permission cache on the instance does not hide it.
        self.client.force_login(User.objects.get(pk=user.pk))
        self.url = reverse('se_delete', kwargs={'pk': self.service_event.pk})

    def test_a_post_with_no_reason_redirects_rather_than_raising(self):
        """form_invalid() returned the URL string instead of a response.

        Django has nothing to do with a `str` from a view, so the request ended
        as a 500 - a server error for what is really a rejected input. The test
        client re-raises, so before the fix this errors rather than fails.
        """
        response = self.client.post(self.url, {})

        assert response.status_code == 302, response.status_code
        assert response['Location'] == reverse('sl_dash')

    def test_a_post_with_a_reason_outside_the_choices_redirects(self):
        response = self.client.post(self.url, {'reason': 'whatever-i-like'})

        assert response.status_code == 302, response.status_code

    def test_a_rejected_delete_leaves_the_service_event_active(self):
        """The point of the whole thing: nothing is deleted on the way out."""
        self.client.post(self.url, {})

        self.service_event.refresh_from_db()
        assert self.service_event.is_active

    def test_the_person_is_told_the_delete_did_not_happen(self):
        """Otherwise a redirect to the dashboard looks like success."""
        response = self.client.post(self.url, {}, follow=True)

        assert response.resolver_match.url_name == 'sl_dash'
        messages = [str(m) for m in response.context['messages']]
        assert f'Could not delete service event {self.service_event.pk}' in messages, messages

    def test_a_valid_reason_still_deletes(self):
        """The negative control: the tests above would pass on a broken view."""
        response = self.client.post(self.url, {'reason': 'Duplicate', 'comment': ''})

        assert response.status_code == 302
        self.service_event.refresh_from_db()
        assert not self.service_event.is_active
