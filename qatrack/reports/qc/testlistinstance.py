from collections import defaultdict

from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch, Q
from django.template.loader import get_template
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qa import models
from qatrack.qa.templatetags.qa_tags import as_time_delta
from qatrack.qatrack_core.dates import format_as_date, format_datetime
from qatrack.reports import filters
from qatrack.reports.reports import BaseReport, format_user
from qatrack.units import models as umodels


class TestListInstanceSummaryReport(BaseReport):

    report_type = "testlistinstance_summary"
    name = _l("Test List Instance Summary")
    filter_class = filters.TestListInstanceFilter
    description = mark_safe(
        _l(
            "This report lists all Test List Instances from a given time period for "
            "selected sites, units, frequencies, and groups."
        )
    )

    MAX_TLIS = getattr(settings, "REPORT_QCSUMMARYREPORT_MAX_TLIS", 5000)

    category = _l("QC")

    template = "reports/qc/testlistinstance_summary.html"

    __test__ = False  # supress pytest warning

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
        return models.TestListInstance.objects.all()

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "test-list-instance-summary"), report_format)

    def get_unit_test_collection__unit__site_details(self, val):
        sites = [x.name if x != "null" else "Other" for x in val]
        return ("Site(s)", ", ".join(sites))

    def get_unit_test_collection__unit_details(self, val):
        units = models.Unit.objects.select_related("site").filter(pk__in=val)
        units = ('%s - %s' % (u.site.name if u.site else _("Other"), u.name) for u in units)
        return ("Unit(s)", ', '.join(units))

    def get_unit_test_collection__frequency_details(self, val):
        freqs = [x.name if x != "null" else "Ad Hoc" for x in val]
        return ("Frequencies", ", ".join(freqs))

    def get_context(self):

        context = super().get_context()

        # since we're grouping by site, we need to handle sites separately
        sites = self.filter_set.qs.order_by("unit_test_collection__unit__site__name").values_list(
            "unit_test_collection__unit__site", flat=True
        ).distinct()

        sites_data = []

        for site in sites:

            if site:  # site can be None here since not all units may have a site
                site = umodels.Site.objects.get(pk=site)

            sites_data.append((site.name if site else "", []))

            for tli in self.get_tlis_for_site(self.filter_set.qs, site):
                sites_data[-1][-1].append({
                    'unit_name': tli.unit_test_collection.unit.name,
                    'test_list_name': tli.test_list.name,
                    'due_date': format_as_date(tli.due_date),
                    'work_completed': self.get_work_completed(tli),
                    'pass_fail': self.get_pass_fail_status(tli),
                    'link': self.make_url(tli.get_absolute_url(), plain=True),
                })

        context['sites_data'] = sites_data

        return context

    def get_tlis_for_site(self, qs, site):
        """Get Test List Instances from filtered queryset for input site"""

        tlis = qs.filter(unit_test_collection__unit__site=site,).exclude(Q(work_completed=None) | Q(in_progress=True),)

        tlis = tlis.order_by(
            "unit_test_collection__unit__%s" % settings.ORDER_UNITS_BY,
            "unit_test_collection__name",
            "test_list__name",
            "work_completed",
        ).select_related(
            "test_list",
            "unit_test_collection",
            "unit_test_collection__unit",
            "unit_test_collection__frequency",
        ).prefetch_related("testinstance_set")

        return tlis

    def get_pass_fail_status(self, tli):
        """Format pass fail status with icons for html reports, otherwise just as plain text"""

        if self.html:
            if not hasattr(self, "_pass_fail_t"):
                self._pass_fail_t = get_template("qa/pass_fail_status.html")
            return self._pass_fail_t.render({'instance': tli, 'show_icons': True})

        return ", ".join("%d %s" % (len(t), d) for s, d, t in tli.pass_fail_status())

    def get_work_completed(self, tli):
        """Format work completed as link to instance if html report otherwise just return formatted date"""

        wc = format_as_date(tli.work_completed)

        if self.html:
            return self.make_url(tli.get_absolute_url(), wc, _("Click to view on site"))

        return wc

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        rows.append([
            _("Site"),
            _("Unit"),
            _("Test list"),
            _("Due Date"),
            _("Work Completed"),
            _("Pass/Fail Status"),
            _("Link"),
        ])

        for site, tlis in context['sites_data']:
            for tli in tlis:
                rows.append([
                    site,
                    tli['unit_name'],
                    tli['test_list_name'],
                    tli['due_date'],
                    tli['work_completed'],
                    tli['pass_fail'],
                    tli['link'],
                ])

        return rows


