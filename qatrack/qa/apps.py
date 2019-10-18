from django.apps import AppConfig
from django.db.models.signals import post_migrate


def do_scheduling(sender, **kwargs):
    from qatrack.qa.tasks import schedule_tasks

    schedule_tasks()


class QAAppConfig(AppConfig):
    name = 'qatrack.qa'
    verbose_name = "QC"

    def ready(self):
        post_migrate.connect(do_scheduling, sender=self)
