from django.contrib.contenttypes.models import ContentType
from django.views.generic import ListView
from .. import models


class PaperForms(ListView):
    model = models.UnitTestCollection

    template_name_suffix = "_backup"

    #---------------------------------------------------------------
    def get_queryset(self):
        qs = super(PaperForms,self).get_queryset().filter(
            active=True,
            frequency__due_interval=1,

        ).select_related(
            "unit",
            "testlist",
        ).prefetch_related(
            "tests_object",
            )
        return qs
    #---------------------------------------------------------------
    def get_context_data(self, *args, **kwargs):
        context = super(PaperForms,self).get_context_data(*args,**kwargs)

        test_lists = {}

        content_type_models = {}

        test_collections = []
        for utc in context["object_list"]:
            key = (utc.content_type_id, utc.object_id)

            try:
                all_lists = test_lists[key]
            except KeyError:
                all_lists = utc.tests_object.test_list_members().prefetch_related("testlistmembership_set__test")
                for li in all_lists:
                    li.all_tests = li.ordered_tests()
                test_lists[key] = all_lists

            for li in all_lists:
                utis = models.UnitTestInfo.objects.filter(
                    test__in=li.all_tests,
                    unit=utc.unit
                ).select_related(
                    "test","reference","tolerance"
                )
                li.utis = list(utis)
            utc.all_lists = all_lists
        return context