class TestListInstanceDetailsReport(BaseReport):

    report_type = "testlistinstance_details"
    name = _l("Test List Instance Details")
    filter_class = filters.TestListInstanceByUTCFilter
    description = mark_safe(
        _l(
            "This report includes details for all Test List Instances from a given time period for "
            "a given Unit Test List (Cycle) assignment."
        )
    )

    MAX_TLIS = getattr(settings, "REPORT_UTCREPORT_MAX_TLIS", 365)

    category = _l("QC")

    template = "reports/qc/testlistinstance_details.html"

    __test__ = False  # supress pytest warning

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
        return "%s.%s" % (slugify(self.name or "test-list-instance-details"), report_format)

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
            "testinstance_set__attachment_set",
            "attachment_set",
            "serviceevents_initiated",
            "rtsqa_for_tli",
        ).order_by("work_completed")
        context['queryset'] = qs

        form = self.get_filter_form()
        utcs = models.UnitTestCollection.objects.filter(pk__in=form.cleaned_data['unit_test_collection'])
        utcs = utcs.select_related('unit', 'unit__site')
        context['utcs'] = utcs

        context['site_name'] = ', '.join(sorted(set(utc.unit.site.name if utc.unit.site else _("N/A") for utc in utcs)))

        context['comments'] = self.get_comments(utcs)
        context['perms'] = PermWrapper(self.user)
        context['review_diff_col'] = settings.REVIEW_DIFF_COL
        return context

    def get_comments(self, utcs):
        from django_comments.models import Comment
        ct = ContentType.objects.get(model="testlistinstance").pk
        tlis = models.TestListInstance.objects.filter(unit_test_collection__id__in=utcs.values_list("id"),)

        comments_qs = Comment.objects.filter(
            content_type_id=ct,
            object_pk__in=map(str, tlis.values_list("id", flat=True)),
        ).order_by(
            "-submit_date",
        ).values_list(
            "object_pk",
            "submit_date",
            "user__username",
            "comment",
        )

        comments = defaultdict(list)
        for c in comments_qs:
            comments[int(c[0])].append(c[1:])

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
                [_("Duration") + ":",
                 _("In Progress") if tli.in_progress else as_time_delta(tli.duration())],
                [_("Modified") + ":", format_as_date(tli.modified)],
                [_("Modified By") + ":", format_user(tli.modified_by)],
                [_("Review Satus") + ":", tli.review_status.name],
            ])
            if tli.is_reviewed and not tli.reviewed_by:
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
            headers = [
                _("Test"),
                _("Value"),
                _("Reference"),
                _("Tolerance"),
            ]
            if settings.REVIEW_DIFF_COL:
                headers.append("Difference")
            headers.extend([
                _("Pass/Fail"),
                _("Comment"),
                _("Attachments"),
            ])
            rows.append(headers)

            for ti, history in tli.history()[0]:
                row = [
                    ti.unit_test_info.test.name,
                    ti.value_display(coerce_numerical=False),
                    ti.reference.value_display() if ti.reference else "",
                    ti.tolerance.name if ti.tolerance else "",
                ]
                if settings.REVIEW_DIFF_COL and not ti.string_value:
                    row.append(ti.diff_display())
                row.extend([
                    ti.get_pass_fail_display(),
                    ti.comment,
                ])
                for a in ti.attachment_set.all():
                    row.append(self.make_url(a.attachment.url, plain=True))

                rows.append(row)

        return rows
