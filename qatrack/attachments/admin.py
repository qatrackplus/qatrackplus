from django import forms
from django.contrib import admin
from django.utils.translation import ugettext as _, ugettext_lazy as _l

from .models import Attachment


class AttachmentAdmin(admin.ModelAdmin):

    list_display = ("get_label", "owner", "type", "attachment", "comment",)

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
