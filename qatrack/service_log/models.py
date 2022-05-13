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

from qatrack.qa import models as q_models
from qatrack.qatrack_core.fields import JSONField
from qatrack.qatrack_core.scheduling import SchedulingMixin
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

LOG_TYPES = ((NEW_SERVICE_EVENT, 'New Service Event'), (MODIFIED_SERVICE_EVENT, 'Modified Service Event'),
             (STATUS_SERVICE_EVENT, 'Service Event Status Changed'), (CHANGED_RTSQA, 'Changed Return To Service'),
             (PERFORMED_RTS, 'Performed Return To Service'), (APPROVED_RTS, 'Approved Return To Service'),
             (DELETED_SERVICE_EVENT, 'Deleted Service Event'))


class ServiceArea(models.Model):

    name = models.CharField(
        _l("name"),
        max_length=32,
        unique=True,
        help_text=_l('Enter a short name for this service area'),
    )
    units = models.ManyToManyField(
        Unit,
        through='UnitServiceArea',
        related_name='service_areas',
        verbose_name=_l("units"),
    )

    class Meta:
        ordering = ("name",)
        verbose_name = _l('service area')
        verbose_name_plural = _l('service area')

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name


class UnitServiceArea(models.Model):

    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        verbose_name=_l("unit"),
    )
    service_area = models.ForeignKey(
        ServiceArea,
        on_delete=models.CASCADE,
        verbose_name=_l("service area"),
    )

    notes = models.TextField(
        _l("notes"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _l('unit service area')
        verbose_name_plural = _l('unit service area memberships')
        unique_together = (
            'unit',
            'service_area',
        )
        ordering = ('unit', 'service_area')

    def __str__(self):
        return '%s :: %s' % (self.unit.name, self.service_area.name)


class ServiceType(models.Model):

    name = models.CharField(
        _l("name"),
        max_length=32,
        unique=True,
        help_text=_l('Enter a short name for this service type'),
    )
    is_review_required = models.BooleanField(
        _l("is review required"),
        default=True,
        help_text=_l('Enable this flag to disable the "Review Required" checkbox for new Service Events'),
    )
    is_active = models.BooleanField(
        _l("is active"),
        default=True,
        help_text=_l('Set to false if service type is no longer used'),
    )
    description = models.TextField(
        _l("description"),
        max_length=512,
        help_text=_l('Give a brief description of this service type'),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _l('service type')
        verbose_name_plural = _l('service types')

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name


class ServiceEventStatus(models.Model):

    name = models.CharField(
        _l("name"),
        max_length=32,
        unique=True,
        help_text=_l('Enter a short name for this service status'),
    )
    is_default = models.BooleanField(
        _l("is default"),
        default=False,
        help_text=_l(
            'Is this the default status for all service events? If set to true every other service event '
            'status will be set to false'
        )
    )
    is_review_required = models.BooleanField(
        _l("is review required"),
        default=True,
        help_text=_l('Do service events with this status require review?'),
    )
    rts_qa_must_be_reviewed = models.BooleanField(
        _l("Return To Service (RTS) QC Must be Reviewed"),
        default=True,
        help_text=_l(
            'Service events with Return To Service (RTS) QC that has not been reviewed '
            'can not have this status selected if set to true.'
        ),
    )
    description = models.TextField(
        _l("description"),
        max_length=512,
        help_text=_l('Give a brief description of this service event status'),
        null=True,
        blank=True,
    )
    colour = models.CharField(
        _l("colour"),
        default=settings.DEFAULT_COLOURS[0],
        max_length=22,
        validators=[validate_color],
        help_text=_l("Choose a colour for this service event status"),
    )
    order = models.PositiveIntegerField(
        _l("Order"),
        help_text=_l("Choose what ordering this status will be listed as in drop down controls"),
        default=0,
    )

    objects = NameNaturalKeyManager()

    class Meta:
        verbose_name = _l('service event status')
        verbose_name_plural = _l('service event statuses')
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
        return self.get_queryset().filter(is_active=False)

    def review_required(self):
        return self.get_queryset().filter(
            service_status__in=ServiceEventStatus.objects.filter(is_review_required=True),
            is_review_required=True,
        )

    def review_required_count(self):
        return self.review_required().count()


class ServiceEvent(models.Model):

    unit_service_area = models.ForeignKey(
        UnitServiceArea,
        on_delete=models.PROTECT,
        verbose_name=_l("unit service area"),
    )
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.PROTECT,
        verbose_name=_l("service type"),
    )
    service_event_related = models.ManyToManyField(
        'self',
        symmetrical=True,
        blank=True,
        verbose_name=_l('related service events'),
        help_text=_l('Enter the service event IDs of any related service events.')
    )
    service_status = models.ForeignKey(
        ServiceEventStatus,
        verbose_name=_l('status'),
        on_delete=models.PROTECT,
        help_text=_l("The current status of this service event"),
    )

    user_status_changed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='+',
        on_delete=models.PROTECT,
        verbose_name=_l("status last changed by")
    )
    user_created_by = models.ForeignKey(
        User,
        related_name='+',
        on_delete=models.PROTECT,
        verbose_name=_l("created by"),
    )
    user_modified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='+',
        on_delete=models.PROTECT,
        verbose_name=_l("modified by"),
    )
    test_list_instance_initiated_by = models.ForeignKey(
        q_models.TestListInstance,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='serviceevents_initiated',
        verbose_name=_l("initiating test list instance"),
    )
    service_event_template = models.ForeignKey(
        'ServiceEventTemplate',
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        verbose_name=_l("service event template"),
    )
    service_event_schedule = models.ForeignKey(
        'ServiceEventSchedule',
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        verbose_name=_l("service event schedule"),
    )
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_l('When was this service event due when it was performed'),
    )

    include_for_scheduling = models.BooleanField(
        help_text=_l("Should this instance be considered when calculating due dates?"),
        default=True,
    )

    datetime_status_changed = models.DateTimeField(
        _l("status changed"),
        null=True,
        blank=True,
    )
    datetime_created = models.DateTimeField(_l("created"),)
    datetime_service = models.DateTimeField(
        verbose_name=_l('Date and time'), help_text=_l('Date and time service performed')
    )
    datetime_modified = models.DateTimeField(
        _l("modified"),
        null=True,
        blank=True,
    )

    safety_precautions = models.TextField(
        _l("safety precautions"),
        null=True,
        blank=True,
        help_text=_l('Describe any safety precautions taken'),
    )
    problem_description = models.TextField(
        _l("problem description"),
        help_text=_l('Describe the problem leading to this service event'),
    )
    work_description = models.TextField(
        _l("work description"),
        null=True,
        blank=True,
        help_text=_l('Describe the work done during this service event'),
    )
    duration_service_time = models.DurationField(
        verbose_name=_l('Service time'),
        null=True,
        blank=True,
        help_text=_l('Enter the total time duration of this service event (Hours : minutes)'),
    )
    duration_lost_time = models.DurationField(
        verbose_name=_l('Lost time'),
        null=True,
        blank=True,
        help_text=_l('Enter the total clinical time lost for this service event (Hours : minutes)'),
    )
    is_review_required = models.BooleanField(
        _l("review required"),
        default=True,
        blank=True,
    )
    is_active = models.BooleanField(
        _l("is active"),
        default=True,
        blank=True,
    )

    objects = ServiceEventManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = _l('service event')
        verbose_name_plural = _l('service events')
        get_latest_by = "datetime_service"

        permissions = (
            ('review_serviceevent', _l('Can review service event')),
            ('view_serviceevent', _l('Can review service event')),
        )
        default_permissions = (
            'add',
            'change',
            'delete',
        )

        ordering = ["-datetime_service"]

    def __str__(self):
        return str(self.id)

    @property
    def work_completed(self):
        return self.datetime_service

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

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        verbose_name=_l("vendor"),
    )

    first_name = models.CharField(
        _l("first name"),
        max_length=32,
        help_text=_l('Enter this persons first name'),
    )
    last_name = models.CharField(
        _l("last name"),
        max_length=32,
        help_text=_l('Enter this persons last name'),
    )

    objects = ThirdPartyManager()

    class Meta:
        verbose_name = _l('third party')
        verbose_name_plural = _l('third parties')
        unique_together = ('first_name', 'last_name', 'vendor')

    def __str__(self):
        return self.last_name + ', ' + self.first_name + ' (' + self.vendor.name + ')'

    def get_full_name(self):
        return str(self)


