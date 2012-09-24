import collections

from django.template import Context
from django.template.loader import get_template
from django import template
from django.utils.safestring import mark_safe
from django.utils import formats

from decimal import Decimal, ROUND_HALF_UP
from django.utils.encoding import force_unicode

import qatrack.qa.models as models
register = template.Library()


@register.simple_tag
def qa_value_form(form, include_admin=False,test_info=None):
    template = get_template("qa/qavalue_form.html")
    c = Context({
        "form": form,
        "test_info":test_info,
        "include_admin":include_admin

    })
    return template.render(c)

#----------------------------------------------------------------------
@register.simple_tag
def reference_tolerance_span(test,ref,tol):

    if ref is None and not test.is_mult_choice():
        return mark_safe("<span>No Ref</span>")

    if test.is_boolean():
        return mark_safe('<span title="Passing value = %s">%s</span>' %(ref.value_display(),ref.value_display()))

    if not tol:
        return	mark_safe('<span title="No Tolerance Set">No Tol</span>')

    if tol.type == models.MULTIPLE_CHOICE:
        return mark_safe('<span><abbr title="Passing Values: %s;  Tolerance Values: %s; All other choices are failing"><em>Mult. Choice</em></abbr></span>' %(", ".join(tol.pass_choices()),', '.join(tol.tol_choices())))


    if tol.type == models.ABSOLUTE:
        return mark_safe('<span> <abbr title="(AL, TL, TH, AH) = (%s, %s, %s, %s)">%s</abbr></span>'% (tol.act_low,tol.tol_low,tol.tol_high,tol.act_high, ref.value_display()))
    elif tol.type == models.PERCENT:
        return mark_safe('<span> <abbr title="(AL, TL, TH, AH) = (%.1f%%, %.1f%%, %.1f%%, %.1f%%)">%s</abbr></span>'% (tol.act_low,tol.tol_low,tol.tol_high,tol.act_high, ref.value_display()))

#----------------------------------------------------------------------
@register.filter
def history_display(history,test):
    template = get_template("qa/history.html")
    c = Context({"history":history,"test":test})
    return template.render(c)

#----------------------------------------------------------------------
@register.filter
def as_pass_fail_status(test_list_instance):
    template = get_template("qa/pass_fail_status.html")
    statuses_to_exclude = [models.NO_TOL]
    c = Context({"instance":test_list_instance,"exclude":statuses_to_exclude})
    return template.render(c)

#----------------------------------------------------------------------
@register.filter
def as_review_status(test_list_instance):
    statuses = collections.defaultdict(lambda:{"count":0})
    for ti in test_list_instance.testinstance_set.all():
        statuses[ti.status.name]["count"] += 1
        statuses[ti.status.name]["valid"] = ti.status.valid
        statuses[ti.status.name]["requires_review"] = ti.status.requires_review
        statuses[ti.status.name]["reviewed_by"] = test_list_instance.modified_by
        statuses[ti.status.name]["reviewed"] = test_list_instance.modified

    template = get_template("qa/review_status.html")
    c = Context({"statuses":dict(statuses)})
    return template.render(c)

#----------------------------------------------------------------------
@register.filter(expects_local_time=True)
def as_due_date(unit_test_collection):
    template = get_template("qa/due_date.html")
    c = Context({"unit_test_collection":unit_test_collection})
    return template.render(c)

#----------------------------------------------------------------------
@register.filter(is_safe=True,expects_local_time=True)
def as_time_delta(time_delta):
    hours, remainder = divmod(time_delta.seconds, 60*60)
    minutes, seconds = divmod(remainder, 60)
    return '%dd %dh %dm %ds' % (time_delta.days, hours, minutes, seconds)
as_time_delta.safe = True
#----------------------------------------------------------------------
@register.filter
def as_data_attributes(unit_test_collection):
    utc = unit_test_collection
    due_date = utc.due_date()
    last_done = utc.last_done_date()

    attrs = {
        "frequency": utc.frequency.slug,
        "due_date": due_date.isoformat() if due_date else "",
        "last_done":last_done.isoformat() if last_done else "",
        "id":utc.pk,
        "unit_number":utc.unit.number,
    }

    return " ".join(['data-%s=%s' % (k,v) for k,v in attrs.items() if v])


pos_inf = 1e200 * 1e200
neg_inf = -1e200 * 1e200
nan = (1e200 * 1e200) / (1e200 * 1e200)
special_floats = [str(pos_inf), str(neg_inf), str(nan)]

@register.filter
def scientificformat(text):
    """
    Displays a float in scientific notation.

    If the input float is infinity or NaN, the (platform-dependent) string
    representation of that value will be displayed.

    This is based on the floatformat function in django/template/defaultfilters.py

    http://classmplanet.wordpress.com/2011/06/26/displaying-floats-with-scientific-notation/
    """

    try:
        input_val = force_unicode(text)
        d = Decimal(input_val)
    except UnicodeEncodeError:
        return u''
    except :
        if input_val in special_floats:
            return input_val
        try:
            d = Decimal(force_unicode(float(text)))
        except (ValueError,  TypeError, UnicodeEncodeError):
            return u''

    try:
        m = int(d) - d
    except (ValueError, OverflowError):
        return input_val

    try:
        # for 'normal' sized numbers
        if d.is_zero():
            number = u'0'
        elif  (Decimal('-10000') < d < Decimal('-0.01')) or (Decimal('0.01') < d < Decimal('10000')):
            # this is what the original floatformat() function does
            sign, digits, exponent = d.quantize(Decimal('.001'), ROUND_HALF_UP).as_tuple()
            digits = [unicode(digit) for digit in reversed(digits)]
            while len(digits) <= abs(exponent):
                digits.append(u'0')
            digits.insert(-exponent, u'.')
            if sign:
                digits.append(u'-')
            number = u''.join(reversed(digits)).rstrip("0")

        else:
            # for very small and very large numbers
            sign, digits, exponent = d.as_tuple()
            exponent = d.adjusted()
            digits = [unicode(digit) for digit in digits][:3] # limit to 2 decimal places
            while len(digits) < 3:
                digits.append(u'0')
            digits.insert(1, u'.')
            if sign:
                digits.insert(0, u'-')
            number = u''.join(digits)
            number += u'e' + u'%i' % exponent

        return mark_safe(formats.number_format(number))
    except :
        return input_val

scientificformat.is_safe = True