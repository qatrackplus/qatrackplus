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
            "name": ['icontains', 'in'],
            "slug": ['icontains', 'in'],
            "nominal_interval": ['exact', 'in', 'gte', 'lte'],
            "due_interval": ['exact', 'in', 'gte', 'lte'],
            "overdue_interval": ['exact', 'in', 'gte', 'lte'],
        }


class TestInstanceStatusFilter(filters.FilterSet):

    class Meta:
        model = models.TestInstanceStatus
        fields = {
            "name": ['icontains', 'in'],
            "slug": ['icontains', 'in'],
            "description": ['icontains'],
            "is_default": ['exact'],
            "requires_review": ['exact'],
            "export_by_default": ['exact'],
            "valid": ['exact'],
        }


class AutoReviewRuleFilter(filters.FilterSet):

    status = filters.RelatedFilter(
        TestInstanceStatusFilter,
        name="status",
        queryset=models.TestInstanceStatus.objects.all(),
    )

    pass_fail = filters.Filter(
        name="pass_fail",
        widget=widgets.Select(choices=[('', 'Any')] + list(models.PASS_FAIL_CHOICES)),
    )

    class Meta:
        model = models.AutoReviewRule
        fields = ['status', 'pass_fail']


class ReferenceFilter(filters.FilterSet):

    created_by = filters.RelatedFilter(UserFilter, name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, name="modified_by", queryset=User.objects.all())

    type = filters.Filter(
        name="type",
        widget=widgets.Select(choices=[('', 'Any')] + list(models.REF_TYPE_CHOICES)),
    )

    created_min = MinDateFilter(name="created")
    created_max = MaxDateFilter(name="created")
    modified_min = MinDateFilter(name="modified")
    modified_max = MaxDateFilter(name="modified")

    class Meta:
        model = models.Reference
        fields = {
            "name": ['icontains', 'in'],
            "value": ['exact', 'in', 'gte', 'lte'],
            "created": ['exact'],
            "modified": ['exact'],
        }


class ToleranceFilter(filters.FilterSet):

    type = filters.Filter(
        name="type",
        widget=widgets.Select(choices=[('', 'Any')] + list(models.TOL_TYPE_CHOICES)),
    )

    class Meta:
        model = models.Tolerance
        fields = {
            "name": ['icontains', 'in'],
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
            "name": ['icontains', 'in'],
            "slug": ['icontains', 'in'],
            "description": ['icontains'],
        }


class TestFilter(filters.FilterSet):

    created_by = filters.RelatedFilter(UserFilter, name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, name="modified_by", queryset=User.objects.all())
    category = filters.RelatedFilter(CategoryFilter, name="category", queryset=models.Category.objects.all())

    type = filters.Filter(
        name="type",
        widget=widgets.Select(choices=[('', 'Any')] + list(models.TEST_TYPE_CHOICES)),
    )

    created_min = MinDateFilter(name="created")
    created_max = MaxDateFilter(name="created")
    modified_min = MinDateFilter(name="modified")
    modified_max = MaxDateFilter(name="modified")

    class Meta:
        model = models.Test
        fields = {
            "name": ['icontains', 'in'],
            "slug": ['icontains', 'in'],
            "description": ['icontains'],
            "procedure": ['icontains'],
            "chart_visibility": ['exact'],
            "auto_review": ['exact'],
            "hidden": ['exact'],
            "skip_without_comment": ['exact'],
            "display_image": ['exact'],
            "choices": ['icontains', 'in'],
            "constant_value": ['exact', 'in', 'gte', 'lte'],
            "created": ['exact'],
            "modified": ['exact'],
        }


class TestListFilter(filters.FilterSet):

    created_by = filters.RelatedFilter(UserFilter, name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, name="modified_by", queryset=User.objects.all())
    tests = filters.RelatedFilter(TestFilter, name="tests", queryset=models.Test.objects.all())
    utcs = filters.RelatedFilter(
        "qatrack.api.qa.filters.UnitTestCollectionFilter",
        name="utcs",
        queryset=models.UnitTestCollection.objects.all(),
    )

    created_min = MinDateFilter(name="created")
    created_max = MaxDateFilter(name="created")
    modified_min = MinDateFilter(name="modified")
    modified_max = MaxDateFilter(name="modified")

    class Meta:
        model = models.TestList
        fields = {
            "name": ['icontains', 'in'],
            "slug": ['icontains', 'in'],
            "description": ['icontains'],
            "warning_message": ['icontains'],
            "created": ['exact'],
            "modified": ['exact'],
        }


