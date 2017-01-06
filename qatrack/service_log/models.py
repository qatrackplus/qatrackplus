
import json
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import User, Group
from django.template import Context
from django.template.loader import get_template
from django.utils import timezone
from django.utils.translation import ugettext as _

from qatrack.units.models import Unit, Vendor
from qatrack.qa.models import UnitTestCollection, TestListInstance
from qatrack.qa import utils

re_255 = '([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])'
color_re = re.compile('^rgba\(' + re_255 + ',' + re_255 + ',' + re_255 + ',(0(\.[0-9][0-9]?)?|1)\)$')
validate_color = RegexValidator(color_re, _('Enter a valid color.'), 'invalid')


class ServiceArea(models.Model):

    name = models.CharField(max_length=32, unique=True, help_text=_('Enter a short name for this service area'))
    units = models.ManyToManyField(Unit, through='UnitServiceArea', related_name='service_areas')

    def __str__(self):
        return self.name

    # @staticmethod
    # def get_for_unit(unit):
    #     usacs = UnitServiceArea.objects.filter(
    #         unit=unit
    #     ).values_list('service_area__pk', flat=True)
    #
    #     return ServiceArea.objects.filter(pk__in=usacs)


class UnitServiceArea(models.Model):

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    service_area = models.ForeignKey(ServiceArea, on_delete=models.CASCADE)

    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name_plural = _('Unit Service Area Memberships')
        unique_together = ('unit', 'service_area',)
        ordering = ('unit', 'service_area')

    def __str__(self):
        return '<usa(%s::%s)>' % (self.unit.name, self.service_area.name)


class ServiceType(models.Model):

    name = models.CharField(max_length=32, unique=True, help_text=_('Enter a short name for this service type'))
    is_approval_required = models.BooleanField(default=False, help_text=_('Does this service type require approval'))
    is_active = models.BooleanField(default=True, help_text=_('Set to false if service type is no longer used'))

    def __str__(self):
        return self.name


class ServiceEventStatus(models.Model):

    name = models.CharField(max_length=32, unique=True, help_text=_('Enter a short name for this service status'))
    is_default = models.BooleanField(
        default=False,
        help_text=_(
            'Is this the default status for all service events? If set to true every other service event '
            'status will be set to false'
        )
    )
    is_approval_required = models.BooleanField(
        default=True, help_text=_('Do service events with this status require approval?')
    )
    is_active = models.BooleanField(default=True, help_text=_('Set to false if service event status is no longer used'))
    description = models.TextField(
        max_length=64, help_text=_('Give a brief description of this service event status'), null=True, blank=True
    )
    colour = models.CharField(default=settings.DEFAULT_COLOURS[0], max_length=22, validators=[validate_color])

    class Meta:
        verbose_name_plural = _('Service Event Statuses')

    def save(self, *args, **kwargs):
        if self.is_default:
            try:
                temp = ServiceEventStatus.objects.get(is_default=True)
                if self != temp:
                    temp.is_default = False
                    temp.save()
            except ServiceEventStatus.DoesNotExist:
                pass
        super(ServiceEventStatus, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    @staticmethod
    def get_default():
        return ServiceEventStatus.objects.get(is_default=True)

    @staticmethod
    def get_colour_dict():
        # return json.dumps({se.id: se.service_status.colour for se in ServiceEvent.objects.all()})
        return {ses.id: ses.colour for ses in ServiceEventStatus.objects.all()}


class ProblemType(models.Model):
    """
    Short description of common occurring problem themes.
    """

    name = models.CharField(max_length=64, unique=True, help_text=_('Enter a short name for this problem type'))
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class ServiceEvent(models.Model):

    unit_service_area = models.ForeignKey(UnitServiceArea, on_delete=models.PROTECT)
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    service_event_related = models.ManyToManyField(
        'self', symmetrical=True, blank=True, verbose_name=_('Service events related'),
        help_text=_('Was there a previous service event that might be related to this event?')
    )
    service_status = models.ForeignKey(ServiceEventStatus, verbose_name=_('Status'), on_delete=models.PROTECT)

    user_status_changed_by = models.ForeignKey(User, null=True, blank=True, related_name='+', on_delete=models.PROTECT)
    user_created_by = models.ForeignKey(User, related_name='+', on_delete=models.PROTECT)
    user_modified_by = models.ForeignKey(User, null=True, blank=True, related_name='+', on_delete=models.PROTECT)
    problem_type = models.ForeignKey(
        ProblemType, null=True, blank=True, on_delete=models.PROTECT,
        help_text=_('Select/create a problem type that describes this service event')
    )

    datetime_status_changed = models.DateTimeField(null=True, blank=True)
    datetime_created = models.DateTimeField()
    datetime_service = models.DateTimeField(
        verbose_name=_('Date and time'), help_text=_('Date and time this event took place')
    )
    datetime_modified = models.DateTimeField(null=True, blank=True)

    safety_precautions = models.TextField(
        null=True, blank=True, help_text=_('Were any special safety precautions taken?')
    )
    problem_description = models.TextField(help_text=_('Describe the problem leading to this service event'))
    work_description = models.TextField(
        null=True, blank=True, help_text=_('Describe the work done during this service event')
    )
    duration_service_time = models.DurationField(
        verbose_name=_('Service time'), null=True, blank=True,
        help_text=_('Enter the total time duration of this service event')
    )
    duration_lost_time = models.DurationField(
        verbose_name=_('Lost time'), null=True, blank=True,
        help_text=_('Enter the total clinical time lost for this service event')
    )
    is_approval_required = models.BooleanField(
        default=False, help_text=_('Does this service event require approval?'), blank=True
    )

    class Meta:
        get_latest_by = "datetime_service"
        default_permissions = ()

        permissions = (
            ("can_approve_service_event", "Can Approve Service Event"),
        )

    def __str__(self):
        return 'id: %s' % self.id

    # def get_colour_dict():
    #     # return json.dumps({se.id: se.service_status.colour for se in ServiceEvent.objects.all()})
    #     return {se.id: se.service_status.colour for se in ServiceEvent.objects.all()}


class ThirdParty(models.Model):

    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)

    first_name = models.CharField(max_length=32, help_text=_('Enter this person\'s first name'))
    last_name = models.CharField(max_length=32, help_text=_('Enter this person\'s last name'))

    class Meta:
        verbose_name = _('Third Party')
        verbose_name_plural = _('Third Parties')
        unique_together = ('first_name', 'last_name', 'vendor')

    def __str__(self):
        return self.last_name + ', ' + self.first_name + ' (' + self.vendor.name + ')'

    def get_full_name(self):
        return self.first_name + ' ' + self.last_name + ' (' + self.vendor.name + ')'


