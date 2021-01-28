import django.forms.widgets as widgets
import rest_framework_filters as filters

from qatrack.api.auth.filters import Group, GroupFilter, User, UserFilter
from qatrack.api.filters import MaxDateFilter, MinDateFilter
from qatrack.api.units.filters import UnitFilter
from qatrack.qa import models
from qatrack.units.models import Unit


class FrequencyFilter(filters.FilterSet):

    class Meta:
        model = models.Frequency
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
            "slug": ['exact', 'icontains', 'contains', 'in'],
            "nominal_interval": ['exact', 'in', 'gte', 'lte'],
            "window_start": ['exact', 'in', 'gte', 'lte'],
            "window_end": ['exact', 'in', 'gte', 'lte'],
        }


class TestInstanceStatusFilter(filters.FilterSet):

    class Meta:
        model = models.TestInstanceStatus
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
            "slug": ['exact', 'icontains', 'contains', 'in'],
            "description": ['icontains'],
            "is_default": ['exact'],
            "requires_review": ['exact'],
            "export_by_default": ['exact'],
            "valid": ['exact'],
        }


class AutoReviewRuleFilter(filters.FilterSet):

    status = filters.RelatedFilter(
        TestInstanceStatusFilter,
        field_name="status",
        queryset=models.TestInstanceStatus.objects.all(),
    )

    pass_fail = filters.Filter(
        field_name="pass_fail",
        widget=widgets.Select(choices=[('', 'Any')] + list(models.PASS_FAIL_CHOICES)),
    )

    class Meta:
        model = models.AutoReviewRule
        fields = ['status', 'pass_fail']


class AutoReviewRuleSetFilter(filters.FilterSet):

    status = filters.RelatedFilter(
        TestInstanceStatusFilter,
        field_name="status",
        queryset=models.TestInstanceStatus.objects.all(),
    )

    pass_fail = filters.Filter(
        field_name="pass_fail",
        widget=widgets.Select(choices=[('', 'Any')] + list(models.PASS_FAIL_CHOICES)),
    )

    class Meta:
        model = models.AutoReviewRuleSet
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
            "is_default": ['exact'],
        }


class ReferenceFilter(filters.FilterSet):

    created_by = filters.RelatedFilter(UserFilter, field_name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, field_name="modified_by", queryset=User.objects.all())

    type = filters.Filter(
        field_name="type",
        widget=widgets.Select(choices=[('', 'Any')] + list(models.REF_TYPE_CHOICES)),
    )

    created_min = MinDateFilter(field_name="created")
    created_max = MaxDateFilter(field_name="created")
    modified_min = MinDateFilter(field_name="modified")
    modified_max = MaxDateFilter(field_name="modified")

    class Meta:
        model = models.Reference
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
            "value": ['exact', 'in', 'gte', 'lte'],
            "created": ['exact'],
            "modified": ['exact'],
        }


class ToleranceFilter(filters.FilterSet):

    type = filters.Filter(
        field_name="type",
        widget=widgets.Select(choices=[('', 'Any')] + list(models.TOL_TYPE_CHOICES)),
    )

    class Meta:
        model = models.Tolerance
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
            "act_low": ['exact', 'in', 'gte', 'lte'],
            "tol_low": ['exact', 'in', 'gte', 'lte'],
            "tol_high": ['exact', 'in', 'gte', 'lte'],
            "act_high": ['exact', 'in', 'gte', 'lte'],
            "mc_pass_choices": ['icontains', 'in'],
            "mc_tol_choices": ['icontains', 'in'],
            "bool_warning_only": ['exact'],
        }


class CategoryFilter(filters.FilterSet):

    class Meta:
        model = models.Category
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
            "slug": ['exact', 'icontains', 'contains', 'in'],
            "description": ['icontains'],
        }


class TestFilter(filters.FilterSet):

    created_by = filters.RelatedFilter(UserFilter, field_name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, field_name="modified_by", queryset=User.objects.all())
    category = filters.RelatedFilter(CategoryFilter, field_name="category", queryset=models.Category.objects.all())

    type = filters.Filter(
        field_name="type",
        widget=widgets.Select(choices=[('', 'Any')] + list(models.TEST_TYPE_CHOICES)),
    )

    created_min = MinDateFilter(field_name="created")
    created_max = MaxDateFilter(field_name="created")
    modified_min = MinDateFilter(field_name="modified")
    modified_max = MaxDateFilter(field_name="modified")

    class Meta:
        model = models.Test
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
            "slug": ['exact', 'icontains', 'contains', 'in'],
            "description": ['icontains'],
            "procedure": ['icontains'],
            "chart_visibility": ['exact'],
            "hidden": ['exact'],
            "skip_without_comment": ['exact'],
            "display_image": ['exact'],
            "choices": ['icontains', 'in'],
            "constant_value": ['exact', 'in', 'gte', 'lte'],
            "created": ['exact'],
            "modified": ['exact'],
        }


