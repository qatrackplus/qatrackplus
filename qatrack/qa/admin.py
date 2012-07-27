import django.forms as forms
import django.db

from salmonella.admin import SalmonellaMixin

from django.utils.translation import ugettext as _
from django.contrib import admin
from django.contrib.admin.templatetags.admin_static import static
from django.utils.safestring import mark_safe
from django.utils import timezone

import qatrack.qa.models as models
from qatrack.units.models import Unit
import qatrack.settings as settings
import os
import re

#============================================================================
class SaveUserMixin(object):
    """A Mixin to save creating user and modifiying user

    Set editable=False on the created_by and modified_by model you
    want to use this for.
    """

    #----------------------------------------------------------------------
    def save_model(self, request, obj, form, change):
        """set user and modified date time"""
        if not obj.pk:
            obj.created_by = request.user
            obj.created = timezone.now()
        obj.modified_by = request.user
        super(SaveUserMixin, self).save_model(request, obj, form, change)


#============================================================================
class BasicSaveUserAdmin(SaveUserMixin, admin.ModelAdmin):
    """manage reference values for tests"""


#============================================================================
class CategoryAdmin(admin.ModelAdmin):
    """QA categories admin"""
    prepopulated_fields =  {'slug': ('name',)}

#============================================================================
class TestInfoForm(forms.ModelForm):
    reference_value = forms.FloatField(label=_("New reference value"),required=False,)
    test_type = forms.CharField(required=False)

    class Meta:
        model = models.UnitTestInfo

    def __init__(self, *args, **kwargs):
        super(TestInfoForm, self).__init__(*args, **kwargs)
        self.fields['test_type'].widget.attrs['readonly'] = "readonly"
        #self.fields['test_type'].widget.attrs['disabled'] = "disabled"


        if self.instance:
            tt = self.instance.test.type
            i = [x[0] for x in models.TEST_TYPE_CHOICES].index(tt)
            self.fields["test_type"].initial = models.TEST_TYPE_CHOICES[i][1]

            if tt == models.BOOLEAN:
                self.fields["reference_value"].widget = forms.Select(choices=[(-1,"---"),(0,"No"),(1,"Yes")])
            elif tt == models.MULTIPLE_CHOICE:
                self.fields["reference_value"].widget = forms.Select(choices=[(-1,"---")]+self.instance.test.get_choices())

    #----------------------------------------------------------------------
    def clean(self):
        """make sure valid numbers are entered for boolean data"""

        if "reference_value" not in self.cleaned_data:
            return self.cleaned_data

        ref_value = self.cleaned_data["reference_value"]

        if self.instance.test.type == models.BOOLEAN and int(ref_value) not in (0,1):
                raise forms.ValidationError(_("You must select Yes or No as a new reference value"))

        if self.instance.test.type in (models.BOOLEAN, models.MULTIPLE_CHOICE):
            if self.cleaned_data["tolerance"] is not None:
                raise forms.ValidationError(_("Please leave tolerance field blank for boolean and multiple choice test types"))
        return self.cleaned_data


#============================================================================
class UnitTestInfoAdmin(admin.ModelAdmin):
    """"""
    form = TestInfoForm
    fields = (
        "unit", "test","test_type",
        "reference", "tolerance",
        "reference_value",
    )
    list_display = ["test", "unit", "reference", "tolerance"]
    list_filter = ["unit","test__category"]
    readonly_fields = ("reference","test", "unit",)

    #---------------------------------------------------------------------------
    def has_add_permission(self,request):
        """unittestinfo's are created automatically"""
        return False
    def has_delete_permission_(self,request, obj=None):
        """unittestinfo's are deleted automatically when test lists removed from unit"""
        return False
    #----------------------------------------------------------------------
    def save_model(self, request, test_info, form, change):
        """create new reference when user updates value"""
        if form.instance.test.type == models.BOOLEAN:
            ref_type = models.BOOLEAN
        elif form.instance.test.type == models.MULTIPLE_CHOICE:
            ref_type = models.MULTIPLE_CHOICE
        else:
            ref_type = models.NUMERICAL
        val = form["reference_value"].value()
        if val not in ("", None):
            ref = models.Reference(
                value=val,
                type = ref_type,
                created_by = request.user,
                modified_by = request.user,
                name = "%s %s" % (test_info.unit.name,test_info.test.name)[:255]
            )
            ref.save()
            test_info.reference = ref
        super(UnitTestInfoAdmin,self).save_model(request,test_info,form,change)


#============================================================================
class TestListAdminForm(forms.ModelForm):
    """Form for handling validation of TestList creation/editing"""

    #----------------------------------------------------------------------
    def clean_sublists(self):
        """Make sure a user doesn't try to add itself as sublist"""
        sublists = self.cleaned_data["sublists"]
        if self.instance in sublists:
            raise django.forms.ValidationError("You can't add a list to its own sublists")

        if self.instance.pk and self.instance.testlist_set.count() > 0 and len(sublists) > 0:
            msg = "Sublists can't be nested more than 1 level deep."
            msg += " This list is already a member of %s and therefore"
            msg += " can't have sublists of it's own."
            msg = msg % ", ".join([str(x) for x in self.instance.testlist_set.all()])
            raise django.forms.ValidationError(msg)

        return sublists

