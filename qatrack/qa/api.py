import datetime
import tastypie
from tastypie.resources import Resource, ModelResource, ALL, ALL_WITH_RELATIONS

import qatrack.qa.models as models
from qatrack.units.models import Unit,Modality, UnitType

#============================================================================
class ModalityResource(ModelResource):
    class Meta:
        queryset = Modality.objects.order_by("type").all()
#============================================================================
class UnitTypeResource(ModelResource):
    class Meta:
        queryset = UnitType.objects.order_by("name").all()


#============================================================================
class UnitResource(ModelResource):
    modalities = tastypie.fields.ToManyField("qatrack.qa.api.ModalityResource","modalities",full=True)
    type = tastypie.fields.ToOneField("qatrack.qa.api.UnitTypeResource","type",full=True)
    class Meta:
        queryset = Unit.objects.order_by("number").all()

#============================================================================
class ReferenceResource(ModelResource):

    class Meta:
        queryset = models.Reference.objects.all()

#============================================================================
class ToleranceResource(ModelResource):

    class Meta:
        queryset = models.Tolerance.objects.all()


#============================================================================
class TaskListResource(ModelResource):
    class Meta:
        queryset = models.TaskList.objects.order_by("name").all()
#============================================================================
class TaskListItemInstanceResource(ModelResource):
    task_list_item = tastypie.fields.ToOneField("qatrack.qa.api.TaskListItemResource","task_list_item", full=True)
    reference = tastypie.fields.ToOneField("qatrack.qa.api.ReferenceResource","reference", full=True,null=True)
    tolerance = tastypie.fields.ToOneField("qatrack.qa.api.ToleranceResource","tolerance", full=True,null=True)

    class Meta:
        queryset = models.TaskListItemInstance.objects.all()
        resource_name = "values"
        filtering = {

            'task_list_item':ALL_WITH_RELATIONS,
            'work_completed':ALL
        }

    #----------------------------------------------------------------------
    def build_filters(self,filters=None):
        """allow filtering by unit"""
        if filters is None:
            filters = {}

        orm_filters = super(TaskListItemInstanceResource,self).build_filters(filters)

        if "units" in filters:
            orm_filters["unit__number__in"] = filters["units"].split(',')

        if "from_date" in filters:
            try:
                orm_filters["work_completed__gte"] = datetime.datetime.strptime(filters["from_date"],"%d-%m-%Y")
            except ValueError:
                pass
        if "to_date" in filters:
            try:
                orm_filters["work_completed__lte"] = datetime.datetime.strptime(filters["to_date"],"%d-%m-%Y")
            except ValueError:
                pass

        if "short_names" in filters:
            orm_filters["task_list_item__short_name__in"] = [x.strip() for x in filters["short_names"].split(',')]
        elif "task_list_id" in filters:
            orm_filters["task_list_item__pk"] = filters["pk"]
        return orm_filters

#----------------------------------------------------------------------
def serialize_tasklistiteminstance(task_list_item_instance):
    """return a dictionary of task_list_item_instance properties"""
    tlii = task_list_item_instance
    info = {
        'value':tlii.value,
        'date':tlii.work_completed.isoformat(),
        'save_date':tlii.created.isoformat(),
        'comment':tlii.comment,
        'status':tlii.status,
        'reference':None,
        'tolerance': {'type':None,'act_low':None,'tol_low':None,'tol_high':None,'act_high':None,},
        'user':None,
        'unit':None,
        'task_list_item':None,
    }
    if tlii.reference:
        info["reference"] = tlii.reference.value

    if tlii.tolerance:
        info['tolerance'] = {
            'type':tlii.tolerance.type,
            'act_low':tlii.tolerance.act_low,
            'tol_low':tlii.tolerance.tol_low,
            'tol_high':tlii.tolerance.tol_high,
            'act_high':tlii.tolerance.act_high,
        }

    if tlii.task_list_item:
        info["task_list_item"] = tlii.task_list_item.short_name

    if tlii.unit:
        info["unit"] = tlii.unit.number

    if tlii.created_by:
        info["user"] = tlii.created_by.username

    if tlii.task_list_item:
        info["task_list_item"] = tlii.task_list_item.short_name

    return info


#============================================================================
class ValueResource(Resource):
    """"""
    values = tastypie.fields.DictField()
    units = tastypie.fields.ListField()
    name = tastypie.fields.CharField()

    #============================================================================
    class Meta:
        resource_name = "grouped_values"
        allowed_methods = ["get"]
    #----------------------------------------------------------------------
    #def dehydrate_values(self,bundle):
    #    return bundle.obj["values"]
    #----------------------------------------------------------------------
    def dehydrate_name(self,bundle):
        return bundle.obj["name"]
    #----------------------------------------------------------------------
    def dehydrate_units(self,bundle):
        unit_data = []

        for unit in bundle.obj["units"]:
            data = []
            for task_list_item_instance in unit["data"]:
                data.append(serialize_tasklistiteminstance(task_list_item_instance))

            unit["data"] = data
        return bundle.obj["units"]
    #----------------------------------------------------------------------
    def get_object_list(self,request):
        """return organized values"""
        objects = TaskListItemInstanceResource().obj_get_list(request)
        short_names = objects.order_by("task_list_item__name").values_list("task_list_item__short_name",flat=True).distinct()
        units = objects.order_by("unit__number").values_list("unit__number",flat=True).distinct()
        self.dispatch
        organized = []
        for short_name in short_names:
            by_unit = []
            for unit in units:
                data = [
                    x for x in objects.filter(
                        task_list_item__short_name=short_name,
                        unit__number = unit,
                    ).order_by("work_completed")
                ]
                by_unit.append({"number":unit,"data":data})
            organized.append({
                'name':short_name,
                'units':by_unit,
            })
        return organized
    #----------------------------------------------------------------------
    def obj_get_list(self,request=None,**kwargs):
        return self.get_object_list(request)

#============================================================================
class TaskListItemResource(ModelResource):
    values = tastypie.fields.ToManyField(TaskListItemInstanceResource,"tasklistiteminstance_set")

    class Meta:
        queryset = models.TaskListItem.objects.all()
        filtering = {
            "short_name": ALL,
        }
    #----------------------------------------------------------------------
    def build_filters(self,filters=None):
        """allow filtering by unit"""
        if filters is None:
            filters = {}

        orm_filters = super(TaskListItemResource,self).build_filters(filters)

        if "unit" in filters:
            orm_filters["task_list_instance__task_list__unit__number"] = filters["unit"]
        return orm_filters
