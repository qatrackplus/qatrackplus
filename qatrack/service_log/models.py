import json
import re

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import pre_save
from django.db.utils import IntegrityError
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _l

from qatrack.qa.models import TestListInstance, UnitTestCollection
from qatrack.qatrack_core.fields import JSONField
from qatrack.units.models import NameNaturalKeyManager, Unit, Vendor

re_255 = '([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])'
color_re = re.compile(r'^rgba\(' + re_255 + ',' + re_255 + ',' + re_255 + r',(0(\.[0-9][0-9]?)?|1)\)$')
validate_color = RegexValidator(color_re, _l('Enter a valid color.'), 'invalid')

NEW_SERVICE_EVENT = 'new_se'
MODIFIED_SERVICE_EVENT = 'mod_se'
STATUS_SERVICE_EVENT = 'stat_se'
CHANGED_RTSQA = 'rtsqa'
PERFORMED_RTS = 'perf_rts'
APPROVED_RTS = 'app_rts'
DELETED_SERVICE_EVENT = 'del_se'

LOG_TYPES = (
    (NEW_SERVICE_EVENT, 'New Service Event'),
    (MODIFIED_SERVICE_EVENT, 'Modified Service Event'),
    (STATUS_SERVICE_EVENT, 'Service Event Status Changed'),
    (CHANGED_RTSQA, 'Changed Return To Service'),
    (PERFORMED_RTS, 'Performed Return To Service'),
    (APPROVED_RTS, 'Approved Return To Service'),
    (DELETED_SERVICE_EVENT, 'Deleted Service Event')
)


class ServiceArea(models.Model):

    name = models.CharField(max_length=32, unique=True, help_text=_l('Enter a short name for this service area'))
    units = models.ManyToManyField(Unit, through='UnitServiceArea', related_name='service_areas')

    objects = NameNaturalKeyManager()

    class Meta:
        ordering = ("name",)

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name


class UnitServiceArea(models.Model):

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    service_area = models.ForeignKey(ServiceArea, on_delete=models.CASCADE)

    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name_plural = _l('Unit Service Area Memberships')
        unique_together = ('unit', 'service_area',)
        ordering = ('unit', 'service_area')

    def __str__(self):
        return '%s :: %s' % (self.unit.name, self.service_area.name)


class ServiceType(models.Model):

    name = models.CharField(max_length=32, unique=True, help_text=_l('Enter a short name for this service type'))
    is_review_required = models.BooleanField(
        default=True,
        help_text=_l('Enable this flag to disable the "Review Required" checkbox for new Service Events'),
    )
    is_active = models.BooleanField(default=True, help_text=_l('Set to false if service type is no longer used'))
    description = models.TextField(
        max_length=512, help_text=_l('Give a brief description of this service type'), null=True, blank=True
    )

    objects = NameNaturalKeyManager()

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name


class ServiceEventStatus(models.Model):

    name = models.CharField(max_length=32, unique=True, help_text=_l('Enter a short name for this service status'))
    is_default = models.BooleanField(
        default=False,
        help_text=_l(
            'Is this the default status for all service events? If set to true every other service event '
            'status will be set to false'
        )
    )
    is_review_required = models.BooleanField(
        default=True, help_text=_l('Do service events with this status require review?')
    )
    rts_qa_must_be_reviewed = models.BooleanField(
        default=True,
        verbose_name=_l("Return To Service (RTS) QC Must be Reviewed"),
        help_text=_l(
            'Service events with Return To Service (RTS) QC that has not been reviewed '
            'can not have this status selected if set to true.'
        ),
    )
    description = models.TextField(
        max_length=512, help_text=_l('Give a brief description of this service event status'), null=True, blank=True
    )
    colour = models.CharField(default=settings.DEFAULT_COLOURS[0], max_length=22, validators=[validate_color])
    order = models.PositiveIntegerField(
        verbose_name=_l("Order"),
        help_text=_l("Choose what ordering this status will be listed as in drop down controls"),
        default=0,
    )

    objects = NameNaturalKeyManager()

    class Meta:
        verbose_name_plural = _l('Service event statuses')
        ordering = ("order", "pk")

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

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name

    @staticmethod
    def get_default():
        try:
            default = ServiceEventStatus.objects.get(is_default=True)
        except ServiceEventStatus.DoesNotExist:
            return None
        return default

    @staticmethod
    def get_colour_dict():
        return {ses.id: ses.colour for ses in ServiceEventStatus.objects.all()}


class ServiceEventManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).filter(is_active=True)

    def get_deleted(self):
        return super().get_queryset().filter(is_active=False)