class TestListCycleFilter(filters.FilterSet):

    created_by = filters.RelatedFilter(UserFilter, name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, name="modified_by", queryset=User.objects.all())
    test_lists = filters.RelatedFilter(TestListFilter, name="test_lists", queryset=models.TestList.objects.all())
    utcs = filters.RelatedFilter(
        "qatrack.api.qa.filters.UnitTestCollectionFilter",
        name="utcs",
        queryset=models.UnitTestCollection.objects.all(),
    )

    created_min = MinDateFilter(name="created")
    created_max = MaxDateFilter(name="created")
    modified_min = MinDateFilter(name="modified")
    modified_max = MaxDateFilter(name="modified")

    class Meta:
        model = models.TestListCycle
        fields = {
            "name": ['icontains', 'in'],
            "slug": ['icontains', 'in'],
            "description": ['icontains'],
            "drop_down_label": ['icontains', 'in'],
            "day_option_text": ['icontains', 'in'],
            "created": ['exact'],
            "modified": ['exact'],
        }


class UnitTestCollectionFilter(filters.FilterSet):

    unit = filters.RelatedFilter(UnitFilter, name="unit", queryset=Unit.objects.all())
    frequency = filters.RelatedFilter(FrequencyFilter, name="frequency", queryset=models.Frequency.objects.all())
    assigned_to = filters.RelatedFilter(GroupFilter, name="assigned_to", queryset=Group.objects.all())
    visible_to = filters.RelatedFilter(GroupFilter, name="visible_to", queryset=Group.objects.all())
    last_instance = filters.RelatedFilter(
        "TestListInstanceFilter", name="last_instance", queryset=models.TestListInstance.objects.all()
    )

    test_list = filters.RelatedFilter(TestListFilter, field_name="test_list", queryset=models.TestList.objects.all(),)
    test_list_cycle = filters.RelatedFilter(
        TestListCycleFilter,
        field_name="test_list_cycle",
        queryset=models.TestListCycle.objects.all(),
    )

    due_date_min = MinDateFilter(name="due_date")
    due_date_max = MaxDateFilter(name="due_date")

    class Meta:
        model = models.UnitTestCollection
        fields = {
            "auto_schedule": ['exact'],
            "active": ['exact'],
            "name": ['icontains', 'in'],
            "content_type": ['exact'],
        }


class TestListInstanceFilter(filters.FilterSet):

    unit_test_collection = filters.RelatedFilter(
        UnitTestCollectionFilter,
        name="unit_test_collection",
        queryset=models.UnitTestCollection.objects.all(),
    )
    test_list = filters.RelatedFilter(TestListFilter, name="test_list", queryset=models.TestList.objects.all())

    reviewed_by = filters.RelatedFilter(UserFilter, name="reviewed_by", queryset=User.objects.all())
    created_by = filters.RelatedFilter(UserFilter, name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, name="modified_by", queryset=User.objects.all())

    due_date_min = MinDateFilter(name="due_date")
    due_date_max = MaxDateFilter(name="due_date")

    reviewed_min = MinDateFilter(name="reviewed")
    reviewed_max = MaxDateFilter(name="reviewed")

    work_started_min = MinDateFilter(name="work_started")
    work_started_max = MaxDateFilter(name="work_started")

    work_completed_min = MinDateFilter(name="work_completed")
    work_completed_max = MaxDateFilter(name="work_completed")

    created_min = MinDateFilter(name="created")
    created_max = MaxDateFilter(name="created")
    modified_min = MinDateFilter(name="modified")
    modified_max = MaxDateFilter(name="modified")

    class Meta:
        model = models.TestListInstance
        fields = {
            "due_date": ['exact'],
            "in_progress": ['exact'],
            "reviewed": ['exact'],
            "all_reviewed": ['exact'],
            "day": ['exact', 'in'],
            "work_started": ['exact'],
            "work_completed": ['exact'],
            "created": ['exact'],
            "modified": ['exact'],
        }


