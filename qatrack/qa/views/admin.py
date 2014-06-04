import json

from django.views.generic import FormView
from django.contrib.formtools.preview import FormPreview
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import HttpResponse, HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from qatrack.qa.views import forms
from qatrack.units.models import Unit
from qatrack.qa.models import UnitTestCollection, TestList, TestListCycle, UnitTestInfo


class SetReferencesAndTolerances(FormPreview):

    form_template = 'admin/unittestinfo_copy_refs_and_tols.html'
    preview_template = 'admin/unittestinfo_copy_refs_and_tols_preview.html'

    def get_context(self, request, form):

        context = super(SetReferencesAndTolerances, self).get_context(request, form)
        if not request.POST:
            return context

        form.full_clean()
        cleaned_data = form.cleaned_data

        source_unit = cleaned_data.get("source_unit")
        dest_unit = cleaned_data.get("dest_unit")
        source_testlist_pk = cleaned_data.get("source_testlist")
        ctype = ContentType.objects.get(model=cleaned_data.get("content_type"))

        ModelClass = ctype.model_class() # either TestList or TestListCycle

        source_testlist = ModelClass.objects.get(pk=source_testlist_pk)
        all_tests = source_testlist.all_tests()

        dest_utis = UnitTestInfo.objects.filter(test__in=all_tests, unit=dest_unit).order_by("test")
        source_utis = UnitTestInfo.objects.filter(test__in=all_tests, unit=source_unit).order_by("test")

        context["dest_source_utis"] = zip(dest_utis, source_utis)
        context["source_test_list"] = source_testlist
        context["source_unit"] = source_unit
        context["dest_unit"] = dest_unit

        return context

    def done(self, request, cleaned_data):

        if 'cancel' in request.POST:
            messages.warning(request, "Copy references & tolerances cancelled")
        else:
            form = forms.SetReferencesAndTolerancesForm(request.POST)
            form.full_clean()
            form.save()

            messages.success(request, "References & tolerances successfully copied")

        return HttpResponseRedirect(reverse_lazy('qa_copy_refs_and_tols'))


def testlist_json(request, source_unit, content_type):
    ctype = ContentType.objects.get(model=content_type)

    if ctype.name == 'test list':
        utcs = UnitTestCollection.objects.filter(unit__pk=source_unit, content_type=ctype).values_list('object_id', flat=True)
        testlists = list(TestList.objects.filter(pk__in=utcs).values_list('pk', 'name'))
        return HttpResponse(json.dumps(testlists), content_type='application/json')
    elif ctype.name == 'test list cycle':
        utcs = UnitTestCollection.objects.filter(unit__pk=source_unit, content_type=ctype).values_list('object_id', flat=True)
        testlistcycles = list(TestListCycle.objects.filter(pk__in=utcs).values_list('pk','name'))
        return HttpResponse(json.dumps(testlistcycles), content_type='application/json')
    else:
        raise ValidationError(_('Invalid value'))



