from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _l
from django_comments.models import Comment

from qatrack.qatrack_core.utils import unique_slug_generator
from qatrack.service_log import models as sl_models
from qatrack.units import models as u_models


def can_review_faults(user):
    """
     users can review faults if one of the the following applies:
        a) No fault review groups exist and they have can_review permissions
        b) Fault review groups exist, they are a member of one, and they have
           review permissions
    """

    can_review = user.has_perm("faults.can_review")
    review_groups = [frg.group for frg in FaultReviewGroup.objects.select_related("group")]
    if review_groups:
        can_review = can_review and len(set(review_groups) & set(user.groups.all())) > 0
    return can_review


class FaultType(models.Model):

    code = models.CharField(
        _l("code"),
        max_length=255,
        help_text=_l('Enter the fault code or number'),
        db_index=True,
    )
    slug = models.SlugField(
        max_length=255,
        editable=False,
        unique=True,
        help_text=_l("Unique URL friendly identifier made of lowercase characters, dashes, and underscores.")
    )

    description = models.TextField(
        _l("description"),
        help_text=_l("Enter a description for this fault type"),
        blank=True,
    )

    class Meta:
        ordering = ("code",)

    def save(self, *args, **kwargs):
        self.slug = unique_slug_generator(self, self.code)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class FaultManager(models.Manager):

    def unreviewed(self):
        return self.filter(faultreviewinstance=None).order_by("-occurred")

    def unreviewed_count(self):
        return self.unreviewed().count()


class Fault(models.Model):

    unit = models.ForeignKey(
        u_models.Unit,
        verbose_name=_l("unit"),
        on_delete=models.CASCADE,
        related_name="faults",
        help_text=_l("Select the unit this fault occurred on"),
    )

    modality = models.ForeignKey(
        u_models.Modality,
        verbose_name=_l("treatment/imaging technique or modality"),
        on_delete=models.SET_NULL,
        related_name="faults",
        null=True,
        blank=True,
        help_text=_l("Select the treatment/imaging modality being used when this fault occurred (optional)"),
    )

    fault_types = models.ManyToManyField(
        FaultType,
        verbose_name=_l("fault types"),
        help_text=_l("Select the fault types that occurred"),
        related_name="faults",
    )

    occurred = models.DateTimeField(
        verbose_name=_l("Date & Time fault occurred"),
        default=timezone.now,
        help_text="When did this fault occur. " + settings.DATETIME_HELP,
        db_index=True
    )

    related_service_events = models.ManyToManyField(
        sl_models.ServiceEvent,
        blank=True,
        verbose_name=_l('related service events'),
        help_text=_l('Enter the service event IDs of any related service events.')
    )

    comments = GenericRelation(
        Comment,
        object_id_field="object_pk",
    )

    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        editable=False,
        related_name="fault_events_created",
    )
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        editable=False,
        related_name="fault_events_modified",
    )

    objects = FaultManager()

    class Meta:
        ordering = ("-occurred",)
        permissions = (("can_review", _l("Can review faults")),)

    def get_absolute_url(self):
        return reverse("fault_details", kwargs={"pk": self.pk})

    def review_complete(self):
        details = self.review_details()
        at_least_one_done = False
        required_completed = True
        for rg, user, date, required in details:
            at_least_one_done = at_least_one_done or user
            if required:
                required_completed = required_completed and user
        return at_least_one_done and required_completed

    def review_details(self):
        review_groups = FaultReviewGroup.objects.order_by("-required", "group__name")
        review_group_instances = self.faultreviewinstance_set.order_by(
            "-fault_review_group__required",
            "fault_review_group__group__name",
        ).select_related(
            "fault_review_group",
            "fault_review_group__group",
        )
        if review_groups:

            review_group_instances_by_group = {}

            for frgi in review_group_instances:
                if frgi.fault_review_group_id:
                    review_group_instances_by_group[frgi.fault_review_group_id] = frgi

            review_details = []
            for review_group in review_groups:
                review_group_instance = review_group_instances_by_group.get(review_group.id)
                reviewed = review_group_instance.reviewed if review_group_instance else None
                reviewed_by = review_group_instance.reviewed_by if review_group_instance else None
                review_details.append((review_group.group.name, reviewed_by, reviewed, review_group.required))

        else:
            review_details = [(None, frgi.reviewed_by, frgi.reviewed, False) for frgi in review_group_instances]

        return review_details

    def fault_types_display(self):
        return ','.join(ft.code for ft in self.fault_types.order_by("code"))

    def __str__(self):
        return "Fault ID: %d" % self.pk


class FaultReviewGroup(models.Model):

    group = models.OneToOneField(
        Group,
        verbose_name=_l("group"),
        on_delete=models.PROTECT,
        help_text=_l("Select the group responsible for reviewing a fault"),
        unique=True,
    )

    required = models.BooleanField(
        _l("required"),
        help_text=_l("Is review by this group required in order to consider a fault reviewed"),
        default=True,
    )


class FaultReviewInstance(models.Model):

    reviewed = models.DateTimeField(
        verbose_name=_l("review date & time"),
        auto_now_add=True,
        editable=False,
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        editable=False,
        related_name="faults_reviewed",
    )

    fault = models.ForeignKey(
        Fault,
        verbose_name=_l("fault"),
        on_delete=models.CASCADE,
    )

    fault_review_group = models.ForeignKey(
        FaultReviewGroup,
        verbose_name=_l("fault review group instance"),
        on_delete=models.SET_NULL,
        null=True,
    )
