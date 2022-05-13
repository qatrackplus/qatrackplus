import json
import logging

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views.generic import FormView
from formtools.preview import FormPreview

from qatrack.qa import models
from qatrack.qa.testpack import add_testpack, create_testpack
from qatrack.units.forms import unit_site_unit_type_choices
from qatrack.units.models import Unit

logger = logging.getLogger('qatrack')


class CopyReferencesAndTolerancesForm(forms.Form):
    """Form for copying references and tolerances from TestList Unit 'x' to TestList Unit 'y' """

    source_unit = forms.TypedChoiceField(
        label=_l("Source Unit"),
        help_text=_("Choose the unit to copy references and tolerances from"),
        coerce=int,
        required=True,
    )
    content_type = forms.ChoiceField(
        label=_l("Copy from TestList or TestListCycle"),
        choices=(
            ('', '---------'),
            ('testlist', _l('TestList')),
            ('testlistcycle', _l('TestListCycle')),
        ),
        required=True,
    )

    # Populate the source testlist field
    source_testlist = forms.ChoiceField(choices=[], label=_l('Source testlist(cycle)'))

    # Populate the dest_unit field
    dest_unit = forms.TypedChoiceField(
        label=_l("Destination Unit"),
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

        source_unit = self.cleaned_data.get("source_unit")
        source_testlist = self.cleaned_data.get("source_testlist")
        dest_unit = self.cleaned_data.get("dest_unit")
        if source_unit and source_unit == dest_unit:
            self.add_error("dest_unit", _("The source and destination units must be different"))
        ctype = self.cleaned_data.get("content_type")
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

        return self.cleaned_data


class CopyReferencesAndTolerances(FormPreview):

    form_template = 'admin/qa/unittestinfo/copy_refs_and_tols.html'
    preview_template = 'admin/qa/unittestinfo/copy_refs_and_tols_preview.html'

    def get_context(self, request, form):

        context = super().get_context(request, form)
        context['title'] = _("Copy References & Tolerances")
        if not request.POST:
            return context

        if not form.is_valid():
            return context

        cleaned_data = form.cleaned_data

        source_unit = cleaned_data.get("source_unit")
        dest_unit = cleaned_data.get("dest_unit")
        source_testlist_pk = cleaned_data.get("source_testlist")
        ctype = ContentType.objects.get(model=cleaned_data.get("content_type"))

        ModelClass = ctype.model_class()  # either TestList or TestListCycle

        source_testlist = ModelClass.objects.get(pk=source_testlist_pk)
        all_tests = source_testlist.all_tests()

        utis = models.UnitTestInfo.objects.filter(test__in=all_tests).select_related(
            "reference",
            "tolerance",
            "test",
        ).order_by("test")

        dest_utis = utis.filter(unit=dest_unit)
        source_utis = utis.filter(unit=source_unit)
        source_utis = {uti.test.pk: uti for uti in source_utis}
        dest_source_utis = [(dest_uti, source_utis[dest_uti.test.pk]) for dest_uti in dest_utis]
        context["dest_source_utis"] = dest_source_utis
        context["source_test_list"] = source_testlist
        context["source_unit"] = source_unit
        context["dest_unit"] = dest_unit

        return context

    def done(self, request, cleaned_data):

        if 'cancel' in request.POST:
            messages.warning(request, _("Copy references & tolerances cancelled"))
        else:
            form = CopyReferencesAndTolerancesForm(request.POST)
            form.full_clean()
            form.save()

            messages.success(request, _("References & tolerances successfully copied"))

        return HttpResponseRedirect(reverse('qa_copy_refs_and_tols'))


def testlist_json(request, source_unit, content_type):
    ctype = ContentType.objects.get(model=content_type)

    if ctype.name == 'test list':
        utcs = models.UnitTestCollection.objects.filter(
            unit__pk=source_unit,
            content_type=ctype,
        ).values_list(
            'object_id', flat=True
        )
        testlists = list(models.TestList.objects.filter(pk__in=utcs).values_list('pk', 'name'))
        return HttpResponse(json.dumps(testlists), content_type='application/json')
    elif ctype.name == 'test list cycle':
        utcs = models.UnitTestCollection.objects.filter(
            unit__pk=source_unit,
            content_type=ctype,
        ).values_list(
            'object_id', flat=True
        )
        testlistcycles = list(models.TestListCycle.objects.filter(pk__in=utcs).values_list('pk', 'name'))
        return HttpResponse(json.dumps(testlistcycles), content_type='application/json')
    else:
        raise ValidationError(_('Invalid value'))


class ExportTestPackForm(forms.Form):

    name = forms.SlugField(label=_l("Test Pack Name"))
    description = forms.CharField(
        label=_("Description"),
        widget=forms.Textarea(attrs={
            'rows': 4,
            'cols': ""
        }),
        required=False,
    )
    testlists = forms.CharField(widget=forms.HiddenInput(), required=False)
    testlistcycles = forms.CharField(widget=forms.HiddenInput(), required=False)
    tests = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean_testlists(self):
        t = self.cleaned_data['testlists'].strip()
        if t == "all":
            return models.TestList.objects.all()
        elif t:
            return models.TestList.objects.filter(id__in=t.split(","))
        return models.TestList.objects.none()

    def clean_testlistcycles(self):
        t = self.cleaned_data['testlistcycles'].strip()
        if t == "all":
            return models.TestListCycle.objects.all()
        elif t:
            return models.TestListCycle.objects.filter(id__in=t.split(","))
        return models.TestListCycle.objects.none()

    def clean_tests(self):
        t = self.cleaned_data['tests'].strip()
        if t == "all":
            return models.Test.objects.all()
        elif t:
            return models.Test.objects.filter(id__in=t.split(","))
        return models.Test.objects.none()

    def clean(self):
        if not any(self.data[t].strip() for t in ['tests', 'testlists', 'testlistcycles']):
            raise ValidationError(_("You must select at least one Test, TestList, or TestListCycle for Export"))
        return super().clean()


class ExportTestPack(FormView):
    """View for exporting a QATrack+ test pack"""

    form_class = ExportTestPackForm
    template_name = "admin/qa/testpack/export.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['title'] = _("Export Test Pack")

        context['cycles'] = models.TestListCycle.objects.all()
        context['testlists'] = models.TestList.objects.only("pk", "name", "description")
        context['tests'] = models.Test.objects.select_related("category").only(
            "pk",
            "name",
            "display_name",
            "type",
            "description",
            "category__name",
        )

        return context

    def form_valid(self, form):
        tls = form.cleaned_data['testlists']
        cycles = form.cleaned_data['testlistcycles']
        extra_tests = form.cleaned_data['tests']
        desc = form.cleaned_data['description']
        user = self.request.user
        name = form.cleaned_data['name']
        try:
            tp = create_testpack(
                test_lists=tls,
                cycles=cycles,
                extra_tests=extra_tests,
                description=desc,
                user=user,
                name=name,
                timeout=settings.TESTPACK_TIMEOUT,
            )
        except RuntimeError as e:
            form.add_error(None, ValidationError(str(e), code="timeout"))
            return self.form_invalid(form)

        response = HttpResponse(json.dumps(tp), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=%s' % (name + ".tpk")
        return response


class ImportTestPackForm(forms.Form):

    testpack_data = forms.CharField(widget=forms.HiddenInput())
    testlists = forms.CharField(widget=forms.HiddenInput(), required=False)
    testlistcycles = forms.CharField(widget=forms.HiddenInput(), required=False)
    tests = forms.CharField(widget=forms.HiddenInput(), required=False)


class ImportTestPack(FormView):
    """View for exporting a QATrack+ test pack"""

    form_class = ImportTestPackForm
    template_name = "admin/qa/testpack/import.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['title'] = _("Import Test Pack")
        context['test_types'] = json.dumps(dict(models.TEST_TYPE_CHOICES))

        return context

    def get_success_url(self):
        """Redirect user to previous page they were on if possible"""
        next_ = self.request.GET.get("next", None)
        if next_ is not None:
            return next_
        return reverse("qa_import_testpack")

    def form_valid(self, form):

        tls = form.cleaned_data['testlists']
        try:
            tls = json.loads(tls) if tls != "all" else None
        except ValueError:
            tls = None

        cycles = form.cleaned_data['testlistcycles']
        try:
            cycles = json.loads(cycles) if cycles != "all" else None
        except ValueError:
            cycles = None

        extra_tests = form.cleaned_data['tests']
        try:
            extra_tests = json.loads(extra_tests) if extra_tests != "all" else None
        except ValueError:
            extra_tests = None

        testpack = form.cleaned_data['testpack_data']
        try:
            counts, totals = add_testpack(
                testpack,
                self.request.user,
                test_keys=extra_tests,
                test_list_keys=tls,
                cycle_keys=cycles,
            )
            count_msg = ", ".join("%d/%d %s's" % (counts[k], totals[k], k) for k in totals)
            msg = _("Test Pack import successfully: %(item_counts)s were imported.") % {'item_counts': count_msg}

            messages.success(self.request, msg)
        except:  # noqa: E722
            msg = _("Sorry, but an error occurred when trying to import your TestPack. Please file a bug report.")
            logger.exception(msg)
            messages.error(self.request, msg)

        return super().form_valid(form)


def recurrence_examples(request):

    dates = []
    return JsonResponse({'dates': dates})