class ServiceEvent(models.Model):

    unit_service_area = models.ForeignKey(UnitServiceArea, on_delete=models.PROTECT)
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    service_event_related = models.ManyToManyField(
        'self', symmetrical=True, blank=True, verbose_name=_l('Related service events'),
        help_text=_l('Enter the service event IDs of any related service events.')
    )
    service_status = models.ForeignKey(ServiceEventStatus, verbose_name=_l('Status'), on_delete=models.PROTECT)

    user_status_changed_by = models.ForeignKey(User, null=True, blank=True, related_name='+', on_delete=models.PROTECT)
    user_created_by = models.ForeignKey(User, related_name='+', on_delete=models.PROTECT)
    user_modified_by = models.ForeignKey(User, null=True, blank=True, related_name='+', on_delete=models.PROTECT)
    test_list_instance_initiated_by = models.ForeignKey(
        TestListInstance,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='serviceevents_initiated'
    )

    datetime_status_changed = models.DateTimeField(null=True, blank=True)
    datetime_created = models.DateTimeField()
    datetime_service = models.DateTimeField(
        verbose_name=_l('Date and time'), help_text=_l('Date and time service performed')
    )
    datetime_modified = models.DateTimeField(null=True, blank=True)

    safety_precautions = models.TextField(
        null=True, blank=True, help_text=_l('Describe any safety precautions taken')
    )
    problem_description = models.TextField(help_text=_l('Describe the problem leading to this service event'))
    work_description = models.TextField(
        null=True, blank=True, help_text=_l('Describe the work done during this service event')
    )
    duration_service_time = models.DurationField(
        verbose_name=_l('Service time'), null=True, blank=True,
        help_text=_l('Enter the total time duration of this service event (Hours : minutes)')
    )
    duration_lost_time = models.DurationField(
        verbose_name=_l('Lost time'), null=True, blank=True,
        help_text=_l('Enter the total clinical time lost for this service event (Hours : minutes)')
    )
    is_review_required = models.BooleanField(
        default=True, blank=True
    )
    is_active = models.BooleanField(default=True, blank=True)

    objects = ServiceEventManager()
    all_objects = models.Manager()

    class Meta:
        get_latest_by = "datetime_service"

        permissions = (
            ('review_serviceevent', 'Can review service event'),
            ('view_serviceevent', 'Can review service event'),
        )
        default_permissions = ('add', 'change', 'delete',)

        ordering = ["-datetime_service"]

    def __str__(self):
        return str(self.id)

    def create_rts_log_details(self):
        rts_states = []
        for r in self.returntoserviceqa_set.all():

            utc = r.unit_test_collection
            if not r.test_list_instance:
                state = 'tli_incomplete'
                details = utc.name
            elif not r.test_list_instance.all_reviewed:
                state = 'tli_req_review'
                details = r.test_list_instance.test_list.name
            else:
                state = 'tli_reviewed'
                details = r.test_list_instance.test_list.name

            rts_states.append({'state': state, 'details': details})
        return rts_states

    def set_inactive(self):
        self.is_active = False
        self.save()

        parts_used = self.partused_set.all()
        for pu in parts_used:
            pu.add_back_to_storage()

    def set_active(self):
        self.is_active = True
        self.save()

        parts_used = self.partused_set.all()
        for pu in parts_used:
            pu.remove_from_storage()

    def get_absolute_url(self):
        return reverse("sl_details", kwargs={"pk": self.pk})


class ThirdPartyManager(models.Manager):

    def get_queryset(self):
        return super(ThirdPartyManager, self).get_queryset().select_related('vendor')


class ThirdParty(models.Model):

    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)

    first_name = models.CharField(max_length=32, help_text=_l('Enter this person\'s first name'))
    last_name = models.CharField(max_length=32, help_text=_l('Enter this person\'s last name'))

    objects = ThirdPartyManager()

    class Meta:
        verbose_name = _l('Third party')
        verbose_name_plural = _l('Third parties')
        unique_together = ('first_name', 'last_name', 'vendor')

    def __str__(self):
        return self.last_name + ', ' + self.first_name + ' (' + self.vendor.name + ')'

    def get_full_name(self):
        return str(self)


class Hours(models.Model):

    service_event = models.ForeignKey(ServiceEvent, on_delete=models.CASCADE)
    third_party = models.ForeignKey(ThirdParty, null=True, blank=True, on_delete=models.PROTECT)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)

    time = models.DurationField(help_text=_l('The time this person spent on this service event'))

    class Meta:
        verbose_name_plural = _l("Hours")
        unique_together = ('service_event', 'third_party', 'user',)

        default_permissions = ()
        permissions = (
            ("can_have_hours", "Can have hours"),
        )

    def user_or_thirdparty(self):
        return self.user or self.third_party


class ReturnToServiceQAManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).filter(service_event__is_active=True)


