from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from qatrack.qa import models
from qatrack.units.forms import unit_site_unit_type_choices
from qatrack.units.models import Unit


class CopyReferencesAndTolerancesForm(forms.Form):
    """Form for copying references and tolerances from TestList Unit 'x' to TestList Unit 'y' """

    stage = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    confirm = forms.CharField(widget=forms.HiddenInput(), required=False)

    source_unit = forms.TypedChoiceField(
        label=_("Source Unit"),
        help_text=_("Choose the unit to copy references and tolerances from"),
        coerce=int,
        required=True,
    )
    content_type = forms.ChoiceField(
        label=_("Copy from TestList or TestListCycle"),
        choices=(
            ('', '---------'),
            ('testlist', _('TestList')),
            ('testlistcycle', _('TestListCycle')),
        ),
        required=True,
    )

    source_testlist = forms.ChoiceField(choices=[], label=_('Source testlist(cycle)'))
    dest_unit = forms.TypedChoiceField(
        label=_("Destination Unit"),
        help_text=_("Choose the unit to copy references and tolerances to"),
        coerce=int,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['source_unit'].choices = unit_site_unit_type_choices(include_empty=True)
        self.fields['dest_unit'].choices = unit_site_unit_type_choices(include_empty=True)
        testlistchoices = models.TestList.objects.all().order_by("name").values_list("pk", 'name')
        testlistcyclechoices = models.TestListCycle.objects.all().order_by("name").values_list("pk", 'name')
        choices = [('', '---------')] + list(testlistchoices) + list(testlistcyclechoices)
        self.fields['source_testlist'].choices = choices

    def save(self):
        source_unit = self.cleaned_data.get("source_unit")
        source_testlist = self.cleaned_data.get("source_testlist")
        dest_unit = self.cleaned_data.get("dest_unit")
        ctype = self.cleaned_data.get("content_type")
        ctype = ContentType.objects.get(model=ctype)
        source_utc = models.UnitTestCollection.objects.get(
            unit=source_unit,
            object_id=source_testlist,
            content_type=ctype,
        )
        source_utc.copy_references(dest_unit)

    def clean_content_type(self):
        ct = self.cleaned_data.get('content_type')
        if not ct:
            self.add_error("content_type", _("This field is required"))
        return ct

    def clean_source_unit(self):
        unit = self.cleaned_data.get('source_unit')
        if unit:
            return Unit.objects.get(pk=unit)

    def clean_dest_unit(self):
        unit = self.cleaned_data.get('dest_unit')
        if unit:
            return Unit.objects.get(pk=unit)

    def clean(self):
        cleaned_data = super().clean()
        source_unit = cleaned_data.get("source_unit")
        source_testlist = cleaned_data.get("source_testlist")
        dest_unit = cleaned_data.get("dest_unit")
        if source_unit and source_unit == dest_unit:
            self.add_error("dest_unit", _("The source and destination units must be different"))
        ctype = cleaned_data.get("content_type")
        if ctype and source_unit and source_testlist:
            ctype = ContentType.objects.get(model=ctype)
            try:
                models.UnitTestCollection.objects.get(
                    unit=source_unit,
                    object_id=source_testlist,
                    content_type=ctype,
                )
            except models.UnitTestCollection.DoesNotExist:
                self.add_error("source_testlist", _("The selected test list does not exist on the source unit"))
        return cleaned_data
