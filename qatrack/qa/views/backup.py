from urllib.parse import urlencode

from django import forms
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _l
from django.views.generic import FormView, ListView

from qatrack.units.models import Unit

from .. import models


class PaperBackupRequestForm(forms.Form):
    """Form for choosing paper backup options"""

    units = forms.models.ModelMultipleChoiceField(
        label=_l("Units"),
        queryset=Unit.objects,
        help_text=_l("Choose which units to include")
    )

    frequencies = forms.models.ModelMultipleChoiceField(
        label=_l("Frequencies"),
        queryset=models.Frequency.objects,
        help_text=_l("Choose which test list frequencies to include"),
    )

    test_categories = forms.models.ModelMultipleChoiceField(
        label=_l("Categories"),
        queryset=models.Category.objects,
        help_text=_l("Choose which test categories to include"),
    )

    assigned_to = forms.models.ModelMultipleChoiceField(
        label=_l("Assigned To"),
        queryset=Group.objects,
        help_text=_l("Filter test lists by who they are assigned to"),
    )

    include_refs = forms.BooleanField(
        label=_l("References & Tolerances"),
        initial=True,
        required=False,
        help_text=_l("Display references and tolerances in forms"),
    )

    include_inactive = forms.BooleanField(
        label=_l("Include Inactive"),
        help_text=_l("Include Inactive Test Lists"),
        initial=False,
        required=False,
    )


class PaperFormRequest(FormView):
    """View for displaying paper backup options form"""

    form_class = PaperBackupRequestForm
    template_name = "qa/backup_form.html"

    def get_initial(self):
        """setup some hopefully sensible default options"""

        if self.request.method == "GET":
            return {
                "units": Unit.objects.values_list("pk", flat=True),
                "frequencies": models.Frequency.objects.filter(nominal_interval__lte=7).values_list("pk", flat=True),
                "test_categories": models.Category.objects.values_list("pk", flat=True),
                "assigned_to": Group.objects.values_list("pk", flat=True),
                "include_refs": True,
                "include_inactive": False,
            }
        return super(PaperFormRequest, self).get_initial()

    def form_valid(self, form):
        """
        url encode all requested options and redirect to the actual
        PaperForms view.
        """

        q = urlencode({
            "unit": form.cleaned_data["units"].values_list("pk", flat=True),
            "frequency": form.cleaned_data["frequencies"].values_list("pk", flat=True),
            "category": form.cleaned_data["test_categories"].values_list("pk", flat=True),
            "assigned_to": form.cleaned_data["assigned_to"].values_list("pk", flat=True),
            "include_refs": form.cleaned_data["include_refs"],
            "include_inactive": form.cleaned_data["include_inactive"],
        }, doseq=True)

        return HttpResponseRedirect("%s?%s" % (reverse("qa_paper_forms"), q))


class PaperForms(ListView):
    """ View that handles the actual creation of the forms"""

    model = models.UnitTestCollection

    template_name_suffix = "_backup"

    def get_queryset(self):
        """filter queryset based on requested options"""

        qs = super(PaperForms, self).get_queryset().filter(
            unit__pk__in=self.request.GET.getlist("unit"),
            frequency__pk__in=self.request.GET.getlist("frequency"),
            assigned_to__pk__in=self.request.GET.getlist("assigned_to"),
        )

        if self.request.GET.get("include_inactive", "False") != "True":
            qs = qs.filter(active=True)

        return qs.select_related("unit").prefetch_related("tests_object")

    def set_utc_all_lists(self, utcs):

        for utc in utcs:

            all_lists = utc.tests_object.test_list_members().prefetch_related("testlistmembership_set__test")
            for li in all_lists:
                li.all_tests = li.ordered_tests()

            for li in all_lists:
                utis = models.UnitTestInfo.objects.filter(
                    test__in=li.all_tests,
                    test__type__in=[
                        models.BOOLEAN, models.SIMPLE, models.WRAPAROUND, models.MULTIPLE_CHOICE, models.STRING
                    ],
                    test__category__pk__in=self.categories,
                    unit=utc.unit,
                ).select_related("test", "reference", "tolerance")

                li.utis = list(sorted(utis, key=lambda uti: li.all_tests.index(uti.test)))

            utc.all_lists = all_lists

    def get_context_data(self, *args, **kwargs):
        """
        Patch each :model:`qa.UnitTestCollection` object with all
        its relevant TestList's, Test's & UnitTestInfo's.
        """

        context = super(PaperForms, self).get_context_data(*args, **kwargs)
        context["include_refs"] = self.request.GET.get("include_refs", "True") != "False"
        self.categories = self.request.GET.getlist("category")
        self.set_utc_all_lists(context['object_list'])
        return context
