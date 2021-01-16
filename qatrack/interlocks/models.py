from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _l
from django_comments.models import Comment

from qatrack.units import models as u_models


class InterlockType(models.Model):

    code = models.CharField(
        _l("code"),
        max_length=255,
        unique=True,
        help_text=_l('Enter the interlock code or number'),
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text=_l("Unique URL friendly identifier made of lowercase characters, dashes, and underscores.")
    )

    description = models.TextField(
        _l("description"),
        help_text=_l("Enter a description for this interlock type"),
    )

    def __str__(self):
        return self.code


class Interlock(models.Model):

    unit = models.ForeignKey(
        u_models.Unit,
        verbose_name=_l("unit"),
        on_delete=models.CASCADE,
        related_name="interlocks",
        help_text=_l("Select the unit this fault occurred on"),
    )

    modality = models.ForeignKey(
        u_models.Modality,
        verbose_name=_l("modality"),
        on_delete=models.SET_NULL,
        related_name="interlocks",
        null=True,
        blank=True,
        help_text=_l("Select the modality being used when this fault occurred"),
    )

    interlock_type = models.ForeignKey(
        InterlockType,
        on_delete=models.PROTECT,
        verbose_name=_l("interlock type"),
        help_text=_l("Select the interlock type that occurred"),
    )

    occurred_on = models.DateTimeField(
        verbose_name=_l("Date & Time interlock occurred on"),
        default=timezone.now,
        help_text="When did this interlock occur. " + settings.DATETIME_HELP,
        db_index=True
    )

    comments = GenericRelation(Comment)

    reviewed = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        editable=False,
        null=True,
        blank=True,
        related_name="interlock_reviewer",
    )

    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        editable=False,
        related_name="interlock_events_created",
    )
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        editable=False,
        related_name="interlock_events_modified",
    )

    class Meta:
        ordering = ("-occurred_on",)

    def __str__(self):
        return "Interlock ID: %d" % self.pk
