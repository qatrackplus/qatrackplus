from django import template
from django.conf import settings
from django.db.models import Q
from django.template.loader import get_template
from django.utils import timezone
from django.utils.safestring import mark_safe

from qatrack.qa import models
from qatrack.qatrack_core import scheduling
from qatrack.qatrack_core.dates import end_of_day, format_as_date, start_of_day

register = template.Library()


@register.simple_tag
def qa_value_form(form, test_list, perms, user, test_info=None, unit_test_collection=None, show_category=True):
    template = get_template("qa/qavalue_form.html")
    c = {
        "user": user,
        "form": form,
        "perms": perms,
        "test_list": test_list,
        "test_info": test_info,
        'unit_test_collection': unit_test_collection,
        'show_category': show_category,
    }
    return template.render(c)


@register.simple_tag
def qa_table_colspan(perms, offset=0):
    perms_to_check = ['can_view_ref_tol', 'can_view_history']
    span = 6 - offset + sum(1 for p in perms_to_check if perms['qa'][p])
    return "%d" % (span)


@register.simple_tag
def reference_tolerance_span(test, ref, tol):

    if ref is None and not (test.is_mult_choice() or test.is_string_type()):
        return mark_safe("<span>No Ref</span>")

    if test.is_boolean():
        return mark_safe('<span title="Passing value = %s">%s</span>' % (ref.value_display(), ref.value_display()))

    if not tol:
        if ref:
            return mark_safe('<span title="No Tolerance Set">%s</span>' % (ref.value_display()))
        return mark_safe('<span title="No Tolerance Set">No Tol</span>')

    tsd = settings.TEST_STATUS_DISPLAY
    if tol.type == models.MULTIPLE_CHOICE:
        params = (tsd['ok'], ", ".join(tol.pass_choices()), tsd['tolerance'], ', '.join(tol.tol_choices()))
        return mark_safe((
            '<span><abbr title="%s Values: %s;  %s Values: %s; All other choices are failing">'
            '<em>Choice</em></abbr></span>'
        ) % params)

    tsds = settings.TEST_STATUS_DISPLAY_SHORT
    if tol.type == models.ABSOLUTE:
        return mark_safe(
            '<span> <abbr title="(%s L, %s L, %s H, %s H) = %s ">%s</abbr></span>' % (
                tsds["action"], tsds["tolerance"], tsds["tolerance"], tsds["action"], str(tol).replace("Absolute", ""),
                ref.value_display() if ref else ""
            )
        )
    elif tol.type == models.PERCENT:
        return mark_safe(
            '<span> <abbr title="(%s L, %s L, %s H, %s H) = %s ">%s</abbr></span>' % (
                tsds["action"], tsds["tolerance"], tsds["tolerance"], tsds["action"], str(tol).replace("Percent", ""),
                ref.value_display() if ref else ""
            )
        )


@register.simple_tag
def tolerance_for_reference(tol, ref):

    if not ref and tol and tol.type != models.MULTIPLE_CHOICE:
        return ""

    tsd = settings.TEST_STATUS_DISPLAY
    if ref and ref.type == models.BOOLEAN:
        expected = ref.value_display()
        return mark_safe(
            '<span>%s: %s; %s: %s</span>' % (tsd['ok'], expected, tsd['action'], "Yes" if expected == "No" else "No")
        )

    if not tol:
        return mark_safe('<span><em>N/A</em></span>')

    if tol.type == models.MULTIPLE_CHOICE:
        params = (tsd['ok'], ", ".join(tol.pass_choices()), tsd['tolerance'], ', '.join(tol.tol_choices()))
        return mark_safe('<span>%s: %s</br>  %s: %s</br> All others fail</span>' % params)

    tols = tol.tolerances_for_value(ref.value)
    for key in tols:
        tols[key] = "-" if tols[key] is None else "%.4g" % tols[key]
    tols["ok_disp"] = tsd['ok']
    tols["tol_disp"] = tsd['tolerance']
    tols["act_disp"] = tsd['action']
    return mark_safe(
        '<span>%(ok_disp)s: Between %(tol_low)s &amp; %(tol_high)s</br> '
        '%(tol_disp)s Between %(act_low)s &amp; %(act_high)s</br> '
        '%(act_disp)s: < %(act_low)s or > %(act_high)s</span>' % tols
    )


