from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qa import models
from qatrack.qa.templatetags.qa_tags import as_time_delta
from qatrack.qatrack_core.utils import format_as_date, format_datetime
from qatrack.reports import filters
from qatrack.reports.reports import BaseReport, format_user


class UTCReport(BaseReport):

    report_type = "utc"
    name = _l("Test List Instances")
    filter_class = filters.UnitTestCollectionFilter
    description = mark_safe(
        _l(
            "This report includes details for all Test List Instances from a given time period for "
            "a given Unit Test List (Cycle) assignment."
        )
    )

    MAX_TLIS = getattr(settings, "REPORT_UTCREPORT_MAX_TLIS", 365)

    template = "reports/qc/utc.html"

    def filter_form_valid(self, filter_form):

        ntlis = self.filter_set.qs.count()
        if ntlis > self.MAX_TLIS:
            filter_form.add_error(
                "__all__", "This report can only be generated with %d or fewer Test List "
                "Instances.  Your filters are including %d. Please reduce the "
                "number of Test List (Cycle) assignments, or Work Completed time "
                "period." % (self.MAX_TLIS, ntlis)
            )

        return filter_form.is_valid()

    def get_queryset(self):
        return models.TestListInstance.objects.select_related("created_by")

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "unit-test-list-assignment-summary-report"), report_format)

    def get_unit_test_collection_details(self, val):
        utcs = models.UnitTestCollection.objects.filter(pk__in=val)
        return ("Unit / Test List", ', '.join("%s - %s" % (utc.unit.name, utc.name) for utc in utcs))

    def get_context(self):

        context = super().get_context()

        qs = self.filter_set.qs.select_related(
            "created_by",
            "modified_by",
            "reviewed_by",
            "test_list",
            "unit_test_collection",
            "unit_test_collection__unit",
            "unit_test_collection__content_type",
        ).prefetch_related(
            "comments",
            Prefetch("testinstance_set", queryset=models.TestInstance.objects.order_by("order")),
            "testinstance_set__unit_test_info__test",
            "testinstance_set__reference",
            "testinstance_set__tolerance",
            "testinstance_set__status",
            "testinstance_set__attachment_set",
            "attachment_set",
            "serviceevents_initiated",
            "rtsqa_for_tli",
        ).order_by("work_completed")
        context['queryset'] = qs

        form = self.get_filter_form()
        utcs = models.UnitTestCollection.objects.filter(pk__in=form.cleaned_data['unit_test_collection'])
        context['utcs'] = utcs

        context['site_name'] = ', '.join(sorted(set(utc.unit.site.name if utc.unit.site else _("N/A") for utc in utcs)))

        context['test_list_borders'] = self.get_borders(utcs)
        context['comments'] = self.get_comments(utcs)
        context['perms'] = PermWrapper(self.user)
        return context

    def get_borders(self, utcs):
        borders = {}
        for utc in utcs:
            for tl in utc.tests_object.all_lists():
                borders[tl.pk] = tl.sublist_borders()

        return borders

    def get_comments(self, utcs):
        from django_comments.models import Comment
        ct = ContentType.objects.get(model="testlistinstance").pk
        tlis = models.TestListInstance.objects.filter(
            unit_test_collection__id__in=utcs.values_list("id"),
        )

        comments_qs = Comment.objects.filter(
            content_type_id=ct,
            object_pk__in=map(str, tlis.values_list("id", flat=True)),
        ).order_by(
            "-submit_date",
        ).values_list(
            "pk",
            "submit_date",
            "user__username",
            "comment",
        )

        comments = dict((c[0], c[1:]) for c in comments_qs)
        return comments

    def to_table(self, context):

        rows = [
            [_("Report Title:"), context['report_title']],
            [_("View On Site:"), self.get_report_url()],
            [_("Report Type:"), context['report_name']],
            [_("Report Description:"), context['report_description']],
            [_("Generated:"), format_datetime(timezone.now())],
            [],
            ["Filters:"],
        ]

        for label, criteria in context['report_details']:
            rows.append([label + ":", criteria])

        for tli in context['queryset']:

            rows.extend([
                [],
                [],
                ["Test List Instance:", self.make_url(tli.get_absolute_url())],
                [_("Created By") + ":", format_user(tli.created_by)],
                [_("Work Started") + ":", format_as_date(tli.work_started)],
                [_("Work Completed") + ":", format_as_date(tli.work_completed)],
                [_("Duration") + ":", _("In Progress") if tli.in_progress else as_time_delta(tli.duration())],
                [_("Modified") + ":", format_as_date(tli.modified)],
                [_("Mofified By") + ":", format_user(tli.modified_by)],
            ])
            if tli.all_reviewed and not tli.reviewed_by:
                rows.extend([
                    [_("Reviewed") + ":", format_as_date(tli.modified)],
                    [_("Reviewed By") + ":", _("Auto Reviewed")],
                ])
            else:
                rows.extend([
                    [_("Reviewed") + ":", format_as_date(tli.reviewed)],
                    [_("Reviewed By") + ":", format_user(tli.reviewed_by)],
                ])

            for c in context['comments'].get(tli.pk, []):
                rows.append([_("Comment") + ":", format_datetime(c[0]), c[1], c[2]])

            for a in tli.attachment_set.all():
                rows.append([_("Attachment") + ":", a.label, self.make_url(a.attachment.url, plain=True)])

            rows.append([])
            rows.append([
                _("Test"),
                _("Value"),
                _("Reference"),
                _("Tolerance"),
                _("Pass/Fail"),
                _("Review Status"),
                _("Comment"),
                _("Attachments"),
            ])

            for ti, history in tli.history()[0]:
                row = [
                    ti.unit_test_info.test.name,
                    ti.value_display(coerce_numerical=False),
                    ti.reference.value_display() if ti.reference else "",
                    ti.tolerance.name if ti.tolerance else "",
                    ti.get_pass_fail_display(),
                    ti.status.name,
                    ti.comment,
                ]
                for a in ti.attachment_set.all():
                    row.append(self.make_url(a.attachment.url, plain=True))

                rows.append(row)

        return rows
