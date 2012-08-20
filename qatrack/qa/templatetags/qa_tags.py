from django.template import Context
from django.template.loader import get_template
from django import template
from django.utils.safestring import mark_safe
from django.utils import formats

import qatrack.qa.models as models
register = template.Library()


@register.filter
def as_qavalue(form, include_admin):
    template = get_template("qavalue_form.html")
    c = Context({"form": form,"include_admin":include_admin})
    return template.render(c)

@register.filter
def as_unittestcollections_table(unit_lists, table_type="datatable"):

    template = get_template("unittestcollections_table.html")

    filter_table = table_type in ("review","datatable")

    unit_lists = unit_lists.select_related(
        "last_instance",
        "frequency",
        "unit__name",
    ).prefetch_related(
        "last_instance__testinstance_set",
        "assigned_to",
        "tests_object",
    )

    c = Context({
        "unittestcollections":unit_lists,
        "filter_table":filter_table,
        "table_type":table_type,
    })
    return template.render(c)

#----------------------------------------------------------------------
@register.filter
def as_pass_fail_status(test_list_instance):
    template = get_template("pass_fail_status.html")
    statuses_to_exclude = [models.NO_TOL]
    c = Context({"instance":test_list_instance,"exclude":statuses_to_exclude})
    return template.render(c)
#----------------------------------------------------------------------
@register.filter
def as_unreviewed_count(unit_test_collection):
    template = get_template("unreviewed_count.html")
    c = Context({"unit_test_collection":unit_test_collection})
    return template.render(c)
#----------------------------------------------------------------------
@register.filter
def as_due_date(unit_test_collection):
    template = get_template("due_date.html")
    c = Context({"unit_test_collection":unit_test_collection})
    return template.render(c)
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
from decimal import Decimal
from django.utils.encoding import force_unicode

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
