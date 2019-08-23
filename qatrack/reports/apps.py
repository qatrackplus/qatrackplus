from django.apps import AppConfig
from django.db.models.signals import post_migrate


def do_scheduling(sender, **kwargs):
    from qatrack.reports.tasks import _schedule_tasks

    _schedule_tasks()


class ReportsConfig(AppConfig):

    name = 'qatrack.reports'

    def ready(self):
        post_migrate.connect(do_scheduling, sender=self)