class Hours(models.Model):

    service_event = models.ForeignKey(
        ServiceEvent,
        on_delete=models.CASCADE,
        verbose_name=_l("service event"),
    )
    third_party = models.ForeignKey(
        ThirdParty,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_l("third party"),
    )
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_l("user"),
    )

    time = models.DurationField(
        _l("time"),
        help_text=_l('The time this person spent on this service event'),
    )

    class Meta:
        verbose_name = _l("hours")
        verbose_name_plural = _l("hours")
        unique_together = (
            'service_event',
            'third_party',
            'user',
        )

        default_permissions = ()
        permissions = (("can_have_hours", _l("Can have hours")),)

    def user_or_thirdparty(self):
        return self.user or self.third_party


class ReturnToServiceQAManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).filter(service_event__is_active=True)

    def unreviewed(self):
        return self.get_queryset().filter(
            test_list_instance__isnull=False,
            test_list_instance__all_reviewed=False,
        )

    def unreviewed_count(self):
        return self.unreviewed().count()

    def incomplete(self):
        return self.get_queryset().filter(test_list_instance__isnull=True)

    def incomplete_count(self):
        return self.incomplete().count()


class ReturnToServiceQA(models.Model):

    unit_test_collection = models.ForeignKey(
        q_models.UnitTestCollection, help_text=_l('Select a TestList to perform'), on_delete=models.CASCADE
    )
    test_list_instance = models.ForeignKey(
        q_models.TestListInstance, null=True, blank=True, on_delete=models.SET_NULL, related_name='rtsqa_for_tli'
    )
    user_assigned_by = models.ForeignKey(User, related_name='+', on_delete=models.PROTECT)
    service_event = models.ForeignKey(ServiceEvent, on_delete=models.CASCADE)

    datetime_assigned = models.DateTimeField()

    objects = ReturnToServiceQAManager()

    class Meta:
        verbose_name = _l("return to service qc")
        verbose_name_plural = _l("return to service qc")
        permissions = (
            ('view_returntoserviceqa', _l('Can view Return To Service QC')),
            ('perform_returntoserviceqa', _l('Can perform Return To Service QC')),
        )
        ordering = ['-datetime_assigned']
        default_permissions = (
            'add',
            'change',
            'delete',
        )