class TestListFilter(filters.FilterSet):

    created_by = filters.RelatedFilter(UserFilter, field_name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, field_name="modified_by", queryset=User.objects.all())
    tests = filters.RelatedFilter(TestFilter, field_name="tests", queryset=models.Test.objects.all())
    utcs = filters.RelatedFilter(
        "qatrack.api.qa.filters.UnitTestCollectionFilter",
        field_name="utcs",
        queryset=models.UnitTestCollection.objects.all(),
    )

    created_min = MinDateFilter(field_name="created")
    created_max = MaxDateFilter(field_name="created")
    modified_min = MinDateFilter(field_name="modified")
    modified_max = MaxDateFilter(field_name="modified")

    class Meta:
        model = models.TestList
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
            "slug": ['exact', 'icontains', 'contains', 'in'],
            "description": ['icontains'],
            "warning_message": ['icontains'],
            "created": ['exact'],
            "modified": ['exact'],
        }


class TestListCycleFilter(filters.FilterSet):

    created_by = filters.RelatedFilter(UserFilter, field_name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, field_name="modified_by", queryset=User.objects.all())
    test_lists = filters.RelatedFilter(TestListFilter, field_name="test_lists", queryset=models.TestList.objects.all())
    utcs = filters.RelatedFilter(
        "qatrack.api.qa.filters.UnitTestCollectionFilter",
        field_name="utcs",
        queryset=models.UnitTestCollection.objects.all(),
    )

    created_min = MinDateFilter(field_name="created")
    created_max = MaxDateFilter(field_name="created")
    modified_min = MinDateFilter(field_name="modified")
    modified_max = MaxDateFilter(field_name="modified")

    class Meta:
        model = models.TestListCycle
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
            "slug": ['exact', 'icontains', 'contains', 'in'],
            "description": ['icontains'],
            "drop_down_label": ['icontains', 'in'],
            "day_option_text": ['icontains', 'in'],
            "created": ['exact'],
            "modified": ['exact'],
        }


class UnitTestCollectionFilter(filters.FilterSet):

    unit = filters.RelatedFilter(UnitFilter, field_name="unit", queryset=Unit.objects.all())
    frequency = filters.RelatedFilter(FrequencyFilter, field_name="frequency", queryset=models.Frequency.objects.all())
    assigned_to = filters.RelatedFilter(GroupFilter, field_name="assigned_to", queryset=Group.objects.all())
    visible_to = filters.RelatedFilter(GroupFilter, field_name="visible_to", queryset=Group.objects.all())
    last_instance = filters.RelatedFilter(
        "TestListInstanceFilter", field_name="last_instance", queryset=models.TestListInstance.objects.all()
    )

    test_list = filters.RelatedFilter(TestListFilter, field_name="test_list", queryset=models.TestList.objects.all())
    test_list_cycle = filters.RelatedFilter(
        TestListCycleFilter, field_name="test_list_cycle", queryset=models.TestListCycle.objects.all()
    )

    due_date_min = MinDateFilter(field_name="due_date")
    due_date_max = MaxDateFilter(field_name="due_date")

    class Meta:
        model = models.UnitTestCollection
        fields = {
            "auto_schedule": ['exact'],
            "active": ['exact'],
            "name": ['exact', 'icontains', 'contains', 'in'],
            "content_type": ['exact'],
        }


class TestListInstanceFilter(filters.FilterSet):

    unit_test_collection = filters.RelatedFilter(
        UnitTestCollectionFilter,
        field_name="unit_test_collection",
        queryset=models.UnitTestCollection.objects.all(),
    )
    test_list = filters.RelatedFilter(TestListFilter, field_name="test_list", queryset=models.TestList.objects.all())

    reviewed_by = filters.RelatedFilter(UserFilter, field_name="reviewed_by", queryset=User.objects.all())
    created_by = filters.RelatedFilter(UserFilter, field_name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, field_name="modified_by", queryset=User.objects.all())

    due_date_min = MinDateFilter(field_name="due_date")
    due_date_max = MaxDateFilter(field_name="due_date")

    reviewed_min = MinDateFilter(field_name="reviewed")
    reviewed_max = MaxDateFilter(field_name="reviewed")

    work_started_min = MinDateFilter(field_name="work_started")
    work_started_max = MaxDateFilter(field_name="work_started")

    work_completed_min = MinDateFilter(field_name="work_completed")
    work_completed_max = MaxDateFilter(field_name="work_completed")

    created_min = MinDateFilter(field_name="created")
    created_max = MaxDateFilter(field_name="created")
    modified_min = MinDateFilter(field_name="modified")
    modified_max = MaxDateFilter(field_name="modified")

    class Meta:
        model = models.TestListInstance
        fields = {
            "due_date": ['exact', "in"],
            "in_progress": ['exact'],
            "include_for_scheduling": ['exact'],
            "reviewed": ['exact'],
            "all_reviewed": ['exact'],
            "day": ['exact', 'in'],
            "work_started": ['exact', "in"],
            "work_completed": ['exact', "in"],
            "created": ['exact', "in"],
            "modified": ['exact', "in"],
        }


