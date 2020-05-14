from django.contrib.sites.models import Site
from django.core.files.base import ContentFile
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.translation import gettext as _
from django_comments.models import Comment
import pytz

from qatrack.attachments.models import Attachment
from qatrack.qa.models import Frequency, TestListInstance
from qatrack.qa.tests import utils
from qatrack.reports import qc
from qatrack.units.models import Site as USite


class TestQCSummaryReport(TestCase):

    def test_filter_form_valid(self):
        """If queryset.count() > MAX_TLIS then filter_form should get an error added"""
        rep = qc.QCSummaryReport()
        rep.MAX_TLIS = -1
        ff = rep.get_filter_form()
        resp = rep.filter_form_valid(ff)
        assert resp is False
        assert '__all__' in ff.errors and "Please reduce" in ff.errors['__all__'][0]

    def test_get_queryset(self):
        assert qc.QCSummaryReport().get_queryset().model._meta.model_name == "testlistinstance"

    def test_get_filename(self):
        assert qc.QCSummaryReport().get_filename('pdf') == 'qc-summary.pdf'

    def test_get_utc_site(self):
        site = USite.objects.create(name="site")
        sites = qc.QCSummaryReport().get_unit_test_collection__unit__site_details([site, 'null'])
        assert sites == ('Site', 'site, Other')

    def test_get_utc_freq(self):
        freq = Frequency.objects.create(name="freq", window_start=0, window_end=0)
        freqs = qc.QCSummaryReport().get_unit_test_collection__frequency_details([freq, 'null'])
        assert freqs == ('Frequencies', 'freq, Ad Hoc')

    @override_settings(TIME_ZONE="America/Toronto")
    def test_get_work_completed_html(self):
        rep = qc.QCSummaryReport()
        rep.report_format = "html"
        tz = pytz.timezone("America/Toronto")
        work_completed = tz.localize(timezone.datetime(2019, 1, 1, 12))
        tli = utils.create_test_list_instance(work_completed=work_completed)
        wc = rep.get_work_completed(tli)
        assert "01 Jan 2019" in wc
        assert "href" in wc

    @override_settings(TIME_ZONE="America/Toronto")
    def test_get_work_completed_plain(self):
        rep = qc.QCSummaryReport()
        rep.report_format = "csv"
        tz = pytz.timezone("America/Toronto")
        work_completed = tz.localize(timezone.datetime(2019, 1, 1, 12))
        tli = utils.create_test_list_instance(work_completed=work_completed)
        wc = rep.get_work_completed(tli)
        assert "01 Jan 2019" in wc
        assert "href" not in wc

    @override_settings(TIME_ZONE="America/Toronto")
    def test_get_pass_fail_html(self):
        rep = qc.QCSummaryReport()
        rep.report_format = "html"
        tli = utils.create_test_list_instance()
        pf = rep.get_pass_fail_status(tli)
        assert "<span" in pf

    @override_settings(TIME_ZONE="America/Toronto")
    def test_get_pass_fail_plain(self):
        rep = qc.QCSummaryReport()
        rep.report_format = "csv"
        tli = utils.create_test_list_instance()
        pf = rep.get_pass_fail_status(tli)
        assert pf == ''  # no test instances, just want to make sure no html tags in status for plain text report

    def test_get_tlis_for_site(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        utc = utils.create_unit_test_collection(unit=unit)
        tli = utils.create_test_list_instance(unit_test_collection=utc)

        unit2 = utils.create_unit(site=None)
        utc2 = utils.create_unit_test_collection(unit=unit2)
        utils.create_test_list_instance(unit_test_collection=utc2)

        qs = TestListInstance.objects.all()
        tlis = qc.QCSummaryReport().get_tlis_for_site(qs, site)
        assert list([x.pk for x in tlis]) == [tli.pk]

    def test_get_tlis_for_null_site(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        utc = utils.create_unit_test_collection(unit=unit)
        utils.create_test_list_instance(unit_test_collection=utc)

        unit2 = utils.create_unit(site=None)
        utc2 = utils.create_unit_test_collection(unit=unit2)
        tli2 = utils.create_test_list_instance(unit_test_collection=utc2)

        qs = TestListInstance.objects.all()
        tlis = qc.QCSummaryReport().get_tlis_for_site(qs, None)
        assert list([x.pk for x in tlis]) == [tli2.pk]

    def test_to_table(self):

        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        utc = utils.create_unit_test_collection(unit=unit)
        utils.create_test_list_instance(unit_test_collection=utc)

        unit2 = utils.create_unit(site=None)
        utc2 = utils.create_unit_test_collection(unit=unit2)
        utils.create_test_list_instance(unit_test_collection=utc2)

        rep = qc.QCSummaryReport()
        rep.report_format = "csv"
        context = rep.get_context()
        table = rep.to_table(context)

        header_row = table.index([
            'Site',
            'Unit',
            'Test list',
            'Due Date',
            'Work Completed',
            'Pass/Fail Status',
            'Link',
        ])
        # should be two tlis after header
        assert len(table[header_row + 1:]) == 2


class TestUTCReport(TestCase):

    def test_filter_form_valid(self):
        """If queryset.count() > MAX_TLIS then filter_form should get an error added"""
        rep = qc.UTCReport()
        rep.MAX_TLIS = -1
        ff = rep.get_filter_form()
        resp = rep.filter_form_valid(ff)
        assert resp is False
        assert '__all__' in ff.errors and "Please reduce" in ff.errors['__all__'][0]

    def test_get_queryset(self):
        assert qc.UTCReport().get_queryset().model._meta.model_name == "testlistinstance"

    def test_get_filename(self):
        fname = qc.UTCReport().get_filename('pdf')
        assert fname == 'test-list-instances.pdf'

    def test_get_unit_test_collection_details(self):
        utc = utils.create_unit_test_collection()
        det = qc.UTCReport().get_unit_test_collection_details([utc.pk])
        assert det == ('Unit / Test List', '%s - %s' % (utc.unit.name, utc.name))

    def test_generate_html(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        utc = utils.create_unit_test_collection(unit=unit)
        utils.create_test_list_instance(unit_test_collection=utc)

        unit2 = utils.create_unit(site=None)
        utc2 = utils.create_unit_test_collection(unit=unit2)
        tli2 = utils.create_test_list_instance(unit_test_collection=utc2)
        comment = Comment(
            submit_date=timezone.now(),
            user=tli2.created_by,
            content_object=tli2,
            comment='test comment',
            site=Site.objects.latest("pk"),
        )
        comment.save()

        rep = qc.UTCReport(report_opts={'unit_test_collection': [utc.pk]})
        rep.report_format = "pdf"
        rep.to_html()

    def test_to_table(self):

        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        utc = utils.create_unit_test_collection(unit=unit)
        tli = utils.create_test_list_instance(unit_test_collection=utc)
        # make this tli autoreviewed
        tli.all_reviewed = True
        tli.reviewed_by = None
        tli.save()

        unit2 = utils.create_unit(site=None)
        utc2 = utils.create_unit_test_collection(unit=unit2)
        tli2 = utils.create_test_list_instance(unit_test_collection=utc2)

        # give tli2 some history
        tli3 = utils.create_test_list_instance(
            unit_test_collection=utc2,
            work_completed=tli2.work_completed - timezone.timedelta(days=2),
        )
        ti = utils.create_test_instance(test_list_instance=tli3)

        # tli comment
        comment = Comment(
            submit_date=timezone.now(),
            user=tli2.created_by,
            content_object=tli2,
            comment='test comment',
            site=Site.objects.latest("pk"),
        )
        comment.save()

        attachment = Attachment(
            attachment=ContentFile("content", "content.pdf"),
            created_by=tli.created_by,
            testlistinstance=tli2,
        )
        attachment.save()

        attachment = Attachment(
            attachment=ContentFile("content", "content.pdf"),
            created_by=tli.created_by,
            testinstance=ti,
        )
        attachment.save()

        rep = qc.UTCReport(report_opts={'unit_test_collection': [utc.pk, utc2.pk]})
        rep.report_format = "csv"
        context = rep.get_context()
        table = rep.to_table(context)

        ntlis = table.count([
            _('Test'),
            _('Value'),
            _('Reference'),
            _('Tolerance'),
            _('Pass/Fail'),
            _('Review Status'),
            _('Comment'),
            _('Attachments'),
        ])

        # should be three tlis
        assert ntlis == 3


class TestTestDataReport(TestCase):

    def test_filter_form_valid(self):
        """If queryset.count() > MAX_TLIS then filter_form should get an error added"""
        rep = qc.TestDataReport()
        rep.MAX_TIS = -1
        ff = rep.get_filter_form()
        resp = rep.filter_form_valid(ff)
        assert resp is False
        assert '__all__' in ff.errors and "Please reduce" in ff.errors['__all__'][0]

    def test_get_queryset(self):
        assert qc.TestDataReport().get_queryset().model._meta.model_name == "testinstance"

    def test_get_filename(self):
        assert qc.TestDataReport().get_filename('pdf') == 'test-instance-values.pdf'

    def test_get_unit_test_info__test_details(self):
        test = utils.create_test()
        tests = qc.TestDataReport().get_unit_test_info__test_details([test.pk])
        assert tests == ('Test', test.name)

    def test_get_organization_details(self):
        org = qc.TestDataReport().get_organization_details('one_per_row')
        assert org == ('Organization', 'One Test Instance Per Row')

    def test_generate_html_group_by_unit_test_date(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        utc = utils.create_unit_test_collection(unit=unit)
        tli = utils.create_test_list_instance(unit_test_collection=utc)
        ti = utils.create_test_instance(test_list_instance=tli)

        rep = qc.TestDataReport(
            report_opts={
                'unit_test_info__test': [ti.unit_test_info.test.pk],
                'organization': 'group_by_unit_test_date'
            }
        )
        rep.report_format = "pdf"
        assert 'not supported for' in rep.to_html()

    def test_generate_html_one_per_row(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        utc = utils.create_unit_test_collection(unit=unit)
        tli = utils.create_test_list_instance(unit_test_collection=utc)
        ti = utils.create_test_instance(test_list_instance=tli)

        rep = qc.TestDataReport(
            report_opts={
                'unit_test_info__test': [ti.unit_test_info.test.pk],
                'organization': 'one_per_row'
            }
        )
        rep.report_format = "pdf"
        rep.to_html()

    def test_to_table_one_per_row_csv(self):

        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        utc = utils.create_unit_test_collection(unit=unit)
        tli = utils.create_test_list_instance(unit_test_collection=utc)
        ti = utils.create_test_instance(test_list_instance=tli)
        utils.create_test_instance(
            test_list_instance=tli,
            unit_test_info=ti.unit_test_info,
            work_completed=tli.work_completed - timezone.timedelta(days=1),
        )

        rep = qc.TestDataReport(
            report_opts={
                'unit_test_info__test': [ti.unit_test_info.test.pk],
                'organization': 'one_per_row'
            }
        )
        rep.report_format = "csv"
        context = rep.get_context()
        table = rep.to_table(context)
        header_row = table.index([
            _("Work Completed"),
            _("Test"),
            _("Unit"),
            _("Site"),
            _("Value"),
            _("Reference"),
            _("Tolerance"),
            _("Skipped"),
            _("Performed By"),
            _("Comment"),
        ])
        # should be two tis after header
        assert len(table[header_row + 1:]) == 2

    def test_to_table_group_by_unit_test_date_csv(self):

        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        utc = utils.create_unit_test_collection(unit=unit)
        tli = utils.create_test_list_instance(unit_test_collection=utc)
        ti = utils.create_test_instance(test_list_instance=tli)
        utils.create_test_instance(
            test_list_instance=tli,
            unit_test_info=ti.unit_test_info,
            work_completed=tli.work_completed - timezone.timedelta(days=1),
        )
        ti3 = utils.create_test_instance(
            test_list_instance=tli,
            work_completed=tli.work_completed - timezone.timedelta(days=1),
        )

        rep = qc.TestDataReport(
            report_opts={
                'unit_test_info__test': [ti.unit_test_info.test.pk, ti3.unit_test_info.test.pk],
                'organization': 'group_by_unit_test_date'
            }
        )
        rep.report_format = "csv"
        context = rep.get_context()
        table = rep.to_table(context)
        org_row = table.index(['Organization:', 'Group by Unit/Test/Date'])

        # should be two rows after blank row
        assert len(table[org_row + 2:]) == 2
        # and 11 columns
        assert len(table[org_row + 3]) == 11


class TestDueDateReport(TestCase):

    def test_get_queryset(self):
        assert qc.NextDueDatesReport().get_queryset().model._meta.model_name == "unittestcollection"

    def test_next_due_dates_get_filename(self):
        assert qc.NextDueDatesReport().get_filename('pdf') == 'next-due-dates-for-qc.pdf'

    def test_next_due_and_overdue_filename(self):
        assert qc.DueAndOverdueQCReport().get_filename('pdf') == 'due-and-overdue-qc.pdf'

    def test_get_unit__site_details(self):
        site = USite.objects.create(name="site")
        sites = qc.NextDueDatesReport().get_unit__site_details([site, 'null'])
        assert sites == ('Site(s)', 'site, Other')

    def test_get_unit_details(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        units = qc.NextDueDatesReport().get_unit_details([unit.pk])
        assert units == ('Unit(s)', '%s - %s' % (unit.site.name, unit.name))

    def test_generate_next_due_dates_html(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        utc = utils.create_unit_test_collection(unit=unit)
        tli = utils.create_test_list_instance(unit_test_collection=utc)
        utils.create_test_instance(test_list_instance=tli)

        rep = qc.NextDueDatesReport()
        rep.report_format = "pdf"
        rep.to_html()

    def test_generate_due_and_overdue_html(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        utc = utils.create_unit_test_collection(unit=unit)
        tli = utils.create_test_list_instance(unit_test_collection=utc)
        utils.create_test_instance(test_list_instance=tli)

        rep = qc.DueAndOverdueQCReport()
        rep.report_format = "pdf"
        rep.to_html()

    def test_to_table(self):

        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        utc = utils.create_unit_test_collection(unit=unit)
        utils.create_test_list_instance(unit_test_collection=utc)

        unit2 = utils.create_unit(site=None)
        utc2 = utils.create_unit_test_collection(unit=unit2)
        utils.create_test_list_instance(unit_test_collection=utc2)

        rep = qc.NextDueDatesReport()
        rep.report_format = "csv"
        context = rep.get_context()
        table = rep.to_table(context)

        header_count = table.count([
            _("Unit"),
            _("Name"),
            _("Frequency"),
            _("Due Date"),
            _("Window"),
            _("Assinged To"),
            _("Perform")
        ])
        assert header_count == 2
