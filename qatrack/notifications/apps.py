from django.apps import AppConfig
from django.db.models.signals import post_migrate


def do_scheduling(sender, **kwargs):
    from qatrack.qatrack_core.tasks import _schedule_periodic_task

    _schedule_periodic_task(
        "qatrack.notifications.qcscheduling.tasks.run_scheduling_notices",
        "QATrack+ Scheduling Notices",
    )


class NotificationsConfig(AppConfig):

    name = 'qatrack.notifications'

    def ready(self):
        post_migrate.connect(do_scheduling, sender=self)