class GroupLinker(models.Model):

    group = models.ForeignKey(
        Group,
        help_text=_l('Select the group. Leave blank to allow choosing any user.'),
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name=_l("group"),
    )

    name = models.CharField(
        _l("name"),
        max_length=64,
        help_text=_l('Enter this group\'s display name (ie: "Physicist reported to")'),
    )

    multiple = models.BooleanField(
        verbose_name=_l("multiple users"),
        help_text=_l("Allow selecting multiple users when using this group linker"),
        default=False,
    )

    required = models.BooleanField(
        verbose_name=_l("required"),
        help_text=_l("Force users to add user from this group linker when creating a service event"),
        default=False,
    )

    description = models.TextField(
        _l("description"),
        null=True,
        blank=True,
        help_text=_l('Describe the relationship between this group and service events.'),
    )

    help_text = models.CharField(
        _l("help text"),
        max_length=64,
        null=True,
        blank=True,
        help_text=_l('Message to display when selecting user in service event form.')
    )

    class Meta:
        unique_together = ('name', 'group')
        verbose_name = _l("group linker")
        verbose_name_plural = _l("group linkers")

    def __str__(self):
        return self.name


class GroupLinkerInstance(models.Model):

    group_linker = models.ForeignKey(
        GroupLinker,
        on_delete=models.PROTECT,
        verbose_name=_l("group linker"),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_l("user"),
    )
    service_event = models.ForeignKey(
        ServiceEvent,
        on_delete=models.CASCADE,
        verbose_name=_l("service event"),
    )

    datetime_linked = models.DateTimeField(_l("linked"),)

    class Meta:
        default_permissions = ()
        verbose_name = _l("group linker instance")
        verbose_name_plural = _l("group linker instances")


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
            user=user, service_event=instance, log_type=MODIFIED_SERVICE_EVENT, extra_info=json.dumps(extra_info)
        )

    def log_service_event_status(self, user, instance, extra_info, status_change):

        self.create(
            user=user,
            service_event=instance,
            log_type=STATUS_SERVICE_EVENT,
            extra_info=json.dumps({
                'status_change': status_change,
                'other_changes': extra_info
            })
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
            user=user, service_event=instance, log_type=DELETED_SERVICE_EVENT, extra_info=json.dumps(extra_info)
        )


class ServiceLog(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_l("user"),
    )
    service_event = models.ForeignKey(
        ServiceEvent,
        on_delete=models.CASCADE,
        verbose_name=_l("service event"),
    )

    log_type = models.CharField(
        _l("log type"),
        choices=LOG_TYPES,
        max_length=10,
    )

    extra_info = JSONField(
        _l("extra info"),
        blank=True,
        null=True,
    )
    datetime = models.DateTimeField(
        _l("date and time"),
        default=timezone.now,
        editable=False,
    )

    objects = ServiceLogManager()

    class Meta:
        ordering = ('-datetime',)
        default_permissions = ()
        verbose_name = _l("service event log")
        verbose_name_plural = _l("service event logs")

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


