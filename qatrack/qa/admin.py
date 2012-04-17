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
    """manage reference values for task list items"""

#----------------------------------------------------------------------
def title_case_name(obj):
    return ("%s"%obj.name).title()
title_case_name.short_description = "Name"

#============================================================================
class CategoryAdmin(admin.ModelAdmin):
    """QA categories admin"""
    prepopulated_fields =  {'slug': ('name',)}

#============================================================================
class TaskListItemInfoForm(forms.ModelForm):
    reference_value = forms.FloatField(
        label=_("Update reference"),
        help_text=_("For Yes/No tests, enter 1 for Yes and 0 for No"),
        required=False,
    )
    #reference_type = forms.ChoiceField(choices=models.Reference.TYPE_CHOICES)

    class Meta:
        model = models.TaskListItemUnitInfo

    #----------------------------------------------------------------------
    def clean(self):
        """make sure valid numbers are entered for boolean data"""

        if "reference_value" not in self.cleaned_data:
            return self.cleaned_data

        ref_value = self.cleaned_data["reference_value"]

        if self.instance.task_list_item.task_type == models.BOOLEAN:
            if int(ref_value) not in (0,1):
                raise forms.ValidationError(_("Yes/No values must be 0 or 1"))

        return self.cleaned_data


#============================================================================
class TaskListItemInfoAdmin(admin.ModelAdmin):
    """"""
    form = TaskListItemInfoForm
    fields = (
        "unit", "task_list_item",
        "reference", "tolerance",
        "reference_value",
    )
    list_display = ["task_list_item", "unit", "reference", "tolerance"]
    list_filter = ["unit","task_list_item__category"]
    readonly_fields = ("task_list_item","unit","reference")

    #----------------------------------------------------------------------
    def save_model(self, request, item_info, form, change):
        """create new reference when user updates value"""
        if form.instance.task_list_item.task_type == models.BOOLEAN:
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
                name = "%s %s" % (item_info.unit.name,item_info.task_list_item.name)
            )
            ref.save()
            item_info.reference = ref
        super(TaskListItemInfoAdmin,self).save_model(request,item_info,form,change)


#============================================================================
class TaskListAdminForm(forms.ModelForm):
    """Form for handling validation of TaskList creation/editing"""

    #----------------------------------------------------------------------
    def clean_sublists(self):
        """Make sure a user doesn't try to add itself as sublist"""
        sublists = self.cleaned_data["sublists"]
        if self.instance in sublists:
            raise django.forms.ValidationError("You can't add a list to its own sublists")

        return sublists
class TaskListItemInlineFormset(forms.models.BaseInlineFormSet):

    #----------------------------------------------------------------------
    def clean(self):
        """"""
        super(TaskListItemInlineFormset,self).clean()
        short_names = [f.instance.task_list_item.short_name for f in self.forms[:-self.extra]]
        duplicates = list(set([sn for sn in short_names if short_names.count(sn)>1]))
        if duplicates:
            raise forms.ValidationError(
                "The following short_names are duplicated " + ",".join(duplicates)
            )

        return self.cleaned_data


#============================================================================
class TaskListMembershipInline(admin.TabularInline):
    """"""
    model = models.TaskListMembership
    formset = TaskListItemInlineFormset
    extra = 1
    template = "admin/qa/tasklistmembership/edit_inline/tabular.html"

#============================================================================
class TaskListAdmin(SaveUserMixin, admin.ModelAdmin):
    prepopulated_fields =  {'slug': ('name',)}
    list_display = (title_case_name, "set_references", "modified", "modified_by", "active")
    list_filter = ("active",)
    filter_horizontal= ("task_list_items", "sublists", )
    form = TaskListAdminForm
    inlines = [TaskListMembershipInline]

    #============================================================================
    class Media:
        js = (
            settings.STATIC_URL+"js/jquery-1.7.1.min.js",
            settings.STATIC_URL+"js/jquery-ui.min.js",
            #settings.STATIC_URL+"js/collapsed_stacked_inlines.js",
            settings.STATIC_URL+"js/m2m_drag_admin.js",
        )


#============================================================================
class TaskListItemAdminForm(forms.ModelForm):
    """custom tasklistitem form to ensure valid shortname to be used in Python snippets"""
    VARIABLE_RE = re.compile("^[a-zA-Z_]+[0-9a-zA-Z_]*")
    RESULT_RE = re.compile("^result\s*=\s*[(_0-9.a-zA-Z]+.*$",re.MULTILINE)

    #----------------------------------------------------------------------
    def clean_short_name(self):
        """replace any dashes in short_name (short_name is an autogenerated slug field) with underscores"""
        short_name = self.cleaned_data["short_name"]
        if not self.VARIABLE_RE.match(short_name):
            raise forms.ValidationError(
                _("Short names must contain only letters, numbers and underscores and start with a ltter or underscore")
            )
        return short_name
    #----------------------------------------------------------------------
    def clean_snippet(self):
        """ensure there's a result defined in the snippet"""
        snippet = self.cleaned_data["snippet"]
        if not snippet:
            return ""
        if not self.RESULT_RE.findall(snippet):
            raise forms.ValidationError(
                _('Snippet must contain a result line (e.g. result = my_var/another_var*2)')
            )

        return snippet

#============================================================================
class TaskListItemAdmin(SaveUserMixin, admin.ModelAdmin):
    form = TaskListItemAdminForm
    list_display = ["name","short_name","category", "task_type", "set_references"]
    list_filter = ["category","task_type"]



#============================================================================
class UnitTaskListAdmin(admin.ModelAdmin):
    readonly_fields = ("unit","frequency",)
    filter_horizontal = ("task_lists","cycles",)
    list_display = ["name", "unit", "frequency"]
    list_filter = ["unit", "frequency"]


#============================================================================
class TaskListCycleMembershipInline(admin.TabularInline):

    model = models.TaskListCycleMembership
    extra = 0

#============================================================================
class TaskListCycleAdmin(admin.ModelAdmin):
    """Admin for daily task list cycles"""
    inlines = [TaskListCycleMembershipInline]

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
admin.site.register([models.TaskList],TaskListAdmin)
admin.site.register([models.TaskListItem],TaskListItemAdmin)
admin.site.register([models.TaskListItemUnitInfo],TaskListItemInfoAdmin)
admin.site.register([models.UnitTaskLists],UnitTaskListAdmin)

admin.site.register([models.TaskListCycle],TaskListCycleAdmin)