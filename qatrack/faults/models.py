from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _l
from django_comments.models import Comment
from django.db.models.signals import pre_save
from django.dispatch import receiver

from qatrack.qatrack_core.utils import unique_slug_generator
from qatrack.units import models as u_models


class FaultType(models.Model):

    code = models.CharField(
        _l("code"),
        max_length=255,
        unique=True,
        help_text=_l('Enter the fault code or number'),
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
        super().save(*args,**kwargs)

    def __str__(self):
        return self.code


#@receiver(pre_save, sender=FaultType)
#def create_fault_type_slug(sender, instance, *args, **kwargs):
#    import ipdb; ipdb.set_trace()  # yapf: disable  # noqa
#    instance.slug = unique_slug_generator(instance, instance.code)


class FaultManager(models.Manager):

    def unreviewed(self):
        return self.filter(reviewed_by=None).order_by("-occurred")


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
        verbose_name=_l("modality"),
        on_delete=models.SET_NULL,
        related_name="faults",
        null=True,
        blank=True,
        help_text=_l("Select the modality being used when this fault occurred (optional)"),
    )

    treatment_technique = models.ForeignKey(
        u_models.TreatmentTechnique,
        verbose_name=_l("treatment technique"),
        on_delete=models.SET_NULL,
        related_name="faults",
        null=True,
        blank=True,
        help_text=_l("Select the treatment technique being used when this fault occurred (optional)"),
    )

    fault_type = models.ForeignKey(
        FaultType,
        on_delete=models.PROTECT,
        verbose_name=_l("fault type"),
        help_text=_l("Select the fault type that occurred"),
    )

    occurred = models.DateTimeField(
        verbose_name=_l("Date & Time fault occurred on"),
        default=timezone.now,
        help_text="When did this fault occur. " + settings.DATETIME_HELP,
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
        related_name="fault_reviewer",
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

    def __str__(self):
        return "Fault ID: %d" % self.pk
