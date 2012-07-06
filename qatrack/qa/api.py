import csv
import StringIO
from qatrack.formats.en.formats import DATETIME_FORMAT
import django.utils.dateformat as dateformat
import tastypie
from tastypie.resources import Resource, ModelResource, ALL, ALL_WITH_RELATIONS
from tastypie.authentication import BasicAuthentication
from tastypie.authorization import DjangoAuthorization
from tastypie.utils import timezone
import qatrack.qa.models as models
from qatrack.units.models import Unit,Modality, UnitType
from tastypie.serializers import Serializer

def csv_date(dt):
    return dateformat.format(timezone.make_naive(dt),DATETIME_FORMAT)

class ValueResourceCSVSerializer(Serializer):

    formats = ['json', 'jsonp', 'csv']
    content_types = {
        'json': 'application/json',
        'jsonp': 'text/javascript',
        'csv': 'text/csv',
    }
    columns = [
        ("Dates","dates",),
        ("Values","values",),
        ("Act Low","tolerances","act_low"),
        ("Tol Low","tolerances","tol_low"),
        ("Reference","references",),
        ("Tol High","tolerances","tol_high"),
        ("Act High","tolerances","act_high"),
        ("Tol Type","tolerances","type"),
        ("Comment","comment",),
        ("Username","user","username"),
    ]

    #----------------------------------------------------------------------
    def instances_to_csv(self,instances):
        rows = [[x[0] for x in self.columns]]
        for i in instances:
            tol_type = ""
            al, tl, th, ah = "","","",""
            if i.tolerance:
                al, tl = i.tolerance.act_low,i.tolerance.tol_low
                ah, th = i.tolerance.act_high,i.tolerance.tol_high
                tol_type = i.tolerance.type
            r = ""
            if i.reference:
                r = i.reference.value

            rows.append([csv_date(i.work_completed),i.value,al,tl,r,th,ah,tol_type,i.comment,i.created_by.username])

        return rows
    #----------------------------------------------------------------------
    def to_csv(self, data, options=None):
        options = options or {}

        csv_data = StringIO.StringIO()
        writer = csv.writer(csv_data)

        for item in data["objects"]:
            headers  = ["Unit:","Unit%02d" %item.data["unit"],"Test:",item.data["name"]]
            column = [headers] + self.instances_to_csv(item.obj["data"])
            writer.writerows(column)

        return csv_data.getvalue()

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
        return list(bundle.obj.assigned_to.values_list("frequency__slug",flat=True).distinct())

#============================================================================
class TestInstanceResource(ModelResource):
    test = tastypie.fields.ForeignKey("qatrack.qa.api.TestResource","test", full=True)
    reference = tastypie.fields.ForeignKey("qatrack.qa.api.ReferenceResource","reference", full=True,null=True)
    tolerance = tastypie.fields.ForeignKey("qatrack.qa.api.ToleranceResource","tolerance", full=True,null=True)
    status = tastypie.fields.ForeignKey("qatrack.qa.api.StatusResource","status",full=True)
    unit = tastypie.fields.ForeignKey(UnitResource,"unit",full=True);
    reviewed_by = tastypie.fields.CharField()
    class Meta:
        queryset = models.TestInstance.objects.all()
        resource_name = "values"
        allowed_methods = ["get","patch","put"]
        always_return_data = True
        filtering = {
            'test':ALL_WITH_RELATIONS,
            'work_completed':ALL,
            'id':ALL,
            'unit':ALL_WITH_RELATIONS,
            'status':ALL_WITH_RELATIONS,
        }
        ordering= ["work_completed"]
        authentication = BasicAuthentication()
        authorization = DjangoAuthorization()
    #----------------------------------------------------------------------
    def dehydrate_reviewed_by(self,bundle):
        if bundle.obj.reviewed_by:
            return bundle.obj.reviewed_by.username

    #----------------------------------------------------------------------
    def build_filters(self,filters=None):
        """allow filtering by unit"""
        if filters is None:
            filters = {}

        orm_filters = super(TestInstanceResource,self).build_filters()


        filters_requiring_processing = (
            ("from_date","work_completed__gte","date"),
            ("to_date","work_completed__lte","date"),
            ("unit","unit__number__in",None),
            ("slug","test__slug__in",None),
        )

        for field,filter_string,filter_type in filters_requiring_processing:

            value = filters.pop(field,[])

            if filter_type == "date":
                try:
                    value = timezone.datetime.datetime.strptime(value[0],"%d-%m-%Y")
                    value = timezone.make_aware(value)
                except ValueError:
                    pass

            orm_filters[filter_string] = value

        #non specfic list filters
        for key in filters:
            if key in self.Meta.filtering:
                orm_filters["%s__in"%key] = filters.getlist(key)

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
        'reviewed_by':None
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
        info["test"] = ti.test.slug

    if ti.unit:
        info["unit"] = ti.unit.number

    if ti.created_by:
        info["user"] = ti.created_by.username

    if ti.reviewed_by:
        info["reviewed_by"] = ti.reviewed_by.username

    if ti.test:
        info["test"] = ti.test.slug

    return info

#============================================================================
class FrequencyResource(ModelResource):
    class Meta:
        queryset = models.Frequency.objects.all()


#============================================================================
class StatusResource(ModelResource):
    """avaialable test statuses"""
    class Meta:
        queryset = models.TestInstanceStatus.objects.all()


#============================================================================
class ValueResource(Resource):
    unit = tastypie.fields.IntegerField()
    name = tastypie.fields.CharField()
    slug = tastypie.fields.CharField()
    data = tastypie.fields.DictField()

    #============================================================================
    class Meta:
        serializer = ValueResourceCSVSerializer()
        resource_name = "grouped_values"
        allowed_methods = ["get"]
    #----------------------------------------------------------------------
    def dehydrate_slug(self,bundle):
        return bundle.obj["slug"]
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


        return data
    #----------------------------------------------------------------------
    def get_object_list(self,request):
        """return organized values"""
        objects = TestInstanceResource().obj_get_list(request)
        names = objects.order_by("test__name").values_list("test__slug","test__name").distinct()
        units = objects.order_by("unit__number").values_list("unit__number",flat=True).distinct()
        self.dispatch
        organized = []
        for slug,name in names:
            for unit in units:
                data = objects.filter(
                        test__slug=slug,
                        unit__number = unit,
                ).order_by("work_completed","pk")

                organized.append({
                    'slug':slug,
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
            "slug": ALL,
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
            "test_list": ALL_WITH_RELATIONS,
            "id":ALL,
        }

        ordering= ["work_completed","id"]

    #----------------------------------------------------------------------
    def dehydrate_review_status(self,bundle):
        reviewed = bundle.obj.testinstance_set.exclude(status__requires_review=True).count()
        total = bundle.obj.testinstance_set.count()
        if total == reviewed:
            #ugly
            try:
                test = bundle.obj.testinstance_set.latest()
                review = (test.modified_by,test.modified)
            except models.TestInstance.DoesNotExist:
                review = ()
        else:
            review = ()
        return review