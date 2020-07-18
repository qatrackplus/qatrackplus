import json

from dateutil import parser
from django import forms
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.utils.translation import gettext as _

from qatrack.qatrack_core.utils import format_as_date
from qatrack.qatrack_core.widgets import ToolTipSelect
from qatrack.reports import models, reports


class ReportForm(forms.ModelForm):
    """Main form for controlling global report settings (as opposed to report type specific
    controls/filters"""

    prefix = "root"

    class Meta:
        model = models.SavedReport
        fields = ("title", "report_type", "report_format", "visible_to", "include_signature")

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        f = self.fields['report_type']
        choices = [('', '------------')] + reports.report_type_choices()
        f.widget = ToolTipSelect(titles=reports.report_descriptions(), choices=choices)


class ReportNoteForm(forms.ModelForm):

    prefix = "report-note-N"

    class Meta:
        model = models.ReportNote
        fields = ("heading", "content",)
        widgets = {
            'heading': forms.TextInput(),
            'content': forms.Textarea(attrs={'rows': 3}),
            'DELETE': forms.HiddenInput(),
        }


class ReportNoteFormSetBase(forms.BaseFormSet):

    def add_fields(self, form, index):
        """ hide ordering and deletion fields """
        super().add_fields(form, index)
        if 'DELETE' in form.fields:
            form.fields['DELETE'].widget = forms.HiddenInput()


ReportNoteFormSet = forms.inlineformset_factory(
    models.SavedReport,
    models.ReportNote,
    extra=0,
    fields=(
        "heading",
        "content",
    ),
    widgets={
        'heading': forms.TextInput(),
        'content': forms.Textarea(attrs={'rows': 3}),
    },
    formset=ReportNoteFormSetBase,
)


def value_to_serializable(val, val_type=None):
    """Convert input report form value to something serializable TODO:: handle
    other input types (single date or datetime) """

    if 'daterange' in val_type.lower() and not isinstance(val, str):
        d1 = format_as_date(parser.parse(val[0]))
        d2 = format_as_date(parser.parse(val[1]))
        val = "%s - %s" % (d1, d2)
    elif val_type == "recurrencefield":
        val = str(val)

    if isinstance(val, Model):  # pragma: no cover
        val = val.pk

    try:
        val = [x.pk for x in val]
    except (TypeError, AttributeError):
        pass

    return val


def serialize_forms(forms, data_attr="initial"):

    form_data = {}

    for form in forms:

        prefix = form.prefix + "-" if form.prefix else ''

        for k, v in getattr(form, data_attr).items():

            if k not in form.fields:  # pragma: no cover
                continue

            field = form.fields[k]
            if type(field.widget).__name__ == "RecurrenceWidget":
                inp_type = "recurrence"
            else:
                inp_type = form.fields[k].widget.input_type

            val_type = field.__class__.__name__.lower()
            v = value_to_serializable(v, val_type)
            form_data[prefix + k] = [inp_type, v]

    return form_data


def serialize_savedreport(instance):
    """
    Convert a report instance to form field dict {id_field_name: field_val}
    """

    report_form = ReportForm(instance=instance)
    filter_set = instance.get_filter_class()(instance.filters)
    filter_form = filter_set.get_form_class()(initial=instance.filters)

    form_data = {}
    forms = [report_form, filter_form]
    form_data = serialize_forms(forms)

    return form_data


def serialize_report(report):
    """Convert a report instance to form field dict {id_field_name: field_val}"""

    report_form = ReportForm(initial=report.base_opts)

    forms = [report_form]
    if report.filter_class:
        filter_set = report.filter_class(report.report_opts)
        filter_form = filter_set.get_form_class()(initial=report.report_opts)
        forms.append(filter_form)

    form_data = serialize_forms(forms)
    return form_data


def serialize_form_data(form_data):
    """Take form data and dump to json. Querysets and models will be converted to pks"""

    data = {}
    for k, v in form_data.items():

        if isinstance(v, Model):
            v = v.pk
        else:
            try:
                v = [obj.pk for obj in v]
            except (TypeError, AttributeError):
                pass

        data[k] = v

    return json.dumps(data, cls=DjangoJSONEncoder)


class ReportScheduleForm(forms.ModelForm):
    """Form for udpate report schedule"""

    prefix = "schedule"

    class Meta:
        model = models.ReportSchedule
        fields = ("report", "schedule", "time", "groups", "users", "emails")

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['report'].widget = forms.HiddenInput()
        self.fields['emails'].widget.attrs['rows'] = 1

    def clean(self):

        cleaned_data = super().clean()
        no_groups = len(cleaned_data.get('groups', [])) == 0
        no_users = len(cleaned_data.get('users', [])) == 0
        no_emails = len([x for x in cleaned_data.get("emails", "").split(",") if x]) == 0
        if no_groups and no_users and no_emails:
            msg = _("You must select at least one group, user, or email address!")
            self.add_error(None, forms.ValidationError(msg))

        return cleaned_data