#============================================================================
class TestInlineFormset(forms.models.BaseInlineFormSet):

    #----------------------------------------------------------------------
    def clean(self):
        """Make sure there are no duplicated slugs in a TestList"""
        super(TestInlineFormset,self).clean()

        if not hasattr(self,"cleaned_data"):
            #something else went wrong already
            return {}

        slugs = [f.instance.test.slug for f in self.forms if (hasattr(f.instance,"test") and not f.cleaned_data["DELETE"])]
        slugs = [x for x in slugs if x]
        duplicates = list(set([sn for sn in slugs if slugs.count(sn)>1]))
        if duplicates:
            raise forms.ValidationError(
                "The following macro names are duplicated :: " + ",".join(duplicates)
            )

        return self.cleaned_data



#----------------------------------------------------------------------
def test_name(obj):
    return obj.test.name
#----------------------------------------------------------------------
def macro_name(obj):
    return obj.test.slug
#============================================================================
class TestListMembershipInline(SalmonellaMixin,admin.TabularInline):
    """"""
    model = models.TestListMembership
    formset = TestInlineFormset
    extra = 5
    template = "admin/qa/testlistmembership/edit_inline/tabular.html"
    readonly_fields = (macro_name,)
    salmonella_fields = ("test",)
#============================================================================
class TestListAdmin(SaveUserMixin, admin.ModelAdmin):
    prepopulated_fields =  {'slug': ('name',)}
    list_display = ("name", "set_references", "modified", "modified_by",)
    search_fields = ("name", "description","slug",)
    filter_horizontal= ("tests", "sublists", )
    form = TestListAdminForm
    inlines = [TestListMembershipInline]

    #============================================================================
    class Media:
        js = (
            settings.STATIC_URL+"js/jquery-1.7.1.min.js",
            settings.STATIC_URL+"js/jquery-ui.min.js",
            #settings.STATIC_URL+"js/collapsed_stacked_inlines.js",
            settings.STATIC_URL+"js/m2m_drag_admin.js",
        )


#============================================================================
class TestAdmin(SaveUserMixin, admin.ModelAdmin):
    list_display = ["name","slug","category", "type", "set_references"]
    list_filter = ["category","type"]
    search_fields = ["name","slug","category__name"]
    #============================================================================
    class Media:
        js = (
            settings.STATIC_URL+"js/jquery-1.7.1.min.js",
            settings.STATIC_URL+"js/test_admin.js",
        )

#----------------------------------------------------------------------
def unit_name(obj):
    return obj.unit.name
unit_name.admin_order_field = "unit__name"
unit_name.short_description = "Unit"
def freq_name(obj):
    return obj.frequency.name
freq_name.admin_order_field = "frequency__name"
freq_name.short_description = "Frequency"
def assigned_to_name(obj):
    return obj.assigned_to.name
assigned_to_name.admin_order_field = "assigned_to__name"
assigned_to_name.short_description = "Assigned To"

#============================================================================
class UnitTestCollectionAdmin(admin.ModelAdmin):
    #readonly_fields = ("unit","frequency",)
    #filter_horizontal = ("test_lists","cycles",)
    list_display = ["test_objects_name", unit_name, freq_name,assigned_to_name]
    list_filter = ["unit__name", "frequency__name","assigned_to__name"]
    search_fields = ["unit__name","frequency__name","testlist__name","testlistcycle__name"]
    change_form_template = "admin/treenav/menuitem/change_form.html"

#============================================================================
class TestListCycleMembershipInline(admin.TabularInline):

    model = models.TestListCycleMembership
    extra = 0


#============================================================================
class TestListCycleAdmin(SaveUserMixin, admin.ModelAdmin):
    """Admin for daily test list cycles"""
    inlines = [TestListCycleMembershipInline]
    prepopulated_fields =  {'slug': ('name',)}

    #============================================================================
    class Media:
        js = (
            settings.STATIC_URL+"js/jquery-1.7.1.min.js",
            settings.STATIC_URL+"js/jquery-ui.min.js",
            settings.STATIC_URL+"js/collapsed_stacked_inlines.js",
            settings.STATIC_URL+"js/m2m_drag_admin.js",
        )

#============================================================================
class FrequencyAdmin(admin.ModelAdmin):
    prepopulated_fields =  {'slug': ('name',)}
    model = models.Frequency

#============================================================================
class StatusAdmin(admin.ModelAdmin):
    prepopulated_fields =  {'slug': ('name',)}
    model = models.TestInstanceStatus


admin.site.register([models.Tolerance], BasicSaveUserAdmin)
admin.site.register([models.Category], CategoryAdmin)
admin.site.register([models.TestList],TestListAdmin)
admin.site.register([models.Test],TestAdmin)
admin.site.register([models.UnitTestInfo],UnitTestInfoAdmin)
admin.site.register([models.UnitTestCollection],UnitTestCollectionAdmin)

admin.site.register([models.TestListCycle],TestListCycleAdmin)
admin.site.register([models.Frequency], FrequencyAdmin)
admin.site.register([models.TestInstanceStatus], StatusAdmin)
admin.site.register([models.TestListInstance,models.TestInstance], admin.ModelAdmin)