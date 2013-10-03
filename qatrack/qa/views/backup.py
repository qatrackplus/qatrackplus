from urllib import urlencode

from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.views.generic import ListView, FormView
from django import forms

from .. import models
from qatrack.units.models import Unit


class PaperBackupRequestForm(forms.Form):
    """Form for choosing paper backup options"""

    units = forms.models.ModelMultipleChoiceField(
        queryset=Unit.objects,
        help_text=_("Choose which units to include")
    )

    frequencies = forms.models.ModelMultipleChoiceField(
        queryset=models.Frequency.objects,
        help_text=_("Choose which test list frequencies to include"),
    )

    test_categories = forms.models.ModelMultipleChoiceField(
        queryset=models.Category.objects,
        help_text=_("Choose which test categories to include"),
    )

    assigned_to = forms.models.ModelMultipleChoiceField(
        queryset=Group.objects,
        help_text=_("Filter test lists by who they are assigned to"),
    )

    include_refs = forms.BooleanField(
        label=_("References & Tolerances"),
        initial=True,
        required=False,
        help_text=_("Display references and tolerances in forms"),
    )

    include_inactive = forms.BooleanField(
        help_text=_("Include Inactive Test Lists"),
        initial=False,
        required=False,
    )


#============================================================================
class PaperFormRequest(FormView):
    """View for displaying paper backup options form"""

    form_class = PaperBackupRequestForm
    template_name = "qa/backup_form.html"

    #---------------------------------------------------------------
    def get_initial(self):
        """setup some hopefully sensible default options"""

        if self.request.method == "GET":
            return {
                "units": Unit.objects.values_list("pk", flat=True),
                "frequencies": models.Frequency.objects.filter(due_interval__lte=7).values_list("pk", flat=True),
                "test_categories": models.Category.objects.values_list("pk", flat=True),
                "assigned_to": Group.objects.values_list("pk", flat=True),
                "include_refs": True,
                "include_inactive": False,
            }
        return super(PaperFormRequest, self).get_initial()

    #---------------------------------------------------------------
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


#============================================================================
class PaperForms(ListView):
    """ View that handles the actual creation of the forms"""

    model = models.UnitTestCollection

    template_name_suffix = "_backup"

    #---------------------------------------------------------------
    def get_queryset(self):
        """filter queryset based on requested options"""

        qs = super(PaperForms, self).get_queryset().filter(
            unit__pk__in=self.request.GET.getlist("unit"),
            frequency__pk__in=self.request.GET.getlist("frequency"),
            assigned_to__pk__in=self.request.GET.getlist("assigned_to"),
        )

        if self.request.GET.get("include_inactive", "False") != "True":
            qs = qs.filter(active=True)

        return qs.select_related("unit", "testlist").prefetch_related("tests_object")

    #---------------------------------------------------------------
    def get_context_data(self, *args, **kwargs):
        """
        Patch each :model:`qa.UnitTestCollection` object with all
        its relevant TestList's, Test's & UnitTestInfo's.
        """

        context = super(PaperForms, self).get_context_data(*args, **kwargs)

        context["include_refs"] = self.request.GET.get("include_refs", "True") != "False"

        test_lists = {}

        for utc in context["object_list"]:
            key = (utc.content_type_id, utc.object_id)

            try:
                # if we've already seen this test list or test list cycle we don't need to
                # fetch all the test list members & tests again
                all_lists = test_lists[key]
            except KeyError:
                # first time we've seen this test list or test list cycle
                # find  all member test lists and tests
                all_lists = utc.tests_object.test_list_members().prefetch_related("testlistmembership_set__test")
                for li in all_lists:
                    li.all_tests = li.ordered_tests()
                test_lists[key] = all_lists

            for li in all_lists:
                utis = models.UnitTestInfo.objects.filter(
                    test__in=li.all_tests,
                    test__type__in=[models.BOOLEAN, models.SIMPLE, models.MULTIPLE_CHOICE, models.STRING],
                    test__category__pk__in=self.request.GET.getlist("category"),
                    unit=utc.unit,
                ).select_related(
                    "test", "reference", "tolerance"
                )

                li.utis = list(sorted(utis, key=lambda uti: li.all_tests.index(uti.test)))

            utc.all_lists = all_lists

        return context