class UnitTestInfoFilter(filters.FilterSet):

    unit = filters.RelatedFilter(UnitFilter, name="unit", queryset=Unit.objects.all())
    test = filters.RelatedFilter(TestFilter, name="test", queryset=models.Test.objects.all())
    reference = filters.RelatedFilter(ReferenceFilter, name="reference", queryset=models.Reference.objects.all())
    tolerance = filters.RelatedFilter(ToleranceFilter, name="tolerance", queryset=models.Tolerance.objects.all())

    class Meta:
        model = models.UnitTestInfo
        fields = {
            "active": ['exact'],
        }


class TestListMembershipFilter(filters.FilterSet):

    test_list = filters.RelatedFilter(TestListFilter, name="test_list", queryset=models.TestList.objects.all())
    test = filters.RelatedFilter(TestFilter, name="test", queryset=models.Test.objects.all())

    class Meta:
        model = models.TestListMembership
        fields = {
            "order": ['exact', 'in'],
        }


class SublistFilter(filters.FilterSet):

    parent = filters.RelatedFilter(TestListFilter, name="parent", queryset=models.TestList.objects.all())
    child = filters.RelatedFilter(TestListFilter, name="child", queryset=models.TestList.objects.all())

    class Meta:
        model = models.Sublist
        fields = {
            "order": ['exact', 'in'],
            "outline": ['exact'],
        }


class TestInstanceFilter(filters.FilterSet):

    status = filters.RelatedFilter(
        TestInstanceStatusFilter,
        name="status",
        queryset=models.TestInstanceStatus.objects.all(),
    )
    reviewed_by = filters.RelatedFilter(UserFilter, name="reviewed_by", queryset=User.objects.all())
    reference = filters.RelatedFilter(ReferenceFilter, name="reference", queryset=models.Reference.objects.all())
    tolerance = filters.RelatedFilter(ToleranceFilter, name="tolerance", queryset=models.Tolerance.objects.all())
    unit_test_info = filters.RelatedFilter(
        UnitTestInfoFilter,
        name="unit_test_info",
        queryset=models.UnitTestInfo.objects.all(),
    )
    test_list_instance = filters.RelatedFilter(
        TestListInstanceFilter,
        name="test_list_instance",
        queryset=models.TestListInstance.objects.all(),
    )

    pass_fail = filters.Filter(
        name="pass_fail",
        widget=widgets.Select(choices=[('', 'Any')] + list(models.PASS_FAIL_CHOICES)),
    )

    created_by = filters.RelatedFilter(UserFilter, name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, name="modified_by", queryset=User.objects.all())

    work_started_min = MinDateFilter(name="work_started")
    work_started_max = MaxDateFilter(name="work_started")

    work_completed_min = MinDateFilter(name="work_completed")
    work_completed_max = MaxDateFilter(name="work_completed")

    review_date_min = MinDateFilter(name="review_date")
    review_date_max = MaxDateFilter(name="review_date")

    created_min = MinDateFilter(name="created")
    created_max = MaxDateFilter(name="created")
    modified_min = MinDateFilter(name="modified")
    modified_max = MaxDateFilter(name="modified")

    class Meta:
        model = models.TestInstance
        fields = {
            "review_date": ['exact'],
            "value": ['exact', 'in', 'gte', 'lte'],
            "string_value": ['icontains', 'in'],
            "skipped": ['exact'],
            "comment": ['icontains'],
            "work_started": ['exact'],
            "work_completed": ['exact'],
            "created": ['exact'],
            "modified": ['exact'],
        }


class TestListCycleMembershipFilter(filters.FilterSet):

    test_list = filters.RelatedFilter(TestListFilter, name="test_list", queryset=models.TestList.objects.all())
    cycle = filters.RelatedFilter(TestListCycleFilter, name="cycle", queryset=models.TestListCycle.objects.all())

    class Meta:
        model = models.TestListCycleMembership
        fields = {
            "order": ['exact', 'in'],
        }
