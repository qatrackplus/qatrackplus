import datetime

import django.forms as forms
import django.db

from django.utils.translation import ugettext as _
from django.contrib import admin

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
        #obj.save()

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


class ReferenceInline(admin.TabularInline):
    model = models.Reference

#============================================================================
class TaskListItemInfoForm(forms.ModelForm):
    reference_value = forms.FloatField(
        label=_("Update current reference value"),
        help_text=_("For Yes/No tests, enter 1 for Yes and 0 for No"),
    )
    reference_type = forms.ChoiceField(choices=models.Reference.TYPE_CHOICES)

    #----------------------------------------------------------------------
    def clean(self):
        """make sure valid numbers are entered for boolean data"""
        print self.cleaned_data
        if "reference_value" not in self.cleaned_data:
            return self.cleaned_data
        ref_value = self.cleaned_data["reference_value"]
        ref_type = self.cleaned_data["reference_type"]

        if ref_type == models.Reference.BOOLEAN:
            if int(ref_value) not in (0,1):
                raise forms.ValidationError(_("Yes/No values must be 0 or 1"))

        return self.cleaned_data

    #tolerance_type = forms.ChoiceField(
        #help_text=_("Select whether this will be an absolute or relative tolerance criteria"),
        #choices=TYPE_CHOICES,
    #)
    #act_low = forms.FloatField(label=_("Lower Action Level"))
    #tol_low = forms.FloatField(label=_("Lower Tolerance Level"))
    #tol_high = forms.FloatField(label=_("Upper Tolerance Level"))
    #act_high = forms.FloatField(label=_("Upper Action Level"))

    class Meta:
        model = models.TaskListItemInfo


class TaskListItemInfoAdmin(admin.ModelAdmin):
    """"""
    form = TaskListItemInfoForm
    fields = (
        "unit", "task_list_item",
        "reference", "tolerance",
        "reference_value", "reference_type",
        #"tolerance_type", "act_low", "tol_low", "tol_high","act_high"
    )
    list_display = ["task_list_item", "unit", "reference", "tolerance"]
    list_filter = ["task_list_item","unit"]
    readonly_fields = ("task_list_item","unit","reference")

    def save_model(self, request, item_info, form, change):
        ref = models.Reference(
            value=form["reference_value"].value(),
            ref_type = form["reference_type"].value(),
            created_by = request.user,
            modified_by = request.user,
            name = "%s %s ref" % (item_info.unit.name,item_info.task_list_item.name)
        )
        ref.save()
        item_info.reference = ref

        #tolerances = ("act_low", "tol_low", "tol_high", "act_high")
        #kwargs = dict([(x,form[x]) for x in tolerances])
        #kwargs["type"] = forms["tolerance_type"],
        #kwargs["name"] = "%s %s
        #tolerance = models.Tolerance(
            #act_low = form["act_low"].value(),
            #tol_low = form["tol_low"].value(),
            #tol_high =

        #)
        super(TaskListItemInfoAdmin,self).save_model(request,item_info,form,change)

#============================================================================
class TaskListAdmin(SaveUserMixin, admin.ModelAdmin):
    prepopulated_fields =  {'slug': ('name',)}
    list_display = (title_case_name, "modified", "modified_by", "active")
    filter_horizontal= ("task_list_items", "sublists", )

    #inlines = [TaskListMembershipInline]
    #exclude = ("task_list_items", )

    class Media:
        js = (
            settings.STATIC_URL+"js/jquery-1.7.1.min.js",
            settings.STATIC_URL+"js/jquery-ui.min.js",
            settings.STATIC_URL+"js/collapsed_stacked_inlines.js",
            settings.STATIC_URL+"js/m2m_drag_admin.js",
        )

#============================================================================
class TaskListItemAdminForm(forms.ModelForm):
    """custom tasklistitem form to ensure valid shortname to be used in Python snippets"""
    VARIABLE_RE = re.compile("^[a-zA-Z_]+[0-9a-zA-Z_]*")
    #----------------------------------------------------------------------
    def clean_short_name(self):
        """replace any dashes in short_name (short_name is an autogenerated slug field) with underscores"""
        short_name = self.cleaned_data["short_name"]
        if not self.VARIABLE_RE.match(short_name):
            raise forms.ValidationError(
                _("Short names must contain only letters, numbers and underscores and start with a ltter or underscore")
            )
        return short_name

#============================================================================
class TaskListItemAdmin(SaveUserMixin, admin.ModelAdmin):
    form = TaskListItemAdminForm
    list_display = ["name","category", "task_type", "modified", "modified_by","set_references"]
    #filter_horizontal = ("units",)

    #----------------------------------------------------------------------
    def save_related(self, request, form, formsets, change):
        """create item info if just being created"""
        super(TaskListItemAdmin, self).save_related(request, form, formsets, change)

        #new = not change
        #if new:
        #    for unit in form.instance.units.all():
        #        item_info = models.TaskListItemInfo(unit=unit, task_list_item=form.instance)
        #        item_info.save()


class UnitTaskListAdmin(admin.ModelAdmin):
    readonly_fields = ("unit","frequency",)
    filter_horizontal = ("task_lists",)
    list_display = ["name", "unit", "frequency"]
    list_filter = ["unit", "frequency"]
    #----------------------------------------------------------------------
    def save_related(self, request, form, formsets, change):
        """create item info if just being created"""
        super(UnitTaskListAdmin, self).save_related(request, form, formsets, change)
        return
        unit_task_list = form.instance()
        for task_list in unit_task_list.task_lists.all():
            task_list_items = task_list.task_list_items.all()
            for task_list_item in task_list_items:
                models.TaskListItemInfo.objects.get_or_create(
                    unit = unit,
                    task_list_item = task_list_item
                )

admin.site.register([models.Tolerance], BasicSaveUserAdmin)
admin.site.register([models.Category], CategoryAdmin)
admin.site.register([models.TaskList],TaskListAdmin)
admin.site.register([models.TaskListItem],TaskListItemAdmin)
admin.site.register([models.TaskListItemInfo],TaskListItemInfoAdmin)
admin.site.register([models.UnitTaskLists],UnitTaskListAdmin)
