import json

from django.views.generic import FormView
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import HttpResponse
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from qatrack.qa.views import forms
from qatrack.units.models import Unit
from qatrack.qa.models import UnitTestCollection, TestList, TestListCycle


class SetReferencesAndTolerances(FormView):
    template_name = 'admin/unittestinfo_copy_refs_and_tols.html'
    form_class = forms.SetReferencesAndTolerancesForm

    def get_success_url(self):
        return reverse_lazy('qa_copy_refs_and_tols')

    def form_valid(self, form):
        form.save()
        return super(SetReferencesAndTolerances, self).form_valid(form)


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


def destunit_json(request, source_unit, content_type, testlist):

    ctype = ContentType.objects.get(model=content_type)

    if ctype.name not in ('test list', 'test list cycle'):
        raise ValidationError(_('Invalid value'), code='invalid')

    utcs = list(UnitTestCollection.objects.filter(object_id=testlist, content_type=ctype)
                    .exclude(unit__pk=source_unit).values_list('unit__pk', 'unit__name'))
    return HttpResponse(json.dumps(utcs), content_type='application/json')