class Hours(models.Model):

    service_event = models.ForeignKey(ServiceEvent, on_delete=models.PROTECT)
    third_party = models.ForeignKey(ThirdParty, null=True, blank=True, on_delete=models.PROTECT)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)

    time = models.DurationField(help_text=_('The time this person spent on this service event'))

    class Meta:
        verbose_name_plural = _("Hours")
        unique_together = ('service_event', 'third_party', 'user',)

        permissions = (
            ("can_have_hours", "Can have hours"),
        )

    def user_or_thirdparty(self):
        return self.user or self.third_party


class QAFollowup(models.Model):

    unit_test_collection = models.ForeignKey(
        UnitTestCollection, help_text=_('Select a TestList to perform'), on_delete=models.PROTECT
    )
    test_list_instance = models.ForeignKey(TestListInstance, null=True, blank=True, on_delete=models.CASCADE)
    user_assigned_by = models.ForeignKey(User, related_name='+', on_delete=models.PROTECT)
    service_event = models.ForeignKey(ServiceEvent, on_delete=models.PROTECT)

    is_complete = models.BooleanField(default=False, help_text=_('Has this QA been completed?'))
    is_approved = models.BooleanField(default=False, help_text=_('Has the QA been approved?'))
    datetime_assigned = models.DateTimeField()


class GroupLinker(models.Model):

    group = models.ForeignKey(Group, help_text=_('Select the group.'))

    name = models.CharField(
        max_length=64, help_text=_('Enter this group\'s display name (ie: "Physicist reported to")')
    )
    description = models.TextField(
        null=True, blank=True, help_text=_('Describe the relationship between this group and service events.')
    )
    help_text = models.CharField(
        max_length=64, null=True, blank=True,
        help_text=_('Message to display when selecting user in service event form.')
    )

    class Meta:
        unique_together = ('name', 'group')

    def __str__(self):
        return self.name


class GroupLinkerInstance(models.Model):

    group_linker = models.ForeignKey(GroupLinker, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    service_event = models.ForeignKey(ServiceEvent, on_delete=models.PROTECT)

    datetime_linked = models.DateTimeField()

    class Meta:
        unique_together = ('service_event', 'group_linker')

