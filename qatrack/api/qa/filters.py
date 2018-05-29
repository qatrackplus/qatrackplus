import rest_framework_filters as filters

from qatrack.api.auth.filters import Group, GroupFilter, User, UserFilter
from qatrack.api.units.filters import UnitFilter
from qatrack.qa import models
from qatrack.units.models import Unit


class FrequencyFilter(filters.FilterSet):

    class Meta:
        model = models.Frequency
        fields = {
            "name": "__all__",
            "slug": "__all__",
            "nominal_interval": "__all__",
            "due_interval": "__all__",
            "overdue_interval": "__all__",
        }


class TestInstanceStatusFilter(filters.FilterSet):

    class Meta:
        model = models.TestInstanceStatus
        fields = {
            "name": "__all__",
            "slug": "__all__",
            "description": "__all__",
            "is_default": "__all__",
            "requires_review": "__all__",
            "export_by_default": "__all__",
            "valid": "__all__",
        }


class AutoReviewRuleFilter(filters.FilterSet):

    status = filters.RelatedFilter(
        TestInstanceStatusFilter,
        name="status",
        queryset=models.TestInstanceStatus.objects.all(),
    )

    class Meta:
        model = models.AutoReviewRule
        fields = {
            "pass_fail": "__all__",
        }


class ReferenceFilter(filters.FilterSet):

    created_by = filters.RelatedFilter(UserFilter, name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, name="modified_by", queryset=User.objects.all())

    class Meta:
        model = models.Reference
        fields = {
            "name": "__all__",
            "type": "__all__",
            "value": "__all__",
            "created": "__all__",
            "modified": "__all__",
        }


class ToleranceFilter(filters.FilterSet):

    class Meta:
        model = models.Tolerance
        fields = {
            "type": "__all__",
            "act_low": "__all__",
            "tol_low": "__all__",
            "tol_high": "__all__",
            "act_high": "__all__",
            "mc_pass_choices": "__all__",
            "mc_tol_choices": "__all__",
            "bool_warning_only": "__all__",
        }


class CategoryFilter(filters.FilterSet):

    class Meta:
        model = models.Category
        fields = {
            "name": "__all__",
            "slug": "__all__",
            "description": "__all__",
        }


class TestFilter(filters.FilterSet):

    created_by = filters.RelatedFilter(UserFilter, name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, name="modified_by", queryset=User.objects.all())
    category = filters.RelatedFilter(CategoryFilter, name="category", queryset=models.Category.objects.all())

    class Meta:
        model = models.Test
        fields = {
            "name": "__all__",
            "slug": "__all__",
            "description": "__all__",
            "procedure": "__all__",
            "chart_visibility": "__all__",
            "auto_review": "__all__",
            "type": "__all__",
            "hidden": "__all__",
            "skip_without_comment": "__all__",
            "display_image": "__all__",
            "choices": "__all__",
            "constant_value": "__all__",
            "created": "__all__",
            "modified": "__all__",
        }


class UnitTestCollectionFilter(filters.FilterSet):

    unit = filters.RelatedFilter(UnitFilter, name="unit", queryset=Unit.objects.all())
    frequency = filters.RelatedFilter(FrequencyFilter, name="frequency", queryset=models.Frequency.objects.all())
    assigned_to = filters.RelatedFilter(GroupFilter, name="assigned_to", queryset=Group.objects.all())
    visible_to = filters.RelatedFilter(GroupFilter, name="visible_to", queryset=Group.objects.all())
    last_instance = filters.RelatedFilter(
        "TestListInstanceFilter", name="last_instance", queryset=models.TestListInstance.objects.all()
    )

    class Meta:
        model = models.UnitTestCollection
        fields = {
            "due_date": "__all__",
            "auto_schedule": "__all__",
            "active": "__all__",
            "name": "__all__",
        }


class TestListFilter(filters.FilterSet):

    created_by = filters.RelatedFilter(UserFilter, name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, name="modified_by", queryset=User.objects.all())
    tests = filters.RelatedFilter(TestFilter, name="tests", queryset=models.Test.objects.all())
    utcs = filters.RelatedFilter(
        UnitTestCollectionFilter,
        name="utcs",
        queryset=models.UnitTestCollection.objects.all(),
    )

    class Meta:
        model = models.TestList
        fields = {
            "name": "__all__",
            "slug": "__all__",
            "description": "__all__",
            "warning_message": "__all__",
            "created": "__all__",
            "modified": "__all__",
        }


