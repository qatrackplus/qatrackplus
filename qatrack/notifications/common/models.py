from django.contrib.auth.models import Group, User
from django.db import models
from django.utils.translation import gettext_lazy as _l

# this import has to be here so that the signal handlers get registered
from qatrack.notifications.faults import handlers as faults_handlers  # noqa: F401
from qatrack.notifications.faults_review import \
    handlers as faults_review_handlers  # noqa: F401
from qatrack.notifications.parts import handlers as part_handlers  # noqa: F401
from qatrack.notifications.qccompleted import handlers as qccompleted_handlers  # noqa: F401
from qatrack.notifications.qcreview import handlers as qcreview_handlers  # noqa: F401
from qatrack.notifications.qcscheduling import handlers as qcscheduling_handlers  # noqa: F401
from qatrack.notifications.service_log import handlers as service_log_handlers  # noqa: F401
from qatrack.notifications.service_log_scheduling import \
    handlers as service_log_scheduling_handlers  # noqa: F401
from qatrack.qa.models import TestList
from qatrack.units.models import Unit


class RecipientGroup(models.Model):

    name = models.CharField(
        max_length=255,
        help_text=_l("Enter a name for this group of recipients"),
    )

    groups = models.ManyToManyField(
        Group,
        help_text=_l("Select which groups this notification should be sent to."),
        blank=True,
    )

    users = models.ManyToManyField(
        User,
        help_text=_l("Select individual users to include in these notifications"),
        blank=True,
    )

    emails = models.TextField(
        verbose_name=_l("Extra recipient emails"),
        help_text=_l("Enter a comma separated list of extra emails this report should be sent to"),
        blank=True
    )

    def recipient_emails(self):
        users = set(self.users.filter(is_active=True).exclude(email='').values_list("email", flat=True))
        group_users = set(
            email for email, active in self.groups.values_list("user__email", "user__is_active") if active and email
        )
        emails = {x.strip() for x in self.emails.split(",") if x.strip()}
        return users | group_users | emails

    def _sort_emails(self):
        self.emails = ', '.join(sorted(e.strip() for e in self.emails.split(",")))

    def save(self, *args, **kwargs):
        self._sort_emails()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TestListGroup(models.Model):

    name = models.CharField(max_length=255, help_text=_l("Enter a name for this group of TestLists"))

    test_lists = models.ManyToManyField(
        TestList,
        help_text=_l(
            "Select which Test Lists should be included in this notification group."
        ),
    )

    __test__ = False  # supress pytest warning

    def __str__(self):
        return self.name


class UnitGroup(models.Model):

    name = models.CharField(max_length=255, help_text=_l("Enter a name for this group of Units"))

    units = models.ManyToManyField(
        Unit,
        help_text=_l(
            "Select which Units should be included in this notification group."
        ),
    )

    def __str__(self):
        return self.name
