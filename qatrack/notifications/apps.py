from django.apps import AppConfig
from django.db.models.signals import post_migrate


def do_scheduling(sender, **kwargs):
    from qatrack.qatrack_core.tasks import _schedule_periodic_task

    periodic_notifications = [
        (
            "qatrack.notifications.qcscheduling.tasks.run_scheduling_notices",
            "QATrack+ Scheduling Notices",
        ),
        (
            "qatrack.notifications.qcreview.tasks.run_review_notices",
            "QATrack+ Review Notices",
        ),
        (
            "qatrack.notifications.service_log_review.tasks.run_service_event_review_notices",
            "QATrack+ Service Event Review Notices",
        ),
        (
            "qatrack.notifications.faults_review.tasks.run_faults_review_notices",
            "QATrack+ Fault Review Notices",
        ),
    ]
    for func, name in periodic_notifications:
        _schedule_periodic_task(func, name)


class NotificationsConfig(AppConfig):

    name = 'qatrack.notifications'

    def ready(self):
        post_migrate.connect(do_scheduling, sender=self)
