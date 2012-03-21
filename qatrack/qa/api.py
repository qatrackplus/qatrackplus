import tastypie
from tastypie.resources import ModelResource, ALL, ALL_WITH_RELATIONS
import qatrack.qa.models as models

#============================================================================
class ReferenceResource(ModelResource):

    class Meta:
        queryset = models.Reference.objects.all()

#============================================================================
class ToleranceResource(ModelResource):

    class Meta:
        queryset = models.Tolerance.objects.all()



class TaskListItemInstanceResource(ModelResource):
    task_list_item = tastypie.fields.ToOneField("qatrack.qa.api.TaskListItemResource","task_list_item")
    reference = tastypie.fields.ToOneField("qatrack.qa.api.ReferenceResource","reference", full=True)
    tolerance = tastypie.fields.ToOneField("qatrack.qa.api.ToleranceResource","tolerance", full=True)

    class Meta:
        #queryset = models.TaskListItemInstance.objects.all()
        resource_name = "values"

    #----------------------------------------------------------------------
    def build_filters(self,filters=None):
        """allow filtering by unit"""
        if filters is None:
            filters = {}

        orm_filters = super(TaskListItemInstanceResource,self).build_filters(filters)

        if "unit" in filters:
            orm_filters["task_list_instance__task_list__unit__number"] = filters["unit"]
        if "slug" in filters:
            orm_filters["task_list_item__short_name"] = filters["slug"]

        return orm_filters


#============================================================================
class TaskListItemResource(ModelResource):
    values = tastypie.fields.ToManyField(TaskListItemInstanceResource,"tasklistiteminstance_set")

    class Meta:
        queryset = models.TaskListItem.objects.all()

    #----------------------------------------------------------------------
    def build_filters(self,filters=None):
        """allow filtering by unit"""
        if filters is None:
            filters = {}

        orm_filters = super(TaskListItemResource,self).build_filters(filters)

        if "unit" in filters:
            orm_filters["task_list_instance__task_list__unit__number"] = filters["unit"]
        return orm_filters
