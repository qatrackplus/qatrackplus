from django.template import Context
from django.template.loader import get_template
from django import template

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
    c = Context({"instance":test_list_instance})
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