class TestListInstanceFilter(filters.FilterSet):

    unit_test_collection = filters.RelatedFilter(
        UnitTestCollectionFilter,
        name="unit_test_collection",
        queryset=models.UnitTestInfo.objects.all(),
    )
    test_list = filters.RelatedFilter(TestListFilter, name="test_list", queryset=models.TestList.objects.all())

    reviewed_by = filters.RelatedFilter(UserFilter, name="reviewed_by", queryset=User.objects.all())
    created_by = filters.RelatedFilter(UserFilter, name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, name="modified_by", queryset=User.objects.all())

    class Meta:
        model = models.TestListInstance
        fields = {
            "due_date": "__all__",
            "in_progress": "__all__",
            "reviewed": "__all__",
            "all_reviewed": "__all__",
            "day": "__all__",
            "work_started": "__all__",
            "work_completed": "__all__",
            "created": "__all__",
            "modified": "__all__",
        }


class UnitTestInfoFilter(filters.FilterSet):

    unit = filters.RelatedFilter(UnitFilter, name="unit", queryset=Unit.objects.all())
    test = filters.RelatedFilter(TestFilter, name="test", queryset=models.Test.objects.all())
    reference = filters.RelatedFilter(ReferenceFilter, name="reference", queryset=models.Reference.objects.all())
    tolerance = filters.RelatedFilter(ToleranceFilter, name="tolerance", queryset=models.Tolerance.objects.all())

    class Meta:
        model = models.UnitTestInfo
        fields = {
            "active": "__all__",
        }


class TestListMembershipFilter(filters.FilterSet):

    test_list = filters.RelatedFilter(TestListFilter, name="test_list", queryset=models.TestList.objects.all())
    test = filters.RelatedFilter(TestFilter, name="test", queryset=models.Test.objects.all())

    class Meta:
        model = models.TestListMembership
        fields = {
            "order": "__all__",
        }


class SublistFilter(filters.FilterSet):

    parent = filters.RelatedFilter(TestListFilter, name="parent", queryset=models.TestList.objects.all())
    child = filters.RelatedFilter(TestListFilter, name="child", queryset=models.TestList.objects.all())

    class Meta:
        model = models.Sublist
        fields = {
            "order": "__all__",
            "outline": "__all__",
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
    created_by = filters.RelatedFilter(UserFilter, name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, name="modified_by", queryset=User.objects.all())

    class Meta:
        model = models.TestInstance
        fields = {
            "review_date": "__all__",
            "pass_fail": "__all__",
            "value": "__all__",
            "string_value": "__all__",
            "skipped": "__all__",
            "comment": "__all__",
            "work_started": "__all__",
            "work_completed": "__all__",
            "created": "__all__",
            "modified": "__all__",
        }


class TestListCycleFilter(filters.FilterSet):

    created_by = filters.RelatedFilter(UserFilter, name="created_by", queryset=User.objects.all())
    modified_by = filters.RelatedFilter(UserFilter, name="modified_by", queryset=User.objects.all())
    test_lists = filters.RelatedFilter(TestListFilter, name="test_lists", queryset=models.TestList.objects.all())
    utcs = filters.RelatedFilter(
        UnitTestCollectionFilter,
        name="utcs",
        queryset=models.UnitTestCollection.objects.all(),
    )

    class Meta:
        model = models.TestListCycle
        fields = {
            "name": "__all__",
            "slug": "__all__",
            "description": "__all__",
            "drop_down_label": "__all__",
            "day_option_text": "__all__",
            "created": "__all__",
            "modified": "__all__",
        }


class TestListCycleMembershipFilter(filters.FilterSet):

    test_list = filters.RelatedFilter(TestListFilter, name="test_list", queryset=models.TestList.objects.all())
    cycle = filters.RelatedFilter(TestListCycleFilter, name="cycle", queryset=models.TestListCycle.objects.all())

    class Meta:
        model = models.TestListCycleMembership
        fields = {
            "order": "__all__",
        }
