from django.contrib.auth.models import User
from django.db.models import Q

from qatrack.notifications.handlers import send_notice_to_users
from qatrack.qa.models import TestListInstance


def send_follow_up_email(test_list_instance_id=None, notification_id=None):
    """Task to do the actual sending of the follow up emails"""

    from qatrack.notifications.models import NotificationSubscription

    tli = TestListInstance.objects.filter(pk=test_list_instance_id).first()
    sub = NotificationSubscription.objects.filter(id=notification_id).first()
    if not (tli and sub):
        return

    users = User.objects.filter(is_active=True).exclude(email='')
    recipients = users.filter(
        Q(groups__notificationsubscriptions=sub) |
        Q(notificationsubscriptions=sub)
    ).distinct()

    send_notice_to_users("follow_up", recipients, {'test_list_instance': tli})
