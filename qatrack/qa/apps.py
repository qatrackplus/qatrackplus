from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils import timezone
from django.utils.translation import gettext_lazy as _l


def do_scheduling(sender, **kwargs):
    from django_q.models import Schedule

    from qatrack.qatrack_core.tasks import _schedule_periodic_task

    _schedule_periodic_task(
        "qatrack.qa.tasks.clean_autosaves",
        "QATrack+ Autosave Cleaner",
        schedule_type=Schedule.DAILY,
        next_run=timezone.localtime(timezone.now() + timezone.timedelta(hours=24)).replace(hour=4),
    )


def rebuild_trees(sender, **kwargs):
    from qatrack.qa.models import Category
    Category.objects.rebuild()


class QAAppConfig(AppConfig):
    name = 'qatrack.qa'
    verbose_name = _l("QC")

    def ready(self):
        post_migrate.connect(do_scheduling, sender=self)
        post_migrate.connect(rebuild_trees, sender=self)
        import qatrack.qa.signals  # noqa