@register.simple_tag
def history_display(history, unit, test_list, test, frequency=None):
    template = get_template("qa/history.html")

    # Set start / end dates of 1 year, or the span of the history elements, whichever is larger
    one_year = timezone.timedelta(days=365)
    end_date = end_of_day(timezone.now())
    start_date = start_of_day(end_date - one_year)
    if history:
        start_date = history[-1][0].work_completed
        end_date = history[0][0].work_completed
        hist_covers_less_than_1_year = end_date - start_date < one_year
        if hist_covers_less_than_1_year:
            start_date = end_date - one_year
    date_range = "%s - %s" % (format_as_date(start_date), format_as_date(end_date))

    c = {
        "history": history,
        "date_range": date_range,
        "unit": unit,
        "test_list": test_list,
        "test": test,
        "show_icons": settings.ICON_SETTINGS['SHOW_STATUS_ICONS_HISTORY'],
        'frequency': frequency
    }
    return template.render(c)


@register.filter
def as_pass_fail_status(test_list_instance, show_label=True):
    template = get_template("qa/pass_fail_status.html")
    # statuses_to_exclude = [models.NO_TOL]
    statuses_to_exclude = ['no_tol']
    c = {"instance": test_list_instance, "exclude": statuses_to_exclude, "show_label": show_label, 'show_icons': True}
    return template.render(c)


@register.filter
def as_review_status(test_list_instance, show_label=False):
    comment_count = test_list_instance.testinstance_set.exclude(Q(comment="") | Q(comment=None)).count()
    comment_count += test_list_instance.comments.count()
    template = get_template("qa/review_status.html")
    c = {
        "instance": test_list_instance,
        "comments": comment_count,
        "show_icons": settings.ICON_SETTINGS['SHOW_REVIEW_ICONS'],
        "show_label": show_label,
    }
    return template.render(c)


@register.filter(expects_local_time=True)
def as_due_date(unit_test_collection):
    template = get_template("qa/due_date.html")
    c = {"unit_test_collection": unit_test_collection, "show_icons": settings.ICON_SETTINGS["SHOW_DUE_ICONS"]}
    return template.render(c)


@register.filter(expects_local_time=True)
def as_qc_window(unit_test_collection):

    start, end = scheduling.qc_window(unit_test_collection.due_date, unit_test_collection.frequency)
    if start:
        start = format_as_date(start)

    if end:
        end = format_as_date(end)

    if start:
        return "%s - %s" % (start, end)
    elif unit_test_collection.due_date:
        start = format_as_date(unit_test_collection.due_date)
        return "%s - %s" % (start, end)

    return ""


@register.filter(is_safe=True, expects_local_time=True)
def as_time_delta(time_delta):
    hours, remainder = divmod(time_delta.seconds, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    return '%dd %dh %dm %ds' % (time_delta.days, hours, minutes, seconds)


as_time_delta.safe = True  # noqa: E305


@register.filter
def as_data_attributes(unit_test_collection):
    utc = unit_test_collection
    due_date = utc.due_date
    last_done = utc.last_done_date()

    attrs = {
        "frequency": utc.frequency.slug,
        "due_date": due_date.isoformat() if due_date else "",
        "last_done": last_done.isoformat() if last_done else "",
        "id": utc.pk,
        "unit_number": utc.unit.number,
    }

    return " ".join(['data-%s=%s' % (k, v) for k, v in list(attrs.items()) if v])


@register.filter
def hour_min(duration):
    if duration in (None, ""):
        return ""
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return '{:0>2}:{:0>2}'.format(hours, minutes)


@register.simple_tag
def service_status_label(status, size=None):
    template = get_template('service_log/service_event_status_label.html')
    return template.render({'colour': status.colour, 'name': status.name, 'size': '10.5' if size is None else size})


@register.simple_tag
def service_event_btn(event, size='xs'):
    template = get_template('service_log/service_event_btn.html')
    return template.render({'colour': event.service_status.colour, 'id': event.id, 'size': size})
