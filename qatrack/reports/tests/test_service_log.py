from django.test import TestCase
from django.utils.translation import gettext as _

from qatrack.qa.tests import utils
from qatrack.reports import service_log as sl
from qatrack.service_log import models
from qatrack.service_log.tests import utils as sl_utils
from qatrack.units.models import Site as USite


class TestServiceEventSummaryReport(TestCase):

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
            _("Service Date"),
            _("Site"),
            _("Unit"),
            _("Service Area"),
            _("Status"),
            _("Service Time"),
            _("Lost Time"),
            _("Problem Description"),
            _("Work Description"),
            _("Link"),
        ])
        # should be two ses after header
        assert len(table[header_row + 1:]) == 2
