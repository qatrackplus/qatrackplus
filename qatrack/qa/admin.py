import datetime

import django.forms as forms
import django.db

from django.utils.translation import ugettext as _
from django.contrib import admin
from django.contrib.admin.templatetags.admin_static import static
from django.utils.safestring import mark_safe

import qatrack.qa.models as models
from qatrack.units.models import Unit
import qatrack.settings as settings
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
            obj.created = datetime.datetime.now()
        obj.modified_by = request.user
        super(SaveUserMixin, self).save_model(request, obj, form, change)


#============================================================================
class BasicSaveUserAdmin(SaveUserMixin, admin.ModelAdmin):
    """manage reference values for tests"""

#----------------------------------------------------------------------
def title_case_name(obj):
    return ("%s"%obj.name).title()
title_case_name.short_description = "Name"

#============================================================================
class CategoryAdmin(admin.ModelAdmin):
    """QA categories admin"""
    prepopulated_fields =  {'slug': ('name',)}

#============================================================================
class TestInfoForm(forms.ModelForm):
    reference_value = forms.FloatField(
        label=_("Update reference"),
        help_text=_("For Yes/No tests, enter 1 for Yes and 0 for No"),
        required=False,
    )
    #reference_type = forms.ChoiceField(choices=models.Reference.TYPE_CHOICES)

    class Meta:
        model = models.UnitTestInfo

    #----------------------------------------------------------------------
    def clean(self):
        """make sure valid numbers are entered for boolean data"""

        if "reference_value" not in self.cleaned_data:
            return self.cleaned_data

        ref_value = self.cleaned_data["reference_value"]

        if self.instance.test.type == models.BOOLEAN:
            if int(ref_value) not in (0,1):
                raise forms.ValidationError(_("Yes/No values must be 0 or 1"))

        return self.cleaned_data


#============================================================================
class TestInfoAdmin(admin.ModelAdmin):
    """"""
    form = TestInfoForm
    fields = (
        "unit", "test",
        "reference", "tolerance",
        "reference_value",
    )
    list_display = ["test", "unit", "reference", "tolerance"]
    list_filter = ["unit","test__category"]
    readonly_fields = ("test","unit","reference")

    #----------------------------------------------------------------------
    def save_model(self, request, test_info, form, change):
        """create new reference when user updates value"""
        if form.instance.test.type == models.BOOLEAN:
            ref_type = models.BOOLEAN
        else:
            ref_type = models.NUMERICAL
        val = form["reference_value"].value()
        if val not in ("", None):
            ref = models.Reference(
                value=val,
                ref_type = ref_type,
                created_by = request.user,
                modified_by = request.user,
                name = "%s %s" % (test_info.unit.name,test_info.test.name)
            )
            ref.save()
            test_info.reference = ref
        super(TestInfoAdmin,self).save_model(request,test_info,form,change)


#============================================================================
class TestListAdminForm(forms.ModelForm):
    """Form for handling validation of TestList creation/editing"""

    #----------------------------------------------------------------------
    def clean_sublists(self):
        """Make sure a user doesn't try to add itself as sublist"""
        sublists = self.cleaned_data["sublists"]
        if self.instance in sublists:
            raise django.forms.ValidationError("You can't add a list to its own sublists")

        return sublists

#============================================================================
class TestInlineFormset(forms.models.BaseInlineFormSet):

    #----------------------------------------------------------------------
    def clean(self):
        """Make sure there are no duplicated short_name's in a TestList"""
        super(TestInlineFormset,self).clean()

        short_names = [f.instance.test.short_name for f in self.forms[:-self.extra]]
        duplicates = list(set([sn for sn in short_names if short_names.count(sn)>1]))
        if duplicates:
            raise forms.ValidationError(
                "The following short_names are duplicated " + ",".join(duplicates)
            )

        return self.cleaned_data


#============================================================================
class TestListMembershipInline(admin.TabularInline):
    """"""
    model = models.TestListMembership
    formset = TestInlineFormset
    extra = 1
    template = "admin/qa/testlistmembership/edit_inline/tabular.html"

#============================================================================
class TestListAdmin(SaveUserMixin, admin.ModelAdmin):
    prepopulated_fields =  {'slug': ('name',)}
    list_display = (title_case_name, "set_references", "modified", "modified_by", "active")
    list_filter = ("active",)
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
    list_display = ["name","short_name","category", "type", "set_references"]
    list_filter = ["category","type"]

    #============================================================================
    class Media:
        js = (
            settings.STATIC_URL+"js/jquery-1.7.1.min.js",
            settings.STATIC_URL+"js/test_admin.js",
        )

#============================================================================
class UnitTestListAdmin(admin.ModelAdmin):
    readonly_fields = ("unit","frequency",)
    filter_horizontal = ("test_lists","cycles",)
    list_display = ["name", "unit", "frequency"]
    list_filter = ["unit", "frequency"]


#============================================================================
class TestListCycleMembershipInline(admin.TabularInline):

    model = models.TestListCycleMembership
    extra = 0

#============================================================================
class TestListCycleAdmin(admin.ModelAdmin):
    """Admin for daily test list cycles"""
    inlines = [TestListCycleMembershipInline]

    #============================================================================
    class Media:
        js = (
            settings.STATIC_URL+"js/jquery-1.7.1.min.js",
            settings.STATIC_URL+"js/jquery-ui.min.js",
            settings.STATIC_URL+"js/collapsed_stacked_inlines.js",
            settings.STATIC_URL+"js/m2m_drag_admin.js",
        )

admin.site.register([models.Tolerance], BasicSaveUserAdmin)
admin.site.register([models.Category], CategoryAdmin)
admin.site.register([models.TestList],TestListAdmin)
admin.site.register([models.Test],TestAdmin)
admin.site.register([models.UnitTestInfo],TestInfoAdmin)
admin.site.register([models.UnitTestLists],UnitTestListAdmin)

admin.site.register([models.TestListCycle],TestListCycleAdmin)