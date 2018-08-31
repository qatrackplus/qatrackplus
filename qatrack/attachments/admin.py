from django import forms
from django.conf import settings
from django.contrib import admin
from django.forms.utils import ErrorList, ValidationError
from django.utils.translation import ugettext as _, ugettext_lazy as _l

from .models import Attachment
from qatrack.qa import models as qa_models
from qatrack.service_log import models as sl_models


class AjaxModelChoiceField(forms.ModelChoiceField):
    def __init__(self, model_class, *args, **kwargs):
        queryset = model_class.objects.none()
        super(AjaxModelChoiceField, self).__init__(queryset, *args, **kwargs)
        self.model_class = model_class

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            key = self.to_field_name or 'pk'
            value = self.model_class.objects.get(**{key: value})
        except (ValueError, self.queryset.model.DoesNotExist):
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
        return value


class AttachmentAdminForm(forms.ModelForm):

    test = AjaxModelChoiceField(qa_models.Test, required=False, label=_('Test'))
    testlist = AjaxModelChoiceField(qa_models.TestList, required=False, label=_('Test List'))
    testlistcycle = AjaxModelChoiceField(qa_models.TestListCycle, required=False, label=_('Test List Cycle'))
    testinstance = AjaxModelChoiceField(qa_models.TestInstance, required=False, label=_('Test Instance'))
    testlistinstance = AjaxModelChoiceField(qa_models.TestListInstance, required=False, label=_('Test List Instance'))
    serviceevent = AjaxModelChoiceField(sl_models.ServiceEvent, required=False, label=_('Service Event'))

    class Meta:
        model = Attachment
        fields = '__all__'

    class Media:
        js = (
            settings.STATIC_URL + 'jquery/js/jquery.min.js',
            settings.STATIC_URL + 'select2/js/select2.js',
            settings.STATIC_URL + 'js/attachment_admin.js'
        )
        css = {
            'all': (
                settings.STATIC_URL + "qatrack_core/css/admin.css",
                settings.STATIC_URL + "select2/css/select2.css",
            ),
        }

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None, initial=None, error_class=ErrorList,
                 label_suffix=None, empty_permitted=False, instance=None, use_required_attribute=None):
        super().__init__(data=data, files=files, auto_id=auto_id, prefix=prefix, initial=initial, error_class=error_class,
                         label_suffix=label_suffix, empty_permitted=empty_permitted, instance=instance, use_required_attribute=use_required_attribute)

        if self.instance.id:
            if self.instance.test:
                self.fields['test'].choices = (('', '--------'),) + tuple(((t.id, '(' + str(t.id) + ') ' + t.name) for t in qa_models.Test.objects.filter(pk=self.instance.test_id)))
                self.initial['test'] = self.instance.test_id
            if self.instance.testlist:
                self.fields['testlist'].choices = (('', '--------'),) + tuple(((tl.id, '(' + str(tl.id) + ') ' + tl.name) for tl in qa_models.TestList.objects.filter(pk=self.instance.testlist_id)))
                self.initial['testlist'] = self.instance.testlist_id
            if self.instance.testlistcycle:
                self.fields['testlistcycle'].choices = (('', '--------'),) + tuple(((tlc.id, '(' + str(tlc.id) + ') ' + tlc.name) for tlc in qa_models.TestListCycle.objects.filter(pk=self.instance.testlistcycle_id)))
                self.initial['testlistcycle'] = self.instance.testlistcycle_id
            if self.instance.testinstance:
                self.fields['testinstance'].choices = (('', '--------'),) + tuple(((ti.id, '(' + str(ti.id) + ') ' + ti.unit_test_info.test.name) for ti in qa_models.TestInstance.objects.filter(pk=self.instance.testinstance_id)))
                self.initial['testinstance'] = self.instance.testinstance_id
            if self.instance.testlistinstance:
                self.fields['testlistinstance'].choices = (('', '--------'),) + tuple(((tli.id, '(' + str(tli.id) + ') ' + tli.test_list.name) for tli in qa_models.TestListInstance.objects.filter(pk=self.instance.testlistinstance_id)))
                self.initial['testlistinstance'] = self.instance.testlistinstance_id
            if self.instance.serviceevent:
                self.fields['serviceevent'].choices = (('', '--------'),) + tuple(((se.id, '(' + str(se.id) + ') ' + se.service_status.name) for se in sl_models.ServiceEvent.objects.filter(pk=self.instance.serviceevent_id)))
                self.initial['serviceevent'] = self.instance.serviceevent_id


class AttachmentAdmin(admin.ModelAdmin):

    list_display = ("get_label", "owner", "type", "attachment", "comment",)
    form = AttachmentAdminForm

    def save_model(self, request, obj, form, change):
        """set user and modified date time"""
        if not obj.pk:
            obj.created_by = request.user

        super(AttachmentAdmin, self).save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super(AttachmentAdmin, self).get_queryset(request)
        qs = qs.select_related(*Attachment.OWNER_MODELS)
        return qs

    def get_label(self, obj):
        return obj.label or _("Unlabeled")
    get_label.short_description = _l("Label")


class SaveInlineAttachmentUserMixin(object):
    """A Mixin to save the user who added attachment in admin

    Set editable=False on the created_by and modified_by model you
    want to use this for.
    """

    def save_formset(self, request, form, formset, change):
        if formset.model._meta.model_name.lower() != "attachment":
            return super(SaveInlineAttachmentUserMixin, self).save_formset(request, form, formset, change)

        instances = formset.save(commit=False)
        for instance in instances:
            instance.created_by = request.user
            instance.save()

        for obj in formset.deleted_objects:
            obj.delete()

        formset.save_m2m()


class AttachmentInlineForm(forms.ModelForm):

    class Meta:
        model = Attachment
        exclude = ("created_by",)
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2}),
        }


class AttachmentInline(admin.TabularInline):
    model = Attachment
    form = AttachmentInlineForm


def get_attachment_inline(model):

    class cls(AttachmentInline):

        fields = ["attachment", "comment", model]
        raw_id_fields = (model, )

    return cls


admin.site.register([Attachment], AttachmentAdmin)
