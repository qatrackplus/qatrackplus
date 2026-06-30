from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _l


class IssueTrackerConfig(AppConfig):
    name = 'qatrack.issue_tracker'
    verbose_name = _l("Issue Tracker") 