class UnitTestInfoFilter(filters.FilterSet):

    unit = filters.RelatedFilter(UnitFilter, field_name="unit", queryset=Unit.objects.all())
    test = filters.RelatedFilter(TestFilter, field_name="test", queryset=models.Test.objects.all())
    reference = filters.RelatedFilter(ReferenceFilter, field_name="reference", queryset=models.Reference.objects.all())
    tolerance = filters.RelatedFilter(ToleranceFilter, field_name="tolerance", queryset=models.Tolerance.objects.all())

    class Meta:
        model = models.UnitTestInfo
        fields = {
            "active": ['exact'],
        }


class TestListMembershipFilter(filters.FilterSet):

    test_list = filters.RelatedFilter(TestListFilter, field_name="test_list", queryset=models.TestList.objects.all())
    test = filters.RelatedFilter(TestFilter, field_name="test", queryset=models.Test.objects.all())

    class Meta:
        model = models.TestListMembership
        fields = {
            "order": ['exact', 'in'],
        }


class SublistFilter(filters.FilterSet):

    parent = filters.RelatedFilter(TestListFilter, field_name="parent", queryset=models.TestList.objects.all())
    child = filters.RelatedFilter(TestListFilter, field_name="child", queryset=models.TestList.objects.all())

    class Meta:
        model = models.Sublist
        fields = {
            "order": ['exact', 'in'],
            "outline": ['exact'],
        }


class TestInstanceFilter(filters.FilterSet):

    status = filters.RelatedFilter(
        TestInstanceStatusFilter,
        field_name="status",
        queryset=models.TestInstanceStatus.objects.all(),
    )
    reviewed_by = filters.RelatedFilter(UserFilter, field_name="reviewed_by", queryset=User.objects.all())
    reference = filters.RelatedFilter(ReferenceFilter, field_name="reference", queryset=models.Reference.objects.all())
    tolerance = filters.RelatedFilter(ToleranceFilter, field_name="tolerance", queryset=models.Tolerance.objects.all())
    unit_test_info = filters.RelatedFilter(
        UnitTestInfoFilter,
        field_name="unit_test_info",
        queryset=models.UnitTestInfo.objects.all(),
    )
    test_list_instance = filters.RelatedFilter(
        TestListInstanceFilter,
        field_name="test_list_instance",
        queryset=models.TestListInstance.objects.all(),
    )

    pass_fail = filters.Filter(
        field_name="pass_fail",
        widget=widgets.Select(choices=[('', 'Any')] + list(models.PASS_FAIL_CHOICES)),
    )

    created_by = filters.RelatedFilter(UserFilter, field_name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, field_name="modified_by", queryset=User.objects.all())

    work_started_min = MinDateFilter(field_name="work_started")
    work_started_max = MaxDateFilter(field_name="work_started")

    work_completed_min = MinDateFilter(field_name="work_completed")
    work_completed_max = MaxDateFilter(field_name="work_completed")

    review_date_min = MinDateFilter(field_name="review_date")
    review_date_max = MaxDateFilter(field_name="review_date")

    created_min = MinDateFilter(field_name="created")
    created_max = MaxDateFilter(field_name="created")
    modified_min = MinDateFilter(field_name="modified")
    modified_max = MaxDateFilter(field_name="modified")

    class Meta:
        model = models.TestInstance
        fields = {
            "review_date": ['exact'],
            "value": ['exact', 'in', 'gte', 'lte'],
            "string_value": ['exact', 'icontains', 'contains', 'in'],
            "skipped": ['exact'],
            "comment": ['exact', 'icontains', 'contains', 'in'],
            "work_started": ['exact'],
            "work_completed": ['exact'],
            "created": ['exact'],
            "modified": ['exact'],
        }


class TestListCycleMembershipFilter(filters.FilterSet):

    test_list = filters.RelatedFilter(TestListFilter, field_name="test_list", queryset=models.TestList.objects.all())
    cycle = filters.RelatedFilter(TestListCycleFilter, field_name="cycle", queryset=models.TestListCycle.objects.all())

    class Meta:
        model = models.TestListCycleMembership
        fields = {
            "order": ['exact', 'in'],
        }
