from croniter import croniter
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils import timezone


def do_scheduling(sender, **kwargs):
    from qatrack.qatrack_core.tasks import _schedule_periodic_task

    cron = "0 4 * * *"  # Django Q runs as localtime (https://github.com/Koed00/django-q/pull/520)
    next_run = croniter(cron, timezone.localtime()).get_next(timezone.datetime)
    _schedule_periodic_task(
        "qatrack.qa.tasks.clean_autosaves",
        "QATrack+ Autosave Cleaner",
        cron=cron,
        next_run=next_run,
    )


def rebuild_trees(sender, **kwargs):
    from qatrack.qa.models import Category
    Category.objects.rebuild()


class QAAppConfig(AppConfig):
    name = 'qatrack.qa'
    verbose_name = "QC"

    def ready(self):
        post_migrate.connect(do_scheduling, sender=self)
        post_migrate.connect(rebuild_trees, sender=self)
