from django.db.models import Count, Sum
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qa.templatetags.qa_tags import hour_min
from qatrack.reports import filters
from qatrack.reports.reports import BaseReport
from qatrack.service_log import models
from qatrack.units import models as umodels


class ServiceEventPersonnelSummaryReport(BaseReport):

    report_type = "service-log-personnel-summary"
    name = _l("Service Event Personnel Summary")
    filter_class = filters.ServiceEventDetailsFilter
    description = mark_safe(
        _l(
            "This report summarizes the involvement of personnel in Service Events "
            "for the selected time period, sites, units, frequencies, and groups."
        )
    )

    category = _l("Service Log")

    template = "reports/service_log/personnel.html"

    def get_queryset(self):
        return models.ServiceEvent.objects.all()

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "service-event-personnel-summary"), report_format)

    def get_unit_service_area__unit_details(self, val):
        units = umodels.Unit.objects.filter(pk__in=val).select_related("site")
        return (
            "Unit(s)", ', '.join("%s%s" % ("%s - " % unit.site.name if unit.site else "", unit.name) for unit in units)
        )

    def get_unit_service_area__unit__site_details(self, sites):
        return ("Site(s)", (', '.join(s.name if s != 'null' else _("Other") for s in sites)).strip(", "))

    def get_context(self):

        context = super().get_context()

        context['group_linkers'] = self.collect_group_linker_instances()

        user_hours, tp_hours = self.collect_hours()
        context['user_hours'] = user_hours
        context['tp_hours'] = tp_hours

        context['num_group_linkers'] = models.GroupLinker.objects.count()

        return context

    def format_user(self, username, first_name, last_name):

        if first_name or last_name:
            return "%s (%s)" % (username, ", ".join(x for x in [last_name, first_name] if x))

        return username

    def collect_group_linker_instances(self):

        group_linker_instances = models.GroupLinkerInstance.objects.filter(
            service_event__in=self.filter_set.qs,
        ).select_related(
            "user",
            "group_linker",
        )

        gli_users = models.GroupLinkerInstance.objects.values_list(
            "user",
            "user__username",
            "user__first_name",
            "user__last_name",
        ).order_by("user__username").distinct()

        user_counts = []
        for user_id, uname, fname, lname in gli_users:
            user_glis = list(group_linker_instances.filter(user=user_id))

            group_linkers = models.GroupLinker.objects.filter(
                group__user=user_id,
            ).select_related("group").order_by("name")

            se_gli_counts = {gl.name: 0 for gl in group_linkers}
            for ugli in user_glis:
                try:
                    se_gli_counts[ugli.group_linker.name] += 1
                except KeyError:
                    # handle case where user is no longer part of group
                    se_gli_counts[ugli.group_linker.name] = 1

            u = self.format_user(uname, fname, lname)
            user_counts.append((u, len(se_gli_counts), sorted(se_gli_counts.items())))

        return user_counts

    def collect_hours(self):

        hours = models.Hours.objects.filter(service_event__in=self.filter_set.qs)

        user_hours = hours.exclude(user=None).values(
            "user__username",
            "user__first_name",
            "user__last_name",
        ).annotate(
            total_hours=Sum('time'),
            total_ses=Count('service_event'),
        )
        user_hours_f = []
        for uh in user_hours:
            user_hours_f.append((
                self.format_user(uh['user__username'], uh['user__first_name'], uh['user__last_name']),
                uh['total_ses'],
                uh['total_hours'],
            ))

        tp_hours = hours.exclude(third_party=None).values(
            "third_party__first_name",
            "third_party__last_name",
            "third_party__vendor__name",
        ).order_by(
            "third_party__vendor__name",
            "third_party__last_name",
            "third_party__first_name",
        ).annotate(
            total_hours=Sum('time'),
            total_ses=Count('service_event'),
        )

        return user_hours_f, tp_hours

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        rows.append([_("Group Members Involved Summary")])
        rows.append([_("User"), _("Linked Group Name"), _("# of Service Events")])
        for user, num_rows, linker_counts in context['group_linkers']:
            for group, count in linker_counts:
                rows.append([user, group, count])

        rows.append([])
        rows.append([_("QATrack+ User Hours Summary")])
        rows.append([_("User"), _("Total Time (HH:MM)"), _("# of Service Events")])
        for user, total_ses, total_hours in context['user_hours']:
            rows.append([user, hour_min(total_hours), total_ses])

        rows.append([])
        rows.append([_("Third Party Hours Summary")])
        rows.append([_("Name"), _("Vendor"), _("Total Time (HH:MM)"), _("# of Service Events")])
        for tp in context['tp_hours']:
            rows.append([
                ', '.join(x for x in [tp['third_party__last_name'], tp['third_party__first_name']] if x),
                tp['third_party__vendor__name'],
                hour_min(tp['total_hours']),
                tp['total_ses'],
            ])

        return rows
