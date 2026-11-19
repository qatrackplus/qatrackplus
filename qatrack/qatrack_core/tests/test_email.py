"""send_email_to_users reports whether it sent anything (scheduled sends rely on it, issue #919)."""

from smtplib import SMTPException
from unittest import mock

import pytest
from django.core import mail
from django.test.utils import override_settings

from qatrack.qatrack_core.email import send_email_to_users

TEMPLATE = "qcscheduling/email.html"


@pytest.fixture(autouse=True)
def plain_context():
    # email_context() looks up the Site; this module tests only the return value
    with mock.patch("qatrack.qatrack_core.email.email_context", side_effect=lambda context: context or {}), \
            mock.patch("qatrack.qatrack_core.email.render_to_string", return_value="<p>body</p>"):
        yield


def test_returns_true_when_sent():
    assert send_email_to_users(["a@example.com"], TEMPLATE) is True
    assert len(mail.outbox) == 1


def test_returns_false_with_no_recipients():
    assert send_email_to_users([], TEMPLATE) is False


def test_returns_false_when_every_recipient_is_blank():
    """Django's send() drops blank addresses and returns 0, having sent nothing"""
    assert send_email_to_users([""], TEMPLATE) is False
    assert len(mail.outbox) == 0


@override_settings(EMAIL_FAIL_SILENTLY=True)
def test_returns_false_when_a_send_fails_silently():
    with mock.patch("qatrack.qatrack_core.email.EmailMultiAlternatives.send", side_effect=SMTPException):
        assert send_email_to_users(["a@example.com"], TEMPLATE) is False


@override_settings(EMAIL_FAIL_SILENTLY=False)
def test_raises_when_a_send_fails_and_failures_are_not_silent():
    with mock.patch("qatrack.qatrack_core.email.EmailMultiAlternatives.send", side_effect=SMTPException):
        with pytest.raises(SMTPException):
            send_email_to_users(["a@example.com"], TEMPLATE)
