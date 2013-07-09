import collections

from django.template import Context
from django.template.loader import get_template
from django import template
from django.utils.safestring import mark_safe

import qatrack.qa.models as models
register = template.Library()


@register.simple_tag
def qa_value_form(form, include_history=False, include_ref_tols=False, test_info=None):
    template = get_template("qa/qavalue_form.html")
    c = Context({
        "form": form,
        "test_info": test_info,
        "include_history": include_history,
        "include_ref_tols": include_ref_tols,
    })
    return template.render(c)


#----------------------------------------------------------------------
@register.simple_tag
def reference_tolerance_span(test, ref, tol):

    if ref is None and not test.is_mult_choice():
        return mark_safe("<span>No Ref</span>")

    if test.is_boolean():
        return mark_safe('<span title="Passing value = %s">%s</span>' % (ref.value_display(), ref.value_display()))

    if not tol:
        if ref:
            return mark_safe('<span title="No Tolerance Set">%s</span>' % (ref.value_display()))
        return mark_safe('<span title="No Tolerance Set">No Tol</span>')

    if tol.type == models.MULTIPLE_CHOICE:
        return mark_safe('<span><abbr title="Passing Values: %s;  Tolerance Values: %s; All other choices are failing"><em>Mult. Choice</em></abbr></span>' % (", ".join(tol.pass_choices()), ', '.join(tol.tol_choices())))

    if tol.type == models.ABSOLUTE:
        return mark_safe('<span> <abbr title="(ACT L, TOL L, TOL H, ACT H) = %s ">%s</abbr></span>' % (str(tol).replace("Absolute",""), ref.value_display()))
    elif tol.type == models.PERCENT:
        return mark_safe('<span> <abbr title="(ACT L, TOL L, TOL H, ACT H) = %s ">%s</abbr></span>' % (str(tol).replace("Percent",""), ref.value_display()))


#----------------------------------------------------------------------
@register.filter
def history_display(history):
    template = get_template("qa/history.html")
    c = Context({"history": history})
    return template.render(c)


#----------------------------------------------------------------------
@register.filter
def as_pass_fail_status(test_list_instance, show_label=True):
    template = get_template("qa/pass_fail_status.html")
    statuses_to_exclude = [models.NO_TOL]
    c = Context({"instance": test_list_instance, "exclude": statuses_to_exclude, "show_label": show_label})
    return template.render(c)


#----------------------------------------------------------------------
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
        if ti.comment:
            comment_count += 1
    if test_list_instance.comment:
        comment_count += 1
    template = get_template("qa/review_status.html")
    c = Context({"statuses": dict(statuses), "comments": comment_count})
    return template.render(c)


#----------------------------------------------------------------------
@register.filter(expects_local_time=True)
def as_due_date(unit_test_collection):
    template = get_template("qa/due_date.html")
    c = Context({"unit_test_collection": unit_test_collection})
    return template.render(c)


#----------------------------------------------------------------------
@register.filter(is_safe=True, expects_local_time=True)
def as_time_delta(time_delta):
    hours, remainder = divmod(time_delta.seconds, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    return '%dd %dh %dm %ds' % (time_delta.days, hours, minutes, seconds)
as_time_delta.safe = True


#----------------------------------------------------------------------
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

    return " ".join(['data-%s=%s' % (k, v) for k, v in attrs.items() if v])
