import base64
from collections import defaultdict
import copy
import json
from numbers import Number
import re

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db.transaction import atomic
from django.utils import timezone
from django_comments.models import Comment
from rest_framework import serializers
from rest_framework.reverse import reverse

from qatrack.api.attachments.serializers import AttachmentSerializer
from qatrack.attachments.models import Attachment
from qatrack.qa import models, signals
from qatrack.qa.views.perform import CompositePerformer, UploadHandler
from qatrack.qatrack_core.serializers import QATrackJSONEncoder
from qatrack.qatrack_core.utils import parse_date, parse_datetime
from qatrack.service_log import models as sl_models

BASE64_RE = re.compile("^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{4}|[A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{2}==)$")


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


class AutoReviewRuleSetSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.AutoReviewRuleSet
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


class UTCTestsObjectRelatedField(serializers.RelatedField):
    """
    A custom field to use for the `tests_object` generic relationship.
    """

    def to_representation(self, obj):
        if isinstance(obj, models.TestList):
            return reverse("testlist-detail", kwargs={'pk': obj.pk}, request=self.context['request'])
        return reverse("testlistcycle-detail", kwargs={'pk': obj.pk}, request=self.context['request'])


class UnitTestCollectionSerializer(serializers.HyperlinkedModelSerializer):

    tests_object = UTCTestsObjectRelatedField(read_only=True)

    class Meta:
        model = models.UnitTestCollection
        fields = "__all__"

    def get_tests_object(self, obj):
        if isinstance(obj, models.TestList):
            return reverse("testlist-detail", kwargs={'pk': obj.pk}, request=self.context['request'])
        return reverse("testlistcycle-detail", kwargs={'pk': obj.pk}, request=self.context['request'])


class TestInstanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.TestInstance
        fields = "__all__"


