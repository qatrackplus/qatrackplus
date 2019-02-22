from django.contrib.auth.models import Group, User
import rest_framework_filters as filters

from qatrack.api.auth.filters import GroupFilter, UserFilter
from qatrack.api.qa.filters import (
    TestListInstanceFilter,
    UnitTestCollectionFilter,
)
from qatrack.api.units.filters import UnitFilter, VendorFilter
from qatrack.qa.models import TestListInstance, UnitTestCollection
from qatrack.service_log import models
from qatrack.units.models import Unit, Vendor


class ServiceAreaFilter(filters.FilterSet):

    units = filters.RelatedFilter(UnitFilter, field_name='units', queryset=Unit.objects.all())

    class Meta:
        model = models.ServiceArea
        fields = {
            "name": "__all__",
        }


class UnitServiceAreaFilter(filters.FilterSet):

    unit = filters.RelatedFilter(UnitFilter, field_name='unit', queryset=Unit.objects.all())
    service_area = filters.RelatedFilter(
        ServiceAreaFilter,
        field_name='service_area',
        queryset=models.ServiceArea.objects.all(),
    )

    class Meta:
        model = models.UnitServiceArea
        fields = {
            "notes": "__all__",
        }


class ServiceTypeFilter(filters.FilterSet):

    class Meta:
        model = models.ServiceType
        fields = {
            "name": "__all__",
            "is_review_required": "__all__",
            "is_active": "__all__",
            "description": "__all__",
        }


class ServiceEventStatusFilter(filters.FilterSet):

    class Meta:
        model = models.ServiceEventStatus
        fields = {
            "name": "__all__",
            "is_review_required": "__all__",
            "is_default": "__all__",
            "rts_qa_must_be_reviewed": "__all__",
            "description": "__all__",
            "colour": "__all__",
        }


class ServiceEventFilter(filters.FilterSet):

    unit_service_area = filters.RelatedFilter(
        UnitServiceAreaFilter,
        field_name='unit_service_area',
        queryset=models.UnitServiceArea.objects.all(),
    )
    service_type = filters.RelatedFilter(
        ServiceTypeFilter,
        field_name='service_type',
        queryset=models.ServiceType.objects.all(),
    )
    service_event_related = filters.RelatedFilter(
        'ServiceEventFilter', field_name='service_event_related', queryset=models.ServiceEvent.objects.all()
    )
    service_status = filters.RelatedFilter(
        ServiceEventStatusFilter,
        field_name='service_status',
        queryset=models.ServiceEventStatus.objects.all(),
    )
    user_status_changed_by = filters.RelatedFilter(
        UserFilter,
        field_name='user_status_changed_by',
        queryset=User.objects.all(),
    )
    user_created_by = filters.RelatedFilter(UserFilter, field_name='user_created_by', queryset=User.objects.all())
    user_modified_by = filters.RelatedFilter(UserFilter, field_name='user_modified_by', queryset=User.objects.all())
    test_list_instance_initiated_by = filters.RelatedFilter(
        TestListInstanceFilter,
        field_name='test_list_instance_initiated_by',
        queryset=TestListInstance.objects.all(),
    )

    class Meta:
        model = models.ServiceEvent
        fields = {
            'datetime_status_changed': '__all__',
            'datetime_created': '__all__',
            'datetime_service': '__all__',
            'datetime_modified': '__all__',
            'safety_precautions': '__all__',
            'problem_description': '__all__',
            'duration_service_time': '__all__',
            'duration_lost_time': '__all__',
            'is_review_required': '__all__',
        }


class ThirdPartyFilter(filters.FilterSet):

    vendor = filters.RelatedFilter(VendorFilter, field_name='vendor', queryset=Vendor.objects.all())

    class Meta:
        model = models.ThirdParty
        fields = {
            'first_name': "__all__",
            'last_name': "__all__",
        }


class HoursFilter(filters.FilterSet):

    service_event = filters.RelatedFilter(
        ServiceEventFilter, field_name='service_event', queryset=models.ServiceEvent.objects.all()
    )
    third_party = filters.RelatedFilter(ThirdPartyFilter, field_name='third_party', queryset=models.ThirdParty.objects.all())

    class Meta:
        model = models.Hours
        fields = {
            'time': '__all__',
        }


class ReturnToServiceQAFilter(filters.FilterSet):

    unit_test_collection = filters.RelatedFilter(
        UnitTestCollectionFilter, field_name='unit_test_collection', queryset=UnitTestCollection.objects.all()
    )
    test_list_instance = filters.RelatedFilter(
        TestListInstanceFilter, field_name='test_list_instance', queryset=TestListInstance.objects.all()
    )
    user_assigned_by = filters.RelatedFilter(UserFilter, field_name='user_assigned_by', queryset=User.objects.all())
    service_event = filters.RelatedFilter(
        ServiceEventFilter, field_name='service_event', queryset=models.ServiceEvent.objects.all()
    )

    class Meta:
        model = models.ReturnToServiceQA
        fields = {
            'datetime_assigned': '__all__',
        }


class GroupLinkerFilter(filters.FilterSet):

    group = filters.RelatedFilter(GroupFilter, field_name='group', queryset=Group.objects.all())

    class Meta:
        model = models.GroupLinker
        fields = {
            'name': "__all__",
            'description': "__all__",
            'help_text': "__all__",
        }


class GroupLinkerInstanceFilter(filters.FilterSet):

    group_linker = filters.RelatedFilter(
        GroupLinkerFilter, field_name='group_linker', queryset=models.GroupLinker.objects.all()
    )
    user = filters.RelatedFilter(UserFilter, field_name='user', queryset=User.objects.all())
    service_event = filters.RelatedFilter(
        ServiceEventFilter, field_name='service_event', queryset=models.ServiceEvent.objects.all()
    )

    class Meta:
        model = models.GroupLinkerInstance
        fields = {
            'datetime_linked': '__all__',
        }
