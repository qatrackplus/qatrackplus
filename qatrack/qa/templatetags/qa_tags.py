import collections

from django import template
from django.conf import settings
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from qatrack.qa import models, utils
from qatrack.qatrack_core.utils import format_as_date

register = template.Library()


@register.simple_tag
def qa_value_form(form, test_list, perms, test_info=None, unit_test_collection=None, show_category=True):
    template = get_template("qa/qavalue_form.html")
    c = {
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
        params = (
            tsd['ok'],
            ", ".join(tol.pass_choices()),
            tsd['tolerance'],
            ', '.join(tol.tol_choices())
        )
        return mark_safe((
            '<span><abbr title="%s Values: %s;  %s Values: %s; All other choices are failing">'
            '<em>Choice</em></abbr></span>'
        ) % params)

    tsds = settings.TEST_STATUS_DISPLAY_SHORT
    if tol.type == models.ABSOLUTE:
        return mark_safe('<span> <abbr title="(%s L, %s L, %s H, %s H) = %s ">%s</abbr></span>' % (
            tsds["action"], tsds["tolerance"], tsds["tolerance"], tsds["action"],
            str(tol).replace("Absolute", ""), ref.value_display() if ref else "")
        )
    elif tol.type == models.PERCENT:
        return mark_safe('<span> <abbr title="(%s L, %s L, %s H, %s H) = %s ">%s</abbr></span>' % (
            tsds["action"], tsds["tolerance"], tsds["tolerance"], tsds["action"],
            str(tol).replace("Percent", ""), ref.value_display() if ref else "")
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
    tols["tol_disp"] = tsd['ok']
    tols["act_disp"] = tsd['action']
    return mark_safe(
        '<span>%(ok_disp)s: Between %(tol_low)s &amp; %(tol_high)s</br> '
        '%(tol_disp)s Between %(act_low)s &amp; %(act_high)s</br> '
        '%(act_disp)s: < %(act_low)s or > %(act_high)s</span>' % tols
    )


@register.simple_tag
def history_display(history, unit, test_list, test, frequency=None):
    template = get_template("qa/history.html")
    c = {
        "history": history,
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
    c = {
        "instance": test_list_instance,
        "exclude": statuses_to_exclude,
        "show_label": show_label,
        'show_icons': True
    }
    return template.render(c)


@register.filter
def as_review_status(test_list_instance):
    statuses = collections.defaultdict(lambda: {"count": 0})
    comment_count = 0
    for ti in test_list_instance.testinstance_set.all():
        statuses[ti.status.name]["count"] += 1
        statuses[ti.status.name]["valid"] = ti.status.valid
        statuses[ti.status.name]["requires_review"] = ti.status.requires_review
        statuses[ti.status.name]["reviewed_by"] = test_list_instance.reviewed_by
        statuses[ti.status.name]["reviewed"] = test_list_instance.reviewed
        statuses[ti.status.name]["colour"] = ti.status.colour
        if ti.comment:
            comment_count += 1
    # if test_list_instance.comment:
    #     comment_count += 1
    comment_count += test_list_instance.comments.count()
    template = get_template("qa/review_status.html")
    c = {
        "statuses": dict(statuses),
        "comments": comment_count,
        "show_icons": settings.ICON_SETTINGS['SHOW_REVIEW_ICONS'],
    }
    return template.render(c)


@register.filter(expects_local_time=True)
def as_due_date(unit_test_collection):
    template = get_template("qa/due_date.html")
    c = {"unit_test_collection": unit_test_collection, "show_icons": settings.ICON_SETTINGS["SHOW_DUE_ICONS"]}
    return template.render(c)


@register.filter(expects_local_time=True)
def as_qc_window(unit_test_collection):

    start, end = utils.qc_window(unit_test_collection.due_date, unit_test_collection.frequency)
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
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return '{:0>2}:{:0>2}'.format(hours, minutes)


@register.simple_tag
def service_status_label(status, size=None):
    template = get_template('service_log/service_event_status_label.html')
    return template.render({
        'colour': status.colour,
        'name': status.name,
        'size': '10.5' if size is None else size
    })


@register.simple_tag
def service_event_btn(event, size='xs'):
    template = get_template('service_log/service_event_btn.html')
    return template.render({
        'colour': event.service_status.colour,
        'id': event.id,
        'size': size
    })