class TestInstanceCreator(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.TestInstance
        fields = ["value", "string_value", "date_value", "datetime_value", "skipped", "comment", "macro"]


class TestListInstanceSerializer(serializers.HyperlinkedModelSerializer):

    attachments = AttachmentSerializer(many=True, source="attachment_set", required=False)

    site_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.TestListInstance
        fields = "__all__"

    def get_site_url(self, obj):
        if obj:
            return reverse("view_test_list_instance", kwargs={'pk': obj.pk}, request=self.context['request'])
        return ""


class TestListInstanceCreator(serializers.HyperlinkedModelSerializer):

    work_completed = serializers.DateTimeField(default=lambda: timezone.now())

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

    attachments = serializers.ListField(required=False)

    # made read_only since we get the test list from the UTC & day
    test_list = serializers.HyperlinkedRelatedField(
        view_name="testlist-detail",
        read_only=True,
    )

    site_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.TestListInstance
        exclude = [
            "modified",
            "modified_by",
            "created",
        ]

    def get_site_url(self, obj):
        if obj:
            return reverse("view_test_list_instance", kwargs={'pk': obj.pk}, request=self.context['request'])
        return ""

    def validate_tests(self, tests):
        err_fields = ['"%s"' % slug for slug, data in tests.items() if not self.valid_test(data)]
        if err_fields:
            fields = ', '.join(err_fields)
            msg = '%s field(s) have errors. Test data must be a dictionary ' % fields
            raise serializers.ValidationError(msg)
        return tests

    def validate_attachments(self, attachments):
        attach_objs = []
        for attach in attachments:
            is_dict = isinstance(attach, dict)
            if not is_dict or 'filename' not in attach or 'value' not in attach:
                msg = (
                    '`attachments` field must be list of form '
                    '[{"filename": "file_name.txt", "value": "<base64 encoded bytes|text>", '
                    '"encoding": "<base64|text>], ...]'
                )
                raise serializers.ValidationError(msg)
            attach_objs.append(self.make_attachment(attach))
        return attach_objs

    def make_attachment(self, data):
        content = data['value']
        if data.get("encoding", "base64") == "base64":
            if not BASE64_RE.match(content):
                raise serializers.ValidationError("base64 encoding requested but content does not appear to be base64")

            content = base64.b64decode(content)

        user = self.context['request'].user

        return Attachment(
            attachment=ContentFile(content, data['filename']),
            comment="Uploaded %s by %s" % (timezone.now(), user.username),
            label=data['filename'],
            created_by=user,
        )

    def valid_test(self, test_data):
        is_dict = isinstance(test_data, dict)
        return is_dict

    def add_data_from_instance(self, data):

        tis = self.instance.testinstance_set.select_related(
            "unit_test_info",
            "unit_test_info__test",
        )
        if "tests" not in data:
            data['tests'] = {}
        for ti in tis:
            test = ti.unit_test_info.test
            slug = test.slug
            if slug not in data['tests']:
                if test.is_upload():
                    upload = ti.get_value()
                    data['tests'][slug] = {
                        'value': base64.b64encode(upload.attachment.read()).decode(),
                        'encoding': 'base64',
                        'filename': ti.string_value,
                        'comment': ti.comment,
                    }
                else:
                    data['tests'][slug] = {
                        'value': ti.get_value(),
                        'comment': ti.comment,
                    }
            elif slug in data['tests'] and data['tests'][slug].get('skipped'):
                data['tests'][slug] = {
                    'value': None,
                    'comment': data['tests'][slug].get("comment", ti.comment),
                    'skipped': True,
                }

        for key in ["work_completed", "work_started", "in_progress"]:
            data[key] = data.get(key, getattr(self.instance, key))

    def validate(self, data):
        post_data = copy.deepcopy(data)

        validated_data = super(TestListInstanceCreator, self).validate(data)

        if self.instance:
            self.add_data_from_instance(validated_data)

        validated_data = self.preprocess(validated_data)

        test_qs = self.tl.all_tests().values_list("slug", "type", "calculation_procedure")

        missing = []
        wrong_types = []
        invalid_autos = []
        msgs = []
        auto_types = [models.CONSTANT] + list(models.CALCULATED_TYPES)

        for slug, type_, procedure in test_qs:

            if slug not in validated_data['tests']:
                missing.append(slug)
                continue

            skipped = validated_data['tests'][slug].get("skipped")
            provided_val = post_data.get('tests', {}).get(slug, {}).get("value")
            validated_val = validated_data['tests'][slug].get("value")
            if not skipped and type_ not in auto_types and not self.type_okay(type_, validated_val):
                wrong_types.append(slug)

            if type_ in auto_types and not self.autovalue_ok(validated_val, provided_val):
                invalid_autos.append(slug)

            d = validated_data['tests'][slug]
            if type_ in models.STRING_TYPES and slug in validated_data['tests']:
                d['string_value'] = d.pop('value', "")
            elif type_ == models.DATE and slug in validated_data['tests']:
                d['date_value'] = parse_date(d.pop('value', ""))
            elif type_ == models.DATETIME and slug in validated_data['tests']:
                d['datetime_value'] = parse_datetime(d.pop('value', ""))
            elif type_ == models.UPLOAD and slug in validated_data['tests']:
                # remove base64 data
                d.pop('value', "")
                # string value needs to be set to attachment id for later editing
                d['string_value'] = self.ti_attachments[slug][0]
                d['json_value'] = json.dumps(self.ti_upload_analysis_data[slug], cls=QATrackJSONEncoder)

        if missing:
            msgs.append("Missing data for tests: %s" % ', '.join(missing))

        if wrong_types:
            msgs.append("Wrong value type (number/string) for tests: %s" % ', '.join(wrong_types))

        if invalid_autos:
            msgs.append(
                "The following tests are calculated automatically and should not have values "
                "provided: %s" % ', '.join(invalid_autos)
            )

        if validated_data['work_completed'] < validated_data['work_started']:
            msgs.append("work_completed date must be after work_started")

        if msgs:
            raise serializers.ValidationError('\n'.join(msgs))

        return validated_data

    def type_okay(self, type_, val):
        if type_ in models.STRING_TYPES + models.DATE_TYPES and not isinstance(val, str):
            return False
        elif type_ in models.NUMERICAL_TYPES and not isinstance(val, Number):
            return False
        return True

    def autovalue_ok(self, calculated, provided):
        not_provided = provided in (None, "")
        values_match = calculated == provided
        return not_provided or values_match

    def preprocess(self, validated_data):

        if self.instance:
            self.utc = self.instance.unit_test_collection
            self.day = self.instance.day
            self.tl = self.instance.test_list
        else:
            self.utc = validated_data['unit_test_collection']
            self.day = validated_data.get('day', 0)
            self.day, self.tl = self.utc.get_list(day=self.day)

        test_qs = self.tl.all_tests().values_list("id", "slug", "type", "constant_value")

        has_calculated = False
        uploads = []
        for pk, slug, type_, cv in test_qs:

            has_calculated = has_calculated or type_ in models.CALCULATED_TYPES

            if type_ == models.CONSTANT:
                # here we get data for the test (comments etc) and make sure the constant value
                # is set correctly (so the user can't send an incorrect value for the constant value)
                d = validated_data['tests'].get(slug, {})
                v = d.get("value")
                if v not in ("", None) and v != cv:
                    raise serializers.ValidationError("Incorrect constant value passed for %s" % slug)
                d['value'] = cv
                validated_data['tests'][slug] = d
            elif type_ == models.UPLOAD:
                d = validated_data['tests'].get(slug, {})
                uploads.append((pk, slug, d))
            elif type_ in models.CALCULATED_TYPES:
                if slug not in validated_data['tests']:
                    validated_data['tests'][slug] = {'value': ''}
                elif 'value' not in validated_data['tests'][slug]:
                    validated_data['tests'][slug]['value'] = ""

        self.ti_attachments = defaultdict(list)
        self.ti_upload_analysis_data = {}

        user = self.context['request'].user

        if has_calculated:

            comp_calc_data = self.data_to_composite(validated_data)
            for pk, slug, d in uploads:
                comp_calc_data['test_id'] = pk
                try:
                    fname = d['filename']
                except KeyError:
                    raise serializers.ValidationError("%s is missing the filename field" % slug)

                content = d['value']

                if d.get("encoding", "base64") == "base64":
                    if not BASE64_RE.match(content):
                        raise serializers.ValidationError(
                            "base64 encoding requested but content does not appear to be base64"
                        )
                    content = base64.b64decode(content)

                f = ContentFile(content, fname)
                test_data = UploadHandler(user, comp_calc_data, f).process()
                if test_data['errors']:
                    raise serializers.ValidationError("Error with %s test: %s" % (slug, '\n'.join(test_data['errors'])))

                self.ti_attachments[slug].append(test_data['attachment_id'])
                self.ti_attachments[slug].extend([a['attachment_id'] for a in test_data['user_attached']])
                self.ti_upload_analysis_data[slug] = test_data['result']

                data = validated_data['tests'].get(slug, {})
                comment_sources = [data.get("comment", ""), test_data.get("comment")]
                comp_calc_data['comments'][slug] = '\n'.join(c for c in comment_sources if c)
                comp_calc_data['tests'][slug] = test_data['result']
                comp_calc_data.pop('test_id', None)

            results = CompositePerformer(user, comp_calc_data).calculate()
            if not results['success']:  # pragma: no cover
                raise serializers.ValidationError(', '.join(results.get("errors", [])))

            for slug, test_data in results['results'].items():
                if test_data['error']:
                    raise serializers.ValidationError("Error with %s test: %s" % (slug, test_data['error']))

                data = validated_data['tests'].get(slug, {})
                data['comment'] = '\n'.join(c for c in [data.get("comment", ""), test_data.get("comment")] if c)
                data['value'] = test_data['value']
                validated_data['tests'][slug] = data

                self.ti_attachments[slug].extend([a['attachment_id'] for a in test_data['user_attached']])

        return validated_data

    def data_to_composite(self, validated_data):
        """Convert API post data to format suitable for CompositePerformer"""

        data = {
            'tests': {k: v.get("value") for k, v in validated_data['tests'].items()},
            'meta': {
                'test_list_name': self.tl.name,
                'unit_number': self.utc.unit.number,
                'cycle_day': self.day,
                'work_completed': validated_data['work_completed'],
                'work_started': validated_data['work_started'],
                'username': self.context['request'].user.username,
            },
            'test_list_id': self.tl.id,
            'unit_id': self.utc.unit.id,
            'comments': {k: v.get("comment") for k, v in validated_data['tests'].items()}
        }
        return data

    @atomic
    def create(self, validated_data):

        utc = validated_data['unit_test_collection']
        user = validated_data['created_by']
        tl = validated_data['test_list']

        # data for creating all test instances
        test_instance_data = validated_data.pop('tests')

        # fields for creating test list instance comment
        self.comment = validated_data.pop("comment", "")

        # user set test instance status or default
        user_set_status = validated_data.pop('status', None)
        status = user_set_status or models.TestInstanceStatus.objects.default()
        if status is None:
            raise serializers.ValidationError("No test instance status available")

        # related return to service
        rtsqa = validated_data.pop('return_to_service_qa', None)

        # attachments for test list instance
        attachments = validated_data.pop('attachments', [])

        tli = models.TestListInstance(**validated_data)
        tli.reviewed = None if status.requires_review else tli.modified
        tli.reviewed_by = None if status.requires_review else user
        tli.save()

        for attachment in attachments:
            attachment.testlistinstance = tli
            attachment.save()

        if self.comment:
            self.create_comment(self.comment, tli)

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
        for order, uti in enumerate(ordered_utis):
            data = test_instance_data[uti.test.slug]
            ti = models.TestInstance(
                value=data.get("value"),
                string_value=data.get("string_value", ""),
                json_value=data.get("json_value", ""),
                date_value=data.get("date_value"),
                datetime_value=data.get("datetime_value"),
                skipped=data.get("skipped", False),
                comment=data.get("comment", ""),
                unit_test_info=uti,
                reference=uti.reference,
                tolerance=uti.tolerance,
                status=status,
                order=order,
                created=tli.created,
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

        for slug, attachment_ids in self.ti_attachments.items():
            for a in Attachment.objects.filter(id__in=attachment_ids):
                a.testinstance = tli.testinstance_set.get(unit_test_info__test__slug=slug)
                a.save()

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
            except:  # pragma: no cover, # noqa: E722
                pass

        return tli

    @atomic
    def update(self, instance, validated_data):

        now = timezone.now()
        utc = instance.unit_test_collection
        user = self.context['request'].user

        # data for creating all test instances
        test_instance_data = validated_data.pop('tests')

        # fields for creating test list instance comment
        self.comment = validated_data.pop("comment", "")

        # user set test instance status or default
        user_set_status = validated_data.pop('status', None)
        status = user_set_status or models.TestInstanceStatus.objects.default()

        # related return to service
        rtsqa = validated_data.pop('return_to_service_qa', None)

        # new attachments for test list instance
        attachments = validated_data.pop('attachments', [])

        instance.work_completed = validated_data['work_completed']
        instance.work_started = validated_data['work_started']
        instance.in_progress = validated_data['in_progress']

        instance.modified_by = user
        instance.modified = timezone.now()
        instance.reviewed = None
        instance.reviewed_by = None
        instance.all_reviewed = False

        if not status.requires_review:
            instance.reviewed = now
            instance.reviewed_by = user
            instance.all_reviewed = True

        instance.work_complete = instance.work_completed or now

        instance.save()

        for attachment in attachments:
            attachment.testlistinstance = instance
            attachment.save()

        if self.comment:
            self.create_comment(self.comment, instance)

        tis = instance.testinstance_set.select_related(
            "unit_test_info",
            "unit_test_info__test",
            "unit_test_info__reference",
            "unit_test_info__tolerance",
        )
        for ti in tis:
            tid = test_instance_data[ti.unit_test_info.test.slug]
            ti.status = status
            ti.modified_by = user
            ti.work_started = instance.work_started
            ti.work_completed = instance.work_completed
            ti.skipped = tid.get("skipped", ti.skipped)
            ti.value = tid.get("value", ti.value)
            ti.string_value = tid.get("string_value", ti.string_value)
            ti.date_value = tid.get("date_value", ti.date_value)
            ti.datetime_value = tid.get("datetime_value", ti.datetime_value)
            ti.skipped = tid.get("skipped", False)
            ti.comment = tid.get("comment", ti.comment)

            ti.calculate_pass_fail()
            if not user_set_status:
                ti.auto_review()

            ti.save()

        utc.set_due_date()

        # is there an existing rtsqa being linked?
        if rtsqa:
            rtsqa.test_list_instance = instance
            rtsqa.save()

            # If tli needs review, update 'Unreviewed RTS QA' counter
            if not instance.all_reviewed:
                cache.delete(settings.CACHE_RTS_QA_COUNT)

        instance.update_all_reviewed()

        if not instance.in_progress:
            try:
                signals.testlist_complete.send(sender=self, instance=instance, created=False)
            except:  # pragma: no cover, # noqa: E722
                pass

        return instance

    def create_comment(self, comment, tli):
        site = get_current_site(self.context['request'])
        user = self.context['request'].user
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
                "date_value": ti.date_value,
                "datetime_value": ti.datetime_value,
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

        if not hasattr(self, "comment"):
            self.comment = ''
            if self.instance:
                self.comment = '\n'.join(
                    '%s:%s:%s' % (c.user.username, c.submit_date, c.comment) for c in self.instance.comments.all()
                )

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
