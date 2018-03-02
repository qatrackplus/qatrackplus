from django_comments.models import Comment
from django.conf import settings
from django.core.cache import cache
from django.db.transaction import atomic
from django.utils import timezone
from rest_framework import serializers
from rest_framework.reverse import reverse

from qatrack.qa import models, signals
from qatrack.service_log import models as sl_models


class FrequencySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Frequency
        fields = "__all__"


class TestInstanceStatusSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.TestInstanceStatus
        fields = "__all__"


class AutoReviewRuleSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.AutoReviewRule
        fields = "__all__"


class ReferenceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Reference
        fields = "__all__"


class ToleranceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Tolerance
        fields = "__all__"


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Category
        fields = "__all__"


class TestSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Test
        fields = "__all__"


class TestListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.TestList
        fields = "__all__"


class UnitTestInfoSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.UnitTestInfo
        fields = "__all__"


class TestListMembershipSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.TestListMembership
        fields = "__all__"


class SublistSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Sublist
        fields = "__all__"


class UnitTestCollectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.UnitTestCollection
        fields = "__all__"


class TestInstanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.TestInstance
        fields = "__all__"


class TestInstanceCreator(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.TestInstance
        fields = ["value", "string_value", "skipped", "comment", "macro"]


class TestListInstanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.TestListInstance
        fields = "__all__"


class TestListInstanceCreator(serializers.HyperlinkedModelSerializer):

    comment = serializers.CharField(required=False)
    tests = serializers.DictField()
    status = serializers.HyperlinkedRelatedField(
        view_name="testinstancestatus-detail",
        queryset=models.TestInstanceStatus.objects.all(),
        required=False,
    )

    return_to_service_qa = serializers.HyperlinkedRelatedField(
        view_name="returntoserviceqa-detail",
        queryset=sl_models.ReturnToServiceQA.objects.all(),
        required=False,
    )

    unit_test_collection = serializers.HyperlinkedRelatedField(
        view_name="unittestcollection-detail",
        queryset=models.UnitTestCollection.objects.all(),
    )

    # made read_only since we get the test list from the UTC & day
    test_list = serializers.HyperlinkedRelatedField(
        view_name="testlist-detail",
        read_only=True,
    )

    class Meta:
        model = models.TestListInstance
        exclude = [
            "modified",
            "modified_by",
            "created",
        ]

    def validate_tests(self, tests):
        err_fields = ['"%s"' % slug for slug, data in tests.items() if not self.valid_test(data)]
        if err_fields:
            fields = ', '.join(err_fields)
            msg = '%s field(s) have errors. Each test must contain either a "value" or "string_value" field' % fields
            raise serializers.ValidationError(msg)
        return tests

    def valid_test(self, test_data):
        return 'value' in test_data or 'string_value' in test_data

    def validate_work_completed(self, wc):
        return wc or timezone.now()

    def validate(self, data):
        validated_data = super(TestListInstanceCreator, self).validate(data)
        utc = validated_data['unit_test_collection']
        day = validated_data.get('day', 0)
        day, tl = utc.get_list(day=day)
        slugs = tl.all_tests().values_list("slug", flat=True)
        missing = ', '.join([s for s in slugs if s not in data['tests']])
        if missing:
            raise serializers.ValidationError("Missing data for tests: %s" % missing)

        if validated_data['work_completed'] < validated_data['work_started']:
            raise serializers.ValidationError("work_completed date must be after work_started")

        return validated_data

    @atomic
    def create(self, validated_data):

        utc = validated_data['unit_test_collection']
        user = validated_data['created_by']
        tl = validated_data['test_list']

        # data for creating all test instances
        test_instance_data = validated_data.pop('tests')

        # fields for creating test list instance comment
        self.comment = validated_data.pop("comment", "")
        site = validated_data.pop("site", "")

        # user set test instance status or default
        user_set_status = validated_data.pop('status', None)
        status = user_set_status or models.TestInstanceStatus.objects.default()

        # related return to service
        rtsqa = validated_data.pop('return_to_service_qa', None)

        tli = models.TestListInstance(**validated_data)
        tli.reviewed = None if status.requires_review else tli.modified
        tli.reviewed_by = None if status.requires_review else user
        tli.save()

        if self.comment:
            self.create_comment(self.comment, user, tli, site)

        tests = tl.ordered_tests()
        utis = models.UnitTestInfo.objects.filter(
            unit=utc.unit,
            test__in=tests,
            active=True,
        ).select_related(
            "reference",
            "test__category",
            "tolerance",
            "unit",
        )

        # make sure utis are correctly ordered
        uti_tests = [x.test for x in utis]
        ordered_utis = [utis[uti_tests.index(test)] for test in tests]
        to_save = []
        for delta, uti in enumerate(ordered_utis):
            now = tli.created + timezone.timedelta(milliseconds=delta)
            data = test_instance_data[uti.test.slug]
            ti = models.TestInstance(
                value=data.get("value", None),
                string_value=data.get("string_value", ""),
                skipped=data.get("skipped", False),
                comment=data.get("comment", ""),
                unit_test_info=uti,
                reference=uti.reference,
                tolerance=uti.tolerance,
                status=status,
                created=now,
                created_by=user,
                modified_by=user,
                test_list_instance=tli,
                work_started=tli.work_started,
                work_completed=tli.work_completed,
            )

            ti.calculate_pass_fail()
            if not user_set_status:
                ti.auto_review()

            to_save.append(ti)

        models.TestInstance.objects.bulk_create(to_save)

        # set due date to account for any non default statuses
        tli.unit_test_collection.set_due_date()

        # is there an existing rtsqa being linked?
        if rtsqa:
            rtsqa.test_list_instance = tli
            rtsqa.save()

            # If tli needs review, update 'Unreviewed RTS QA' counter
            if not tli.all_reviewed:
                cache.delete(settings.CACHE_RTS_QA_COUNT)

        tli.update_all_reviewed()

        if not tli.in_progress:
            # TestListInstance & TestInstances have been successfully create, fire signal
            # to inform any listeners (e.g notifications.handlers.email_no_testlist_save)
            try:
                signals.testlist_complete.send(sender=self, instance=tli, created=False)
            except:
                pass

        return tli

    def create_comment(self, comment, user, tli, site):
        Comment.objects.create(
            submit_date=timezone.now(),
            user=user,
            content_object=tli,
            comment=comment,
            site=site,
        )

    def to_representation(self, obj):
        # Monkeypatch on a tests dict here since it doesn't actually
        # exist on the TestListInstance object
        base_url = reverse("testinstance-list")
        base_status_url = reverse("testinstancestatus-list")
        base_ref_url = reverse("reference-list")
        base_tol_url = reverse("tolerance-list")
        qs = obj.testinstance_set.select_related(
            'status',
            'reference',
            'tolerance',
            'unit_test_info__test',
        )
        obj.status = None
        obj.return_to_service_qa = None
        obj.tests = {}
        for ti in qs:
            status = base_status_url + "%d/" % ti.status.pk
            tol = base_tol_url + "%d/" % ti.tolerance.pk if ti.tolerance else None
            ref = base_ref_url + "%d/" % ti.reference.pk if ti.reference else None
            obj.tests[ti.unit_test_info.test.slug] = {
                "url": base_url + "%d/" % ti.pk,
                "value": ti.value,
                "string_value": ti.string_value,
                "value_display": ti.value_display(),
                "diff_display": ti.diff_display(),
                "pass_fail": (ti.pass_fail, ti.get_pass_fail_display()),
                "skipped": ti.skipped,
                "comment": ti.comment,
                "status": status,
                "reference": ref,
                "tolerance": tol,
                "attachments": [a.attachment.url for a in ti.attachment_set.all()],
            }

        rep = super(TestListInstanceCreator, self).to_representation(obj)
        if self.comment:
            rep['comment'] = self.comment

        rep.pop("return_to_service_qa", None)
        rep.pop("status", None)

        return rep


class TestListCycleSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.TestListCycle
        fields = "__all__"


class TestListCycleMembershipSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.TestListCycleMembership
        fields = "__all__"