class ReturnToServiceQA(models.Model):

    unit_test_collection = models.ForeignKey(
        UnitTestCollection, help_text=_l('Select a TestList to perform'), on_delete=models.CASCADE
    )
    test_list_instance = models.ForeignKey(
        TestListInstance, null=True, blank=True, on_delete=models.SET_NULL, related_name='rtsqa_for_tli'
    )
    user_assigned_by = models.ForeignKey(User, related_name='+', on_delete=models.PROTECT)
    service_event = models.ForeignKey(ServiceEvent, on_delete=models.CASCADE)

    datetime_assigned = models.DateTimeField()

    objects = ReturnToServiceQAManager()

    class Meta:
        permissions = (
            ('view_returntoserviceqa', 'Can view return to service qa'),
            ('perform_returntoserviceqa', 'Can perform return to service qa'),
        )
        ordering = ['-datetime_assigned']
        default_permissions = ('add', 'change', 'delete',)


class GroupLinker(models.Model):

    group = models.ForeignKey(
        Group,
        help_text=_l('Select the group. Leave blank to allow choosing any user.'),
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    name = models.CharField(
        max_length=64, help_text=_l('Enter this group\'s display name (ie: "Physicist reported to")')
    )

    multiple = models.BooleanField(
        verbose_name=_l("Multiple users"),
        help_text=_l("Allow selecting multiple users when using this group linker"),
        default=False,
    )

    required = models.BooleanField(
        verbose_name=_l("Required"),
        help_text=_l("Force users to add user from this group linker when creating a service event"),
        default=False,
    )

    description = models.TextField(
        null=True, blank=True, help_text=_l('Describe the relationship between this group and service events.')
    )

    help_text = models.CharField(
        max_length=64, null=True, blank=True,
        help_text=_l('Message to display when selecting user in service event form.')
    )

    class Meta:
        unique_together = ('name', 'group')

    def __str__(self):
        return self.name


class GroupLinkerInstance(models.Model):

    group_linker = models.ForeignKey(GroupLinker, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    service_event = models.ForeignKey(ServiceEvent, on_delete=models.CASCADE)

    datetime_linked = models.DateTimeField()

    class Meta:
        default_permissions = ()


class ServiceLogManager(models.Manager):

    def log_new_service_event(self, user, instance):
        self.create(
            user=user,
            service_event=instance,
            log_type=NEW_SERVICE_EVENT,
            # Cheat to always show create logs before rtsqa logs created at same time
            datetime=timezone.now() - timezone.timedelta(seconds=1)
        )

    def log_changed_service_event(self, user, instance, extra_info):
        self.create(
            user=user,
            service_event=instance,
            log_type=MODIFIED_SERVICE_EVENT,
            extra_info=json.dumps(extra_info)
        )

    def log_service_event_status(self, user, instance, extra_info, status_change):

        self.create(
            user=user,
            service_event=instance,
            log_type=STATUS_SERVICE_EVENT,
            extra_info=json.dumps({'status_change': status_change, 'other_changes': extra_info})
        )

    def log_rtsqa_changes(self, user, instance):

        self.create(
            user=user,
            service_event=instance,
            log_type=CHANGED_RTSQA,
            extra_info=json.dumps(instance.create_rts_log_details())
        )

    def log_service_event_delete(self, user, instance, extra_info):

        self.create(
            user=user,
            service_event=instance,
            log_type=DELETED_SERVICE_EVENT,
            extra_info=json.dumps(extra_info)
        )


class ServiceLog(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service_event = models.ForeignKey(ServiceEvent, on_delete=models.CASCADE)

    log_type = models.CharField(choices=LOG_TYPES, max_length=10)

    extra_info = JSONField(blank=True, null=True)
    datetime = models.DateTimeField(default=timezone.now, editable=False)

    objects = ServiceLogManager()

    class Meta:
        ordering = ('-datetime',)
        default_permissions = ()

    def info(self):
        if self.extra_info and isinstance(self.extra_info, str):
            return json.loads(self.extra_info)
        return self.extra_info or {}

    @property
    def is_new(self):
        return self.log_type == NEW_SERVICE_EVENT

    @property
    def is_modified(self):
        return self.log_type == MODIFIED_SERVICE_EVENT

    @property
    def is_status_change(self):
        return self.log_type == STATUS_SERVICE_EVENT

    @property
    def is_rtsqa_change(self):
        return self.log_type == CHANGED_RTSQA

    @property
    def is_rtsqa_performed(self):
        return self.log_type == PERFORMED_RTS

    @property
    def is_rtsqa_approved(self):
        return self.log_type == APPROVED_RTS

    @property
    def is_deleted(self):
        return self.log_type == DELETED_SERVICE_EVENT


@receiver(pre_save, sender=Hours, dispatch_uid="qatrack.service_log.models.ensure_hours_unique")
def ensure_hours_unique(sender, instance, raw, using, update_fields, **kwargs):
    """Some DB's don't consider multiple rows which contain the same columns
    and include null to violate unique contraints so we do our own check"""

    if instance.id is None:
        try:
            Hours.objects.get(
                service_event=instance.service_event,
                third_party=instance.third_party,
                user=instance.user,
            )
        except Hours.DoesNotExist:
            pass
        else:
            # not a unique Hours object
            raise IntegrityError
