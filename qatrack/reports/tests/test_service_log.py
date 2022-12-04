from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone
from django.utils.translation import gettext as _

from qatrack.attachments.models import Attachment
from qatrack.parts import models as parts_models
from qatrack.qa.tests import utils
from qatrack.reports import service_log as sl
from qatrack.service_log import models
from qatrack.service_log.tests import utils as sl_utils
from qatrack.units.models import Site as USite
from qatrack.units.tests import utils as u_utils


class TestServiceEventSummaryReport(TestCase):

    def test_filter_form_valid(self):
        """If queryset.count() > MAX_TLIS then filter_form should get an error added"""
        rep = sl.ServiceEventSummaryReport()
        rep.MAX_SES = -1
        ff = rep.get_filter_form()
        resp = rep.filter_form_valid(ff)
        assert resp is False
        assert '__all__' in ff.errors and "Please reduce" in ff.errors['__all__'][0]

    def test_get_queryset(self):
        assert sl.ServiceEventSummaryReport().get_queryset().model._meta.model_name == "serviceevent"

    def test_get_filename(self):
        assert sl.ServiceEventSummaryReport().get_filename('pdf') == 'service-event-summary.pdf'

    def test_get_include_description_details(self):
        details = sl.ServiceEventSummaryReport().get_include_description_details(False)
        assert details == (_("Include Description"), _("No"))

    def test_get_unit_service_area__unit_details(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        units = sl.ServiceEventSummaryReport().get_unit_service_area__unit_details([unit.pk])
        assert units == ('Unit(s)', '%s - %s' % (unit.site.name, unit.name))

    def test_get_unit_service_area__unit__site_details(self):
        site = USite.objects.create(name="site")
        sites = sl.ServiceEventSummaryReport().get_unit_service_area__unit__site_details([site, 'null'])
        assert sites == ('Site(s)', 'site, Other')

    def test_get_ses_for_site(self):
        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        usa1 = sl_utils.create_unit_service_area(unit=unit1)
        se1 = sl_utils.create_service_event(unit_service_area=usa1)

        unit2 = utils.create_unit(site=None)
        usa2 = sl_utils.create_unit_service_area(unit=unit2)
        sl_utils.create_service_event(unit_service_area=usa2)

        qs = models.ServiceEvent.objects.all()
        ses = sl.ServiceEventSummaryReport().get_ses_for_site(qs, site)
        assert [x.pk for x in ses] == [se1.pk]

    def test_get_ses_for_null_site(self):
        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        usa1 = sl_utils.create_unit_service_area(unit=unit1)
        sl_utils.create_service_event(unit_service_area=usa1)

        unit2 = utils.create_unit(site=None)
        usa2 = sl_utils.create_unit_service_area(unit=unit2)
        se2 = sl_utils.create_service_event(unit_service_area=usa2)

        qs = models.ServiceEvent.objects.all()
        ses = sl.ServiceEventSummaryReport().get_ses_for_site(qs, None)
        assert [x.pk for x in ses] == [se2.pk]

    def test_generate_html(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        usa1 = sl_utils.create_unit_service_area(unit=unit1)
        sl_utils.create_service_event(unit_service_area=usa1)

        unit2 = utils.create_unit()
        usa2 = sl_utils.create_unit_service_area(unit=unit2)
        sl_utils.create_service_event(unit_service_area=usa2)

        rep = sl.ServiceEventSummaryReport()
        rep.report_format = "pdf"
        rep.to_html()

    def test_to_table(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        usa1 = sl_utils.create_unit_service_area(unit=unit1)
        sl_utils.create_service_event(unit_service_area=usa1)

        unit2 = utils.create_unit()
        usa2 = sl_utils.create_unit_service_area(unit=unit2)
        sl_utils.create_service_event(unit_service_area=usa2)

        rep = sl.ServiceEventSummaryReport(report_opts={'include_description': True})
        rep.report_format = "csv"
        context = rep.get_context()
        table = rep.to_table(context)

        header_row = table.index([
            _("Service Event ID"),
            _("Service Date"),
            _("Site"),
            _("Unit"),
            _("Service Area"),
            _("Service Type"),
            _("Status"),
            _("Service Time"),
            _("Lost Time"),
            _("Problem Description"),
            _("Work Description"),
            _("Link"),
        ])
        # should be two ses after header
        assert len(table[header_row + 1:]) == 2


class TestServiceEventDetailsReport(TestCase):

    def test_get_filename(self):
        assert sl.ServiceEventDetailsReport().get_filename('pdf') == 'service-event-details.pdf'

    def test_generate_html(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        usa1 = sl_utils.create_unit_service_area(unit=unit1)
        sl_utils.create_service_event(unit_service_area=usa1)

        unit2 = utils.create_unit()
        usa2 = sl_utils.create_unit_service_area(unit=unit2)
        sl_utils.create_service_event(unit_service_area=usa2)

        rep = sl.ServiceEventDetailsReport()
        rep.report_format = "pdf"
        rep.to_html()

    def test_to_table(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        usa1 = sl_utils.create_unit_service_area(unit=unit1)
        sl_utils.create_service_event(unit_service_area=usa1)

        unit2 = utils.create_unit()
        usa2 = sl_utils.create_unit_service_area(unit=unit2)
        se = sl_utils.create_service_event(unit_service_area=usa2)
        se2 = sl_utils.create_service_event(unit_service_area=usa2)
        se.service_event_related.add(se2)

        sl_utils.create_hours(service_event=se)
        sl_utils.create_return_to_service_qa(service_event=se)
        sl_utils.create_group_linker_instance(service_event=se)
        part = sl_utils.create_part()

        parts_models.PartUsed.objects.create(service_event=se, part=part, quantity=1)

        attachment = Attachment(
            attachment=ContentFile("content", "content.pdf"),
            created_by=se.user_created_by,
            serviceevent=se,
        )
        attachment.save()

        rep = sl.ServiceEventDetailsReport(report_opts={'include_description': True})
        rep.report_format = "csv"
        context = rep.get_context()
        table = rep.to_table(context)

        header_row = table.index([
            _("Service Event ID"),
            _("Service Date"),
            _("Site"),
            _("Unit"),
            _("Service Area"),
            _("Service Type"),
            _("Service Time"),
            _("Lost Time"),
            _("Status"),
            _("Created By"),
            _("Created Date"),
            _("Modified By"),
            _("Modified Date"),
            _("Problem Description"),
            _("Work Description"),
            _("Safety Precautions"),
            _("Initiated By"),
            _("Related Service Events"),
            _("Group Members Involved"),
            _("Work Durations"),
            _("Return To Service QC"),
            _("Return To Service Comments"),
            _("Parts Used"),
            _("Attachments"),
            _("Link"),
        ])
        # should be three ses after header
        assert len(table[header_row + 1:]) == 3


class TestServiceEventPersonnelSummaryReport(TestCase):

    def test_get_filename(self):
        assert sl.ServiceEventPersonnelSummaryReport().get_filename('pdf') == 'service-event-personnel-summary.pdf'

    def test_generate_html(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        usa1 = sl_utils.create_unit_service_area(unit=unit1)
        sl_utils.create_service_event(unit_service_area=usa1)

        unit2 = utils.create_unit()
        usa2 = sl_utils.create_unit_service_area(unit=unit2)
        sl_utils.create_service_event(unit_service_area=usa2)

        rep = sl.ServiceEventPersonnelSummaryReport()
        rep.report_format = "pdf"
        rep.to_html()

    def test_to_table(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        usa1 = sl_utils.create_unit_service_area(unit=unit1)
        sl_utils.create_service_event(unit_service_area=usa1)

        unit2 = utils.create_unit()
        usa2 = sl_utils.create_unit_service_area(unit=unit2)
        se = sl_utils.create_service_event(unit_service_area=usa2)
        se2 = sl_utils.create_service_event(unit_service_area=usa2)
        se.service_event_related.add(se2)

        sl_utils.create_hours(service_event=se)
        tp = sl_utils.create_third_party()
        sl_utils.create_hours(service_event=se, third_party=tp)
        sl_utils.create_group_linker_instance(service_event=se)
        part = sl_utils.create_part()

        parts_models.PartUsed.objects.create(service_event=se, part=part, quantity=1)

        attachment = Attachment(
            attachment=ContentFile("content", "content.pdf"),
            created_by=se.user_created_by,
            serviceevent=se,
        )
        attachment.save()

        rep = sl.ServiceEventPersonnelSummaryReport()
        rep.report_format = "xlsx"
        context = rep.get_context()
        rep.to_table(context)

    def test_format(self):
        assert sl.ServiceEventPersonnelSummaryReport().format_user("foo", "bar", "baz") == "foo (baz, bar)"

    def test_format_no_fname(self):
        assert sl.ServiceEventPersonnelSummaryReport().format_user("foo", "", "baz") == "foo (baz)"


class TestServiceTimesReport(TestCase):

    def test_get_filename(self):
        assert sl.ServiceTimesReport().get_filename('pdf') == 'service-times.pdf'

    def test_generate_html(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        usa1 = sl_utils.create_unit_service_area(unit=unit1)
        sl_utils.create_service_event(
            unit_service_area=usa1,
            service_time=timezone.timedelta(hours=1, minutes=23),
            lost_time=timezone.timedelta(hours=1, minutes=23),
        )

        unit2 = utils.create_unit()
        usa2 = sl_utils.create_unit_service_area(unit=unit2)
        sl_utils.create_service_event(unit_service_area=usa2)

        rep = sl.ServiceTimesReport()
        rep.report_format = "pdf"
        rep.to_html()

    def test_to_table(self):

        site = USite.objects.create(name="site")
        unit1 = utils.create_unit(site=site)
        usa1 = sl_utils.create_unit_service_area(unit=unit1)
        sl_utils.create_service_event(
            unit_service_area=usa1,
            service_time=timezone.timedelta(hours=1, minutes=23),
            lost_time=timezone.timedelta(hours=1, minutes=23),
        )

        unit2 = utils.create_unit()
        usa2 = sl_utils.create_unit_service_area(unit=unit2)
        sl_utils.create_service_event(unit_service_area=usa2)

        rep = sl.ServiceTimesReport()
        rep.report_format = "xlsx"
        context = rep.get_context()
        rep.to_table(context)


class TestDueDateReport(TestCase):

    def test_get_queryset(self):
        assert (
            sl.NextScheduledServiceEventsDueDatesReport().get_queryset().model._meta.model_name ==
            "serviceeventschedule"
        )

    def test_next_due_dates_get_filename(self):
        assert (
            sl.NextScheduledServiceEventsDueDatesReport().get_filename('pdf') ==
            'next-due-dates-for-scheduled-service-events.pdf'
        )

    def test_next_due_and_overdue_filename(self):
        assert (
            sl.DueAndOverdueServiceEventScheduleReport().get_filename('pdf') ==
            'due-and-overdue-scheduled-service-events.pdf'
        )

    def test_get_unit__site_details(self):
        site = USite.objects.create(name="site")
        sites = sl.NextScheduledServiceEventsDueDatesReport().get_unit_service_area__unit__site_details([site, 'null'])
        assert sites == ('Site(s)', 'site, Other')

    def test_get_unit_details(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        units = sl.NextScheduledServiceEventsDueDatesReport().get_unit_service_area__unit_details([unit.pk])
        assert units == ('Unit(s)', '%s - %s' % (unit.site.name, unit.name))

    def test_generate_next_due_dates_html(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        usa = sl_utils.create_unit_service_area(unit=unit)
        sch = sl_utils.create_service_event_schedule(unit_service_area=usa)
        sch.due_date = timezone.now() + timezone.timedelta(days=1)
        sch.save()
        rep = sl.NextScheduledServiceEventsDueDatesReport()
        rep.report_format = "pdf"
        rep.to_html()

    def test_generate_due_and_overdue_html(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        usa = sl_utils.create_unit_service_area(unit=unit)
        sch = sl_utils.create_service_event_schedule(unit_service_area=usa)
        sch.due_date = timezone.now() - timezone.timedelta(days=1)
        sch.save()

        rep = sl.DueAndOverdueServiceEventScheduleReport()
        rep.report_format = "pdf"
        rep.to_html()

    def test_to_table(self):

        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        usa = sl_utils.create_unit_service_area(unit=unit)
        sch1 = sl_utils.create_service_event_schedule(unit_service_area=usa)
        sch1.due_date = timezone.now() - timezone.timedelta(days=1)
        sch1.save()

        unit2 = utils.create_unit(site=None)
        usa2 = sl_utils.create_unit_service_area(unit=unit2)
        sl_utils.create_service_event_schedule(unit_service_area=usa2)

        rep = sl.NextScheduledServiceEventsDueDatesReport()
        rep.report_format = "csv"
        context = rep.get_context()
        table = rep.to_table(context)

        header_count = table.count([
            _("Unit"),
            _("Service Area"),
            _("Template Name"),
            _("Frequency"),
            _("Due Date"),
            _("Window"),
            _("Assigned To"),
            _("Perform")
        ])
        assert header_count == 2

    def test_generate_next_due_dates_active_filter_true(self):
        """If a unit is inactive, it should not be included in filterset when active is True"""
        site = USite.objects.create(name="site")
        unit = u_utils.create_unit(site=site)
        unit.active = False
        unit.save()
        usa = sl_utils.create_unit_service_area(unit=unit)
        sch = sl_utils.create_service_event_schedule(unit_service_area=usa)
        sch.due_date = timezone.now() + timezone.timedelta(days=1)
        sch.save()
        for ReportType in [sl.NextScheduledServiceEventsDueDatesReport, sl.DueAndOverdueServiceEventScheduleReport]:
            rep = ReportType(report_opts={'active': True})
            assert rep.filter_set.qs.count() == 0

    def test_generate_next_due_dates_active_filter_false(self):
        """If a unit is active, it should not be included in filterset when active is False"""
        site = USite.objects.create(name="site")
        unit = u_utils.create_unit(site=site)
        usa = sl_utils.create_unit_service_area(unit=unit)
        sch = sl_utils.create_service_event_schedule(unit_service_area=usa)
        sch.due_date = timezone.now() + timezone.timedelta(days=1)
        sch.save()
        for ReportType in [sl.NextScheduledServiceEventsDueDatesReport, sl.DueAndOverdueServiceEventScheduleReport]:
            rep = sl.NextScheduledServiceEventsDueDatesReport(report_opts={'active': False})
            assert rep.filter_set.qs.count() == 0


class TestAssignedTemplatesReport(TestCase):

    def test_get_queryset(self):
        assert sl.ScheduledTemplatesReport().get_queryset().model._meta.model_name == "serviceeventschedule"

    def test_get_filename(self):
        assert sl.ScheduledTemplatesReport().get_filename('pdf') == 'scheduled-service-event-assignment-summary.pdf'

    def test_get_unit_service_area__unit__site_details(self):
        site = USite.objects.create(name="site")
        sites = sl.ScheduledTemplatesReport().get_unit_service_area__unit__site_details([site, 'null'])
        assert sites == ('Site(s)', 'site, Other')

    def test_get_unit_service_area__unit_details(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        units = sl.ScheduledTemplatesReport().get_unit_service_area__unit_details([unit.pk])
        assert units == ('Unit(s)', '%s - %s' % (unit.site.name, unit.name))

    def test_generate_summary_html(self):
        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        usa = sl_utils.create_unit_service_area(unit=unit)
        sl_utils.create_service_event_schedule(unit_service_area=usa)
        rep = sl.ScheduledTemplatesReport()
        rep.report_format = "pdf"
        rep.to_html()

    def test_to_table(self):

        site = USite.objects.create(name="site")
        unit = utils.create_unit(site=site)
        usa = sl_utils.create_unit_service_area(unit=unit)
        sl_utils.create_service_event_schedule(unit_service_area=usa)

        usa2 = sl_utils.create_unit_service_area()
        sl_utils.create_service_event_schedule(unit_service_area=usa2)

        rep = sl.ScheduledTemplatesReport(report_opts={'active': True})
        rep.report_format = "csv"
        context = rep.get_context()
        table = rep.to_table(context)

        header_row = table.index([
            _("Site"),
            _("Unit"),
            _("Service Area"),
            _("Template Name"),
            _("Frequency"),
            _("Assigned To"),
            _("Link"),
        ])
        assert len(table[header_row + 1:]) == 2
