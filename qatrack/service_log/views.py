
from listable.views import (
    BaseListableView, DATE_RANGE, SELECT_MULTI, NONEORNULL,
    TODAY, YESTERDAY, TOMORROW, LAST_WEEK, THIS_WEEK, NEXT_WEEK, LAST_14_DAYS, THIS_MONTH, THIS_YEAR
)

from qatrack.service_log import models



class TestListInstances(BaseListableView):
    """
    This view provides a base for any sort of listing of
    :model:`service_log.ServiceEvent`'s.
    """

    model = models.ServiceEvent
    paginate_by = 50

    order_by = ["unit_test_collection__unit__name", "-work_completed"]

    fields = (
        "actions",
        "unit_test_collection__unit__name",
        "unit_test_collection__frequency__name",
        "test_list__name",
        "work_completed",
        "created_by__username",
        "review_status",
        "pass_fail",
    )

    headers = {
        "unit_test_collection__unit__name": _("Unit"),
        "unit_test_collection__frequency__name": _("Frequency"),
        "created_by__username": _("Created By"),
    }

    widgets = {
        "unit_test_collection__frequency__name": SELECT_MULTI,
        "unit_test_collection__unit__name": SELECT_MULTI,
        "created_by__username": SELECT_MULTI,
        "work_completed": DATE_RANGE
    }

    date_ranges = {
        "work_completed": [TODAY, YESTERDAY, THIS_WEEK, LAST_14_DAYS, THIS_MONTH, THIS_YEAR]
    }

    search_fields = {
        "actions": False,
        "pass_fail": False,
        "review_status": False,
    }

    order_fields = {
        "actions": False,
        "unit_test_collection__unit__name": "unit_test_collection__unit__number",
        "unit_test_collection__frequency__name": "unit_test_collection__frequency__due_interval",
        "review_status": False,
        "pass_fail": False,
    }

    select_related = (
        "test_list__name",
        # "testinstance_set__status",
        "unit_test_collection__unit__name",
        "unit_test_collection__frequency__due_interval",
        "created_by", "modified_by", "reviewed_by",
    )

    prefetch_related = ("testinstance_set", "testinstance_set__status")

    def __init__(self, *args, **kwargs):
        super(TestListInstances, self).__init__(*args, **kwargs)

        self.templates = {
            'actions': get_template("qa/testlistinstance_actions.html"),
            'work_completed': get_template("qa/testlistinstance_work_completed.html"),
            'review_status': get_template("qa/testlistinstance_review_status.html"),
            'pass_fail': get_template("qa/pass_fail_status.html"),
        }

    def get_icon(self):
        return 'fa-question-circle'

    def get_page_title(self):
        return "All Test Collections"

    def get_context_data(self, *args, **kwargs):
        context = super(TestListInstances, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        context["page_title"] = self.get_page_title()
        return context

    def get_filters(self, field, queryset=None):

        filters = super(TestListInstances, self).get_filters(field, queryset=queryset)

        if field == 'unit_test_collection__frequency__name':
            filters = [(NONEORNULL, 'Ad Hoc') if f == (NONEORNULL, 'None') else f for f in filters]

        return filters

    def unit_test_collection__frequency__name(self, tli):
        freq = tli.unit_test_collection.frequency
        return freq.name if freq else "Ad Hoc"

    def actions(self, tli):
        template = self.templates['actions']
        c = Context({"instance": tli, "perms": PermWrapper(self.request.user), "request": self.request})
        return template.render(c)

    def work_completed(self, tli):
        template = self.templates['work_completed']
        c = Context({"instance": tli})
        return template.render(c)

    def review_status(self, tli):
        template = self.templates['review_status']
        c = Context({"instance": tli, "perms": PermWrapper(self.request.user), "request": self.request})
        c.update(generate_review_status_context(tli))
        return template.render(c)

    def pass_fail(self, tli):
        template = self.templates['pass_fail']
        c = Context({"instance": tli, "exclude": [models.NO_TOL], "show_label": True, "show_icons": settings.ICON_SETTINGS['SHOW_STATUS_ICONS_LISTING']})
        return template.render(c)