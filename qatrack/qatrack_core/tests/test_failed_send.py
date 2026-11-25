"""A send that fails must leave the email unsent and unclaimed, for every notice sender (#919).

QC Scheduling notices and reports have this test beside their other tests
(test_qcs.py and the report tests), and the QC Completed follow-up has its own
in test_qcc.py. The four notice senders here repeat the same few lines around
the send, so one test is run against each of them.
"""

from smtplib import SMTPException
from unittest import mock

import pytest
from django.contrib.auth.models import Group, User
from django.core import mail

from qatrack.notifications.faults_review.tasks import send_faultsreview_notice
from qatrack.notifications.models import (
    FaultsReviewNotice,
    QCReviewNotice,
    RecipientGroup,
    ServiceEventReviewNotice,
    ServiceEventSchedulingNotice,
)
from qatrack.notifications.qcreview.tasks import send_qcreview_notice
from qatrack.notifications.service_log_review.tasks import (
    send_serviceeventreview_notice,
)
from qatrack.notifications.service_log_scheduling.tasks import (
    send_scheduling_notice,
)

SENDERS = [
    (QCReviewNotice, send_qcreview_notice, {}),
    (FaultsReviewNotice, send_faultsreview_notice, {}),
    (ServiceEventReviewNotice, send_serviceeventreview_notice, {}),
    (
        ServiceEventSchedulingNotice,
        send_scheduling_notice,
        {'notification_type': ServiceEventSchedulingNotice.UPCOMING_AND_DUE, 'future_days': 7},
    ),
]


@pytest.mark.django_db
@pytest.mark.parametrize('model, send, extra', SENDERS)
def test_failed_send_can_be_retried(model, send, extra):
    """A send that fails silently must not stop a later copy from sending"""
    group = Group.objects.create(name='group')
    User.objects.create_user('user', 'user@example.com', 'password').groups.add(group)
    recipients = RecipientGroup.objects.create(name='recipients')
    recipients.groups.add(group)
    notice = model.objects.create(
        recipients=recipients, recurrences='RRULE:FREQ=DAILY', time='0:00', send_empty=True, **extra
    )
    task_name = 'Send %s %d 2026-11-19T08:00:00-05:00' % (model.__name__, notice.pk)

    with mock.patch('qatrack.qatrack_core.email.EmailMultiAlternatives.send', side_effect=SMTPException):
        send(notice.pk, task_name)
    assert len(mail.outbox) == 0

    send(notice.pk, task_name)
    assert len(mail.outbox) == 1
