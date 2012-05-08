import tastypie
from tastypie.resources import Resource, ModelResource, ALL, ALL_WITH_RELATIONS
from tastypie.authentication import BasicAuthentication
from tastypie.authorization import DjangoAuthorization
from tastypie.utils import timezone
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
        filtering = {
            "number": ALL_WITH_RELATIONS,
            "name":ALL,
        }

#============================================================================
class ReferenceResource(ModelResource):
    class Meta:
        queryset = models.Reference.objects.all()

#============================================================================
class ToleranceResource(ModelResource):
    class Meta:
        queryset = models.Tolerance.objects.all()


#============================================================================
class CategoryResource(ModelResource):
    class Meta:
        queryset = models.Category.objects.all()

#============================================================================
class TestListResource(ModelResource):
    tests = tastypie.fields.ToManyField("qatrack.qa.api.TestResource","tests",full=True)
    frequencies = tastypie.fields.ListField()

    class Meta:
        queryset = models.TestList.objects.order_by("name").all()
        filtering = {
            "pk":ALL,
            "slug":ALL,
            "name":ALL,
        }
    #----------------------------------------------------------------------
    def dehydrate_frequencies(self,bundle):
        return list(bundle.obj.unittestlists_set.values_list("frequency",flat=True).distinct())

#============================================================================
class TestInstanceResource(ModelResource):
    test = tastypie.fields.ForeignKey("qatrack.qa.api.TestResource","test", full=True)
    reference = tastypie.fields.ForeignKey("qatrack.qa.api.ReferenceResource","reference", full=True,null=True)
    tolerance = tastypie.fields.ForeignKey("qatrack.qa.api.ToleranceResource","tolerance", full=True,null=True)
    unit = tastypie.fields.ForeignKey(UnitResource,"unit",full=True);

    class Meta:
        queryset = models.TestInstance.objects.all()
        resource_name = "values"
        allowed_methods = ["get","patch","put"]
        always_return_data = True
        filtering = {
            'test':ALL_WITH_RELATIONS,
            'work_completed':ALL,
            'id':ALL,
        }
        ordering= ["work_completed"]
        authentication = BasicAuthentication()
        authorization = DjangoAuthorization()

    #----------------------------------------------------------------------
    def build_filters(self,filters=None):
        """allow filtering by unit"""
        if filters is None:
            filters = {}

        orm_filters = super(TestInstanceResource,self).build_filters(filters)

        if "units" in filters:
            orm_filters["unit__number__in"] = filters["units"].split(',')

        if "from_date" in filters:
            try:
                orm_filters["work_completed__gte"] = timezone.datetime.datetime.strptime(filters["from_date"],"%d-%m-%Y")
            except ValueError:
                pass
        if "to_date" in filters:
            try:
                orm_filters["work_completed__lte"] = timezone.datetime.datetime.strptime(filters["to_date"],"%d-%m-%Y")
            except ValueError:
                pass

        if "review_status" in filters:
            orm_filters["status__in"] = filters["review_status"].split(',')

        if "short_names" in filters:
            orm_filters["test__short_name__in"] = [x.strip() for x in filters["short_names"].split(',')]
        #elif "test_id" in filters:
        #    orm_filters["test__pk"] = filters["pk"]
        return orm_filters

    #----------------------------------------------------------------------
    def is_authorized(self,request,obj=None):
        auth =super(TestInstanceResource,self).is_authorized(request,obj)
        return auth



#----------------------------------------------------------------------
def serialize_testinstance(test_instance):
    """return a dictionary of test_instance properties"""
    ti = test_instance
    info = {
        'value':ti.value,
        'date':ti.work_completed.isoformat(),
        'save_date':ti.created.isoformat(),
        'comment':ti.comment,
        'status':ti.status,
        'reference':None,
        'tolerance': {'type':None,'act_low':None,'tol_low':None,'tol_high':None,'act_high':None,},
        'user':None,
        'unit':None,
        'test':None,
    }
    if ti.reference:
        info["reference"] = ti.reference.value

    if ti.tolerance:
        info['tolerance'] = {
            'type':ti.tolerance.type,
            'act_low':ti.tolerance.act_low,
            'tol_low':ti.tolerance.tol_low,
            'tol_high':ti.tolerance.tol_high,
            'act_high':ti.tolerance.act_high,
        }

    if ti.test:
        info["test"] = ti.test.short_name

    if ti.unit:
        info["unit"] = ti.unit.number

    if ti.created_by:
        info["user"] = ti.created_by.username

    if ti.test:
        info["test"] = ti.test.short_name

    return info