class ServiceEventTemplate(models.Model):

    service_type = models.ForeignKey(
        ServiceType,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_l("service type"),
        help_text=_l(
            'Select the Service Type this Service Event Template applies to. '
            'Leave blank to create a generic template.'
        ),
    )
    service_area = models.ForeignKey(
        ServiceArea,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_l("service area"),
        help_text=_l(
            'Select the Service Area this Service Event Template applies to. '
            'Leave blank to create a generic template.'
        ),
    )
    problem_description = models.TextField(
        _l("problem description"),
        help_text=_l('Describe the problem leading to this service event'),
        null=True,
        blank=True,
    )
    work_description = models.TextField(
        _l("work description"),
        null=True,
        blank=True,
        help_text=_l('Describe the work done during this service event'),
    )
    is_review_required = models.BooleanField(
        _l("is review required"),
        default=True,
        blank=True,
        help_text=_l('Check this option to make "Review" mandatory for Service Events created with this template'),
    )
    return_to_service_test_lists = models.ManyToManyField(
        q_models.TestList,
        related_name='service_event_templates',
        verbose_name=_l("return to service test lists"),
        help_text=_l("Select the Return to Service QC that must be performed for this Service Event Type"),
        blank=True,
    )

    return_to_service_cycles = models.ManyToManyField(
        q_models.TestListCycle,
        related_name='service_event_templates',
        verbose_name=_l("return to service test list cycles"),
        help_text=_l("Select the Return to Service QC that must be performed for this Service Event Type"),
        blank=True,
    )

    # Template fields
    name = models.CharField(
        _l("name"),
        max_length=255,
        help_text=_l("Give this template a concise name"),
    )

    created = models.DateTimeField(
        _l("created"),
        auto_now_add=True,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        editable=False,
        verbose_name=_l("created by"),
        related_name='service_event_templates_created',
    )
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        editable=False,
        verbose_name=_l("modified by"),
        related_name='service_event_templates_modified',
    )

    class Meta:
        verbose_name = _l("service event template")
        verbose_name_plural = _l("service event templates")
        ordering = ("name",)

    def __str__(self):
        return self.name


@receiver(pre_save, sender=Hours, dispatch_uid="qatrack.service_log.models.ensure_hours_unique")
def ensure_hours_unique(sender, instance, raw, using, update_fields, **kwargs):
    """Some DB's don't consider multiple rows which contain the same columns
    and include null to violate unique constraints so we do our own check"""

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


class ServiceEventSchedule(SchedulingMixin, models.Model):

    unit_service_area = models.ForeignKey(
        UnitServiceArea,
        on_delete=models.CASCADE,
        verbose_name=_l("unit service area"),
    )

    frequency = models.ForeignKey(
        q_models.Frequency,
        on_delete=models.CASCADE,
        verbose_name=_l("frequency"),
        null=True,
        blank=True,
        related_name='serviceeventschedules',
    )

    due_date = models.DateTimeField(
        _l("due date"),
        help_text=_l("Next time this service event schedule is due"),
        null=True,
        blank=True,
    )
    auto_schedule = models.BooleanField(
        _l("auto schedule"),
        help_text=_l("If this is checked, due_date will be auto set based on the assigned frequency"),
        default=True,
    )

    assigned_to = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        help_text=_l("QC group that this test list should nominally be performed by"),
        null=True,
        related_name="serviceeventschedule_assigned_to",
    )
    visible_to = models.ManyToManyField(
        Group,
        help_text=_l("Select groups who will be able to see this test collection on this unit"),
        related_name="serviceeventschedule_visible_to",
    )

    active = models.BooleanField(
        _l("active"),
        default=True,
        help_text=_l("Uncheck to disable scheduling of this service event template"),
    )

    service_event_template = models.ForeignKey(
        ServiceEventTemplate,
        on_delete=models.CASCADE,
        verbose_name=_l("service event template"),
    )

    last_instance = models.ForeignKey(
        ServiceEvent,
        null=True,
        editable=False,
        on_delete=models.SET_NULL,
        verbose_name=_l("last instance"),
    )

    class Meta:
        unique_together = ('unit_service_area', 'service_event_template', 'frequency')
        verbose_name = _l("service event schedule")
        verbose_name_plural = _l("Assign Service Event Templates to Units")

    def get_last_instance(self):
        """ return last service_event """

        try:
            return ServiceEvent.objects.filter(
                service_event_template=self.service_event_template, is_active=True
            ).latest('datetime_service')
        except ServiceEvent.DoesNotExist:
            pass

    def last_instance_for_scheduling(self):
        """ return last test_list_instance with all valid tests """

        try:
            return self.serviceevent_set.filter(
                include_for_scheduling=True,
            ).exclude(is_active=False).latest("datetime_service")
        except ServiceEvent.DoesNotExist:
            pass

    def get_absolute_url(self):
        return "%s?se_schedule=%s" % (reverse("sl_new"), self.pk)

    def __str__(self):
        return 'Service Schedule for {}'.format(self.service_event_template)
