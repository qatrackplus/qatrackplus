from django.contrib.sites.shortcuts import get_current_site
from django.test import TestCase
from django.utils import timezone
from django.utils.translation import gettext as _
from django_comments.models import Comment

from qatrack.faults import models
from qatrack.faults.tests import utils as fault_utils
from qatrack.qa.tests import utils
from qatrack.reports import faults
from qatrack.service_log.tests import utils as sl_utils
from qatrack.units.models import Site as USite


class TestFaultSummaryReport(TestCase):

    def test_filter_form_valid(self):
        """If queryset.count() > MAX_FAULTS then filter_form should get an error added"""
        rep = faults.FaultSummaryReport()
        rep.MAX_FAULTS = -1
        ff = rep.get_filter_form()
        resp = rep.filter_form_valid(ff)
        assert resp is False
        assert '__all__' in ff.errors and "Please reduce" in ff.errors['__all__'][0]

    def test_get_queryset(self):
        assert faults.FaultSummaryReport().get_queryset().model._meta.model_name == "fault"

    def test_get_filename(self):
        assert faults.FaultSummaryReport().get_filename('pdf') == 'fault-summary.pdf'

    def test_get_review_status_details(self):
        details = faults.FaultSummaryReport().get_review_status_details("")
        assert details == (_("Review Status"), "")
        details = faults.FaultSummaryReport().get_review_status_details("unreviewed")
        assert details == (_("Review Status"), _("Unreviewed Only"))
        details = faults.FaultSummaryReport().get_review_status_details("reviewed")
        assert details == (_("Review Status"), _("Reviewed Only"))

    def test_get_unit_details(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        units = faults.FaultSummaryReport().get_unit_details([unit.pk])
        assert units == ('Unit(s)', '%s - %s' % (unit.site.name, unit.name))

    def test_get_unit__site_details(self):
        site = USite.objects.create(name="site")
        sites = faults.FaultSummaryReport().get_unit__site_details([site, 'null'])
        assert sites == ('Site(s)', 'site, Other')

    def test_get_faults_for_site(self):
        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        fault1 = fault_utils.create_fault(unit=unit1)

        unit2 = utils.create_unit(site=None)
        fault_utils.create_fault(unit=unit2)

        qs = models.Fault.objects.all()
        fs = faults.FaultSummaryReport().get_faults_for_site(qs, site)
        assert [x.pk for x in fs] == [fault1.pk]

    def test_get_faults_for_null_site(self):
        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        fault_utils.create_fault(unit=unit1)

        unit2 = utils.create_unit(site=None)
        fault2 = fault_utils.create_fault(unit=unit2)

        qs = models.Fault.objects.all()
        fs = faults.FaultSummaryReport().get_faults_for_site(qs, None)
        assert [x.pk for x in fs] == [fault2.pk]

    def test_generate_html(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        fault_utils.create_fault(unit=unit1)

        unit2 = utils.create_unit()
        fault_utils.create_fault(unit=unit2)

        rep = faults.FaultSummaryReport()
        rep.report_format = "pdf"
        rep.to_html()

    def test_to_table_reviewed(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        fault_utils.create_fault(unit=unit1)

        unit2 = utils.create_unit()
        fault2 = fault_utils.create_fault(unit=unit2)
        fault_rev = fault_utils.create_fault_review(fault=fault2)
        comment = Comment(
            submit_date=timezone.now(),
            user=fault_rev.reviewed_by,
            content_object=fault_rev.fault,
            comment="comment",
            site=get_current_site(None)
        )
        comment.save()

        rep = faults.FaultSummaryReport(report_opts={'review_status': "reviewed"})
        rep.report_format = "csv"
        context = rep.get_context()
        table = rep.to_table(context)

        header_row = table.index([
            _("Fault ID"),
            _("Occurred"),
            _("Site"),
            _("Unit"),
            _("Fault Type"),
            _("Modality"),
            _("Link"),
        ])
        # should be one fault after header
        assert len(table[header_row + 1:]) == 1

    def test_unreviewed_filter(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        fault_utils.create_fault(unit=unit1)
        rep = faults.FaultSummaryReport(report_opts={'review_status': "unreviewed"})
        rep.report_format = "csv"
        context = rep.get_context()
        assert len(context['sites_data'][0][1]) == 1


class TestFaultDetailsReport(TestCase):

    def test_get_filename(self):
        assert faults.FaultDetailsReport().get_filename('pdf') == 'fault-details.pdf'

    def test_generate_html(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        fault_utils.create_fault(unit=unit1)

        unit2 = utils.create_unit(site=None)
        fault_utils.create_fault(unit=unit2)

        rep = faults.FaultDetailsReport()
        rep.report_format = "pdf"
        rep.to_html()

    def test_to_table(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        fault_utils.create_fault(unit=unit1)

        unit2 = utils.create_unit()
        fault2 = fault_utils.create_fault(unit=unit2)

        usa2 = sl_utils.create_unit_service_area(unit=unit2)
        sl_utils.create_service_event(unit_service_area=usa2)
        se2 = sl_utils.create_service_event(unit_service_area=usa2)
        fault2.related_service_events.add(se2)

        user = sl_utils.create_user()
        comment = Comment(
            submit_date=timezone.now(),
            user=user,
            content_object=fault2,
            comment="comment",
            site=get_current_site(None)
        )
        comment.save()

        rep = faults.FaultDetailsReport(report_opts={'review_status': 'unreviewed'})
        rep.report_format = "csv"
        context = rep.get_context()
        table = rep.to_table(context)

        header_row = table.index([
            _("Fault ID"),
            _("Occurred"),
            _("Site"),
            _("Unit"),
            _("Fault Type"),
            _("Modality"),
            _("Created By"),
            _("Created Date"),
            _("Modified By"),
            _("Modified Date"),
            _("Reviewed By"),
            _("Reviewed Date"),
            _("Related Service Events"),
            _("Link"),
        ])
        # should be three faults after header
        assert len(table[header_row + 1:]) == 2

    def test_reviewed_filter(self):

        fault_utils.create_fault_review()
        rep = faults.FaultDetailsReport(report_opts={'review_status': "reviewed"})
        rep.report_format = "csv"
        context = rep.get_context()
        assert len(context['sites_data'][0][1]) == 1