#============================================================================
class FrequencyResource(Resource):
    """available test frequencies"""
    value = tastypie.fields.CharField()
    display = tastypie.fields.CharField()
    class Meta:
        allowed_methods = ["get"]
    #----------------------------------------------------------------------
    def dehydrate_value(self,bundle):
        return bundle.obj["value"]
    #----------------------------------------------------------------------
    def dehydrate_display(self,bundle):
        return bundle.obj["display"]
    #----------------------------------------------------------------------
    def get_object_list(self):
        return [{"value":x[0],"display":x[1]} for x in models.FREQUENCY_CHOICES]
    #----------------------------------------------------------------------
    def obj_get_list(self,request=None,**kwargs):
        return self.get_object_list()

#============================================================================
class StatusResource(Resource):
    """avaialable test statuses"""
    value = tastypie.fields.CharField()
    display = tastypie.fields.CharField()
    class Meta:
        allowed_methods = ["get"]
    #----------------------------------------------------------------------
    def dehydrate_value(self,bundle):
        return bundle.obj["value"]
    #----------------------------------------------------------------------
    def dehydrate_display(self,bundle):
        return bundle.obj["display"]
    #----------------------------------------------------------------------
    def get_object_list(self):
        return [{"value":x[0],"display":x[1]} for x in models.STATUS_CHOICES]
    #----------------------------------------------------------------------
    def obj_get_list(self,request=None,**kwargs):
        return self.get_object_list()


#============================================================================
class ValueResource(Resource):
    unit = tastypie.fields.IntegerField()
    name = tastypie.fields.CharField()
    short_name = tastypie.fields.CharField()
    data = tastypie.fields.DictField()
    #============================================================================
    class Meta:
        resource_name = "grouped_values"
        allowed_methods = ["get"]
    #----------------------------------------------------------------------
    def dehydrate_short_name(self,bundle):
        return bundle.obj["short_name"]
    #----------------------------------------------------------------------
    def dehydrate_name(self,bundle):
        return bundle.obj["name"]
    #----------------------------------------------------------------------
    def dehydrate_unit(self,bundle):
        return bundle.obj["unit"]
    #----------------------------------------------------------------------
    def dehydrate_data(self,bundle):
        """"""
        data = {
            'values':[],
            'references':[],

            'tolerances':[],
            'comments':[],
            'dates':[],
            'users':[]
        }
        for test_instance in bundle.obj["data"]:
            instance = serialize_testinstance(test_instance)
            for prop in ('value','reference','date','user'):
                data[prop+'s'].append(instance.get(prop,None))
            data["tolerances"].append(instance["tolerance"])
            #for tol in ("act_low","tol_low","tol_high","act_high"):
            #    data[tol].append(instance['tolerance'].get(tol,None))


        return data
    #----------------------------------------------------------------------
    def get_object_list(self,request):
        """return organized values"""
        objects = TestInstanceResource().obj_get_list(request)
        names = objects.order_by("test__name").values_list("test__short_name","test__name").distinct()
        units = objects.order_by("unit__number").values_list("unit__number",flat=True).distinct()
        self.dispatch
        organized = []
        for short_name,name in names:
            for unit in units:
                data = objects.filter(
                        test__short_name=short_name,
                        unit__number = unit,
                ).order_by("work_completed")

                organized.append({
                    'short_name':short_name,
                    'name':name,
                    'unit':unit,
                    'data':data,
                })
        return organized
    #----------------------------------------------------------------------
    def obj_get_list(self,request=None,**kwargs):
        return self.get_object_list(request)

#============================================================================
class TestResource(ModelResource):

    category = tastypie.fields.ToOneField(CategoryResource,"category",full=True)
    class Meta:
        queryset = models.Test.objects.all()
        filtering = {
            "short_name": ALL,
            "id":ALL
        }
    #    excludes = ["values"]

    #----------------------------------------------------------------------
    def build_filters(self,filters=None):
        """allow filtering by unit"""
        if filters is None:
            filters = {}

        orm_filters = super(TestResource,self).build_filters(filters)

        if "unit" in filters:
            orm_filters["test_instance__test_list__unit__number"] = filters["unit"]
        return orm_filters

#============================================================================
class TestListInstanceResource(ModelResource):
    unit = tastypie.fields.ForeignKey(UnitResource,"unit",full=True)
    test_list = tastypie.fields.ForeignKey(TestListResource,"test_list",full=True)
    test_instances = tastypie.fields.ToManyField(TestInstanceResource,"testinstance_set",full=True)
    review_status = tastypie.fields.ListField()

    class Meta:
        queryset = models.TestListInstance.objects.all()
        filtering = {
            "unit":ALL_WITH_RELATIONS,
            "test_list": ALL_WITH_RELATIONS
        }

        ordering= ["work_completed"]

    #----------------------------------------------------------------------
    def dehydrate_review_status(self,bundle):
        reviewed = bundle.obj.testinstance_set.exclude(status=models.UNREVIEWED).count()
        total = bundle.obj.testinstance_set.count()
        if total == reviewed:
            #ugly
            test = bundle.obj.testinstance_set.latest()
            review = (test.modified_by,test.modified)
        else:
            review = ()
        return review