
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.utils.translation import ugettext as _

from qatrack.units.models import Unit, Vendor
from qatrack.qa.models import UnitTestCollection, TestListInstance
from qatrack.qa import utils


class ServiceArea(models.Model):

    name = models.CharField(max_length=32, unique=True, help_text=_('Enter a short name for this service area'))


class UnitServiceAreaCollection(models.Model):

    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    service_area = models.ForeignKey(ServiceArea, on_delete=models.PROTECT)


class ServiceType(models.Model):

    name = models.CharField(max_length=32, unique=True, help_text=_('Enter a short name for this service type'))
    is_approval_required = models.BooleanField(default=False, help_text=_('Does this service type require approval'))
    is_active = models.BooleanField(defaul=True, help_text=_('Set to false if service type is no longer used'))


class ServiceEventStatus(models.Model):

    name = models.CharField(max_length=32, unique=True, help_text=_('Enter a short name for this service status'))
    is_default = models.BooleanField(default=False, help_text=_('Is this the default status for all service events? If set to True every other service event status will be set to False'))
    is_review_required = models.BooleanField(default=True, help_text=_('Do service events with this status require review?'))
    is_active = models.BooleanField(default=True, help_text=_('Set to false if service event status is no longer used'))
    description = models.TextField(max_length=64, help_text=_('Give a brief description of this service event status'), null=True, blank=True)

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


class ProblemType(models.Model):

    name = models.CharField(max_length=32, unique=True, help_text=_('Enter a short name for this problem type'))


class ServiceEvent(models.Model):

    unit_service_area_collection = models.ForeignKey(UnitServiceAreaCollection, on_delete=models.PROTECT)
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    service_event_related = models.ManyToManyField('self', symmetrical=True, null=True, blank=True, help_text=_('Was there a previous service event that might be related to this event?'), on_delete=models.PROTECT)
    service_status = models.ForeignKey(ServiceEventStatus, on_delete=models.PROTECT)
    user_physicist_reported_to = models.ForeignKey(User, null=True, blank=True, related_name='+', help_text=_('Has a physicist been notified of this service event?'), on_delete=models.PROTECT)
    user_therapist_reported_to = models.ForeignKey(User, null=True, blank=True, related_name='+', help_text=_('Has a therapist been notified of this service event?'), on_delete=models.PROTECT)
    user_status_changed_by = models.ForeignKey(User, null=True, blank=True, related_name='+', on_delete=models.PROTECT)
    user_created_by = models.ForeignKey(User, related_name='+', on_delete=models.PROTECT)
    user_modified_by = models.ForeignKey(User, related_name='+', on_delete=models.PROTECT)
    problem_type = models.ForeignKey(null=True, blank=True, help_text=_('Select/create a problem type that describes this service event'), on_delete=models.PROTECT)

    datetime_status_changed = models.DateTimeField(null=True, blank=True)
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_service = models.DateTimeField(help_text=_('Date and time this event took place'))
    datetime_modified = models.DateTimeField(auto_now=True)

    srn = models.IntegerField(null=True, blank=True)  # TODO: Char field?
    safety_precautions = models.TextField(null=True, blank=True, help_text=_('Were any special safety precautions taken?'))
    problem_description = models.TextField(help_text=_('Describe the problem leading to this service event'))
    work_description = models.TextField(null=True, blank=True, help_text=_('Describe the work done during this service event'))
    duration_service_time = models.DurationField(null=True, blank=True, help_text=_('Enter the total time duration of this service event'))
    duration_lost_time = models.DurationField(null=True, blank=True, help_text=_('Enter the total clinical time lost for this service event'))

    # TODO:
    # class Meta:
    #
    #     permissions = (
    #         ("can_view_overview", "Can view program overview"),
    #         ("can_review_non_visible_tli", "Can view tli and utc not visible to user's groups")
    #     )


class ThirdParty(models.Model):

    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)

    name = models.CharField(max_length=32, unique=True, help_text=_('Enter a short name for this person'))


class Hours(models.Model):

    service_event = models.ForeignKey(ServiceEvent, on_delete=models.PROTECT)
    third_party = models.ForeignKey(ThirdParty, null=True, blank=True, on_delete=models.PROTECT)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)

    time = models.DurationField(help_text=_('The time this person spent on this service event'))

    def clean(self):
        super(Hours, self).clean()
        if bool(self.third_party) ^ bool(self.user):  # xor thirdparty and user (one and only one must be selected
            raise ValidationError('One of third party or user must be entered')


class QAFollowup(models.Model):

    unit_test_collection = models.ForeignKey(UnitTestCollection, help_text=_('Select a TestList to perform'), on_delete=models.PROTECT)
    test_list_instance = models.ForeignKey(TestListInstance, null=True, blank=True, on_delete=models.PROTECT)
    user_assigned_by = models.ForeignKey(User, related_name='+', on_delete=models.PROTECT)
    service_event = models.ForeignKey(ServiceEvent, on_delete=models.PROTECT)

    is_complete = models.BooleanField(help_text=_('Has this QA been completed?'))




