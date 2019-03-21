from itertools import groupby
import re

from admin_views.admin import AdminViews
from django import VERSION
from django.apps import apps
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import options, widgets
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
import django.forms as forms
from django.shortcuts import HttpResponseRedirect, redirect, render
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _l
from dynamic_raw_id.admin import DynamicRawIDMixin
from dynamic_raw_id.widgets import DynamicRawIDWidget

from qatrack.attachments.admin import (
    SaveInlineAttachmentUserMixin,
    get_attachment_inline,
)
import qatrack.qa.models as models
from qatrack.qa.utils import format_qa_value
from qatrack.units.models import Unit

admin.site.disable_action("delete_selected")


class SaveUserMixin(object):
    """A Mixin to save creating user and modifiying user

    Set editable=False on the created_by and modified_by model you
    want to use this for.
    """

    def save_model(self, request, obj, form, change):
        """set user and modified date time"""
        if not obj.pk:
            obj.created_by = request.user
            obj.created = timezone.now()
        obj.modified_by = request.user

        super(SaveUserMixin, self).save_model(request, obj, form, change)


class BasicSaveUserAdmin(SaveUserMixin, admin.ModelAdmin):
    """manage reference values for tests"""


class CategoryAdmin(admin.ModelAdmin):
    """QC categories admin"""
    prepopulated_fields = {'slug': ('name',)}
    list_display = (
        "name",
        "description",
    )


class TestInfoForm(forms.ModelForm):

    reference_value = forms.FloatField(label=_("New reference value"), required=False,)
    reference_set_by = forms.CharField(label=_("Set by"), required=False)
    reference_set = forms.CharField(label=_("Date"), required=False)
    test_type = forms.CharField(required=False)
    comment = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = models.UnitTestInfo
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(TestInfoForm, self).__init__(*args, **kwargs)
        readonly = ("test_type", "reference_set_by", "reference_set",)

        for f in readonly:
            self.fields[f].widget.attrs['readonly'] = "readonly"
            self.fields[f].widget.attrs['disabled'] = "disabled"

        if self.instance:
            tt = self.instance.test.type
            i = [x[0] for x in models.TEST_TYPE_CHOICES].index(tt)
            self.fields["test_type"].initial = models.TEST_TYPE_CHOICES[i][1]

            if tt == models.BOOLEAN:
                self.fields["reference_value"].widget = forms.Select(choices=[("", "---"), (0, "No"), (1, "Yes")])
                tolf = self.fields['tolerance']
                tolf.queryset = tolf.queryset.filter(type=models.BOOLEAN)
                for p in ['add', 'change', 'delete']:
                    setattr(tolf.widget, 'can_%s_related' % p, False)
                if not self.instance.tolerance:
                    self.initial["tolerance"] = models.Tolerance.objects.get(
                        type=models.BOOLEAN,
                        bool_warning_only=False,
                    )
            elif tt == models.MULTIPLE_CHOICE or self.instance.test.is_string_type():
                self.fields["reference_value"].widget = forms.HiddenInput()
                qs = self.fields['tolerance'].queryset.filter(type=models.MULTIPLE_CHOICE)
                self.fields['tolerance'].queryset = qs
            else:
                qs = self.fields['tolerance'].queryset.exclude(type=models.MULTIPLE_CHOICE)
                self.fields['tolerance'].queryset = qs

            if tt != models.MULTIPLE_CHOICE and self.instance.reference:
                if tt == models.BOOLEAN:
                    val = int(self.instance.reference.value)
                else:
                    val = self.instance.reference.value
                self.initial["reference_value"] = val

            if self.instance.reference:
                les = LogEntry.objects.filter(
                    Q(change_message__contains="reference_value") | Q(change_message__contains="tolerance"),
                    content_type_id=ContentType.objects.get_for_model(self.instance).pk,
                    object_id=self.instance.pk,
                    action_flag=CHANGE,
                ).order_by("-action_time")
                if les:
                    self.initial["reference_set_by"] = "%s" % (les[0].user)
                    self.initial["reference_set"] = "%s" % (timezone.localtime(les[0].action_time))

    def clean(self):
        """make sure valid numbers are entered for boolean data"""

        if (self.instance.test.type == models.MULTIPLE_CHOICE or
                self.instance.test.is_string_type()) and self.cleaned_data.get("tolerance"):
            if self.cleaned_data["tolerance"].type != models.MULTIPLE_CHOICE:
                raise forms.ValidationError(
                    _("You can't use a non-multiple choice tolerance with a multiple choice or string test")
                )
        else:
            if "reference_value" not in self.cleaned_data:
                return self.cleaned_data

            ref_value = self.cleaned_data["reference_value"]

            tol = self.cleaned_data.get("tolerance")
            if tol is not None:
                if ref_value == 0 and tol.type == models.PERCENT:
                    raise forms.ValidationError(
                        _("Percentage based tolerances can not be used with reference value of zero (0)")
                    )

        return self.cleaned_data


def test_name(obj):
    return obj.test.name
test_name.admin_order_field = "test__name"  # noqa: E305


def test_type(obj):
    for tt, display in models.TEST_TYPE_CHOICES:
        if obj.test.type == tt:
            return display
test_type.admin_order_field = "test__type"  # noqa: E305


class SetMultipleReferencesAndTolerancesForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    contenttype = forms.CharField(widget=forms.HiddenInput, required=False)
    tolerance = forms.ModelChoiceField(queryset=models.Tolerance.objects.all())
    reference = forms.CharField(max_length=255)


# see http://stackoverflow.com/questions/851636/default-filter-in-django-admin
class ActiveUnitTestInfoFilter(admin.SimpleListFilter):

    NOTACTIVE = 'notactive'
    ACTIVE = 'active'

    title = _('Active Unit Assignments')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'activeassignment'

    def lookups(self, request, model_admin):
        return (
            (None, _('At Least One Active Unit Assignment')),
            (self.NOTACTIVE, _('No Active Unit Assignments')),
            ('all', _('All')),
        )

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }

    # TODO fix this
    def queryset(self, request, qs):
        if self.value() in (self.NOTACTIVE,):
            return models.UnitTestInfo.objects.inactive(qs)
        elif self.value() is None:
            return models.UnitTestInfo.objects.active(qs)
        return qs


class UnitTestInfoAdmin(AdminViews, admin.ModelAdmin):

    admin_views = (
        ('Copy References & Tolerances', 'redirect_to'),
    )

    actions = ['set_multiple_references_and_tolerances']
    form = TestInfoForm
    # model = models.UnitTestInfo
    fields = (
        "unit",
        "test",
        "test_type",
        "reference",
        "reference_set_by",
        "reference_set",
        "tolerance",
        "reference_value",
        "comment",
        "history",
    )

    list_display = [test_name, "unit", test_type, "reference", "tolerance"]
    list_filter = [ActiveUnitTestInfoFilter, "unit", "test__category", "test__testlistmembership__test_list"]
    readonly_fields = ("reference", "test", "unit", "history")
    search_fields = ("test__name", "test__slug", "unit__name")
    # list_select_related = ['reference', 'tolerance', 'test', 'unit']

    def redirect_to(self, *args, **kwargs):
        return redirect(reverse("qa_copy_refs_and_tols"))

    def get_queryset(self, *args, **kwargs):
        """just display active ref/tols"""
        qs = models.UnitTestInfo.objects.select_related(
            "reference",
            "tolerance",
            "unit",
            "test",
        )

        return qs

    def has_add_permission(self, request):
        """unittestinfo's are created automatically"""
        return False

    def form_valid(self, request, queryset, form):

        if form.is_valid():
            reference = form.cleaned_data['reference']
            tolerance = form.cleaned_data['tolerance']

            # Save the uti with the new references and tolerance
            # TODO: Combine with save method: save_model ?
            for uti in queryset:
                if uti.test.type != models.MULTIPLE_CHOICE:
                    if uti.test.type == models.BOOLEAN:
                        ref_type = models.BOOLEAN
                        if reference == 'True' or reference == 1:
                            reference = 1
                        else:
                            reference = 0
                    else:
                        ref_type = models.NUMERICAL
                    if reference not in ("", None):
                        if not(uti.reference and uti.reference.value == float(reference)):
                            try:
                                ref = models.Reference.objects.get(value=reference, type=ref_type)
                            except models.Reference.DoesNotExist:
                                ref = models.Reference(
                                    value=reference,
                                    type=ref_type,
                                    created_by=request.user,
                                    modified_by=request.user,
                                    name="%s %s" % (uti.unit.name, uti.test.name)[:255]
                                )
                                ref.save()
                            uti.reference = ref
                    else:
                        uti.reference = None
                uti.tolerance = tolerance
                uti.save()

            messages.success(request, "%s tolerances and references have been saved successfully." % queryset.count())
            return HttpResponseRedirect(request.get_full_path())

    def set_multiple_references_and_tolerances(self, request, queryset):

        testtypes = set(queryset.values_list('test__type', flat=True).distinct())

        has_upload = models.UPLOAD in testtypes
        has_bool = models.BOOLEAN in testtypes
        has_num = len(set(models.NUMERICAL_TYPES) & testtypes) > 0
        has_str = len(set(models.STRING_TYPES) & testtypes) > 0

        # check if tests have the same type of tolerance, else return with error message
        if [has_bool, has_num, has_str].count(True) > 1 or has_upload:
            messages.error(
                request,
                (
                    "Invalid combination of tests selected.  Tests must be either all "
                    "Numerical types, all String types, or all Boolean"
                )
            )
            return HttpResponseRedirect(request.get_full_path())

        if 'apply' in request.POST:
            form = SetMultipleReferencesAndTolerancesForm(request.POST)
        else:
            form = SetMultipleReferencesAndTolerancesForm(initial={'contenttype': None})

        # if selected tests are NOT multiple choice or boolean,
        # select all the tolerances which are NOT multiple choice or boolean
        if has_num:
            tolerances = models.Tolerance.objects.exclude(type="multchoice")
            form.fields["tolerance"].queryset = tolerances

        # if selected tests are multiple choice select all the tolerances which are multiple choice
        elif has_str:
            tolerances = models.Tolerance.objects.filter(type="multchoice")
            form.fields["contenttype"].initial = 'multchoice'
            form.fields["tolerance"].queryset = tolerances
            form.fields["reference"].required = False
            form.fields["reference"].widget = forms.HiddenInput()

        # if selected tests are boolean select all the tolerances which are boolean
        elif has_bool:
            tolerances = models.Tolerance.objects.filter(type="boolean")
            form.fields["contenttype"].initial = 'boolean'
            form.fields["reference"].widget = forms.NullBooleanSelect()
            form.fields["tolerance"].required = False
            form.fields["tolerance"].queryset = tolerances

        if 'apply' in request.POST and form.is_valid():
            return self.form_valid(request, queryset, form)
        else:
            context = {
                'queryset': queryset,
                'form': form,
                'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
            }
            return render(request, 'admin/qa/unittestinfo/set_multiple_refs_and_tols.html', context)

    set_multiple_references_and_tolerances.short_description = "Set multiple references and tolerances"

    def save_model(self, request, test_info, form, change):
        """create new reference when user updates value"""

        if any(k in form.changed_data for k in ['comment', 'reference_value', 'tolerance']):
            if form.instance and form.instance.pk:
                old = models.UnitTestInfo.objects.get(pk=form.instance.pk)
                models.UnitTestInfoChange.objects.create(
                    unit_test_info=old,
                    comment=form.cleaned_data["comment"],
                    reference=old.reference,
                    reference_changed=old.reference != form.instance.reference,
                    tolerance=old.tolerance,
                    tolerance_changed=old.tolerance != form.instance.tolerance,
                    changed_by=request.user,
                )

        if form.instance.test.type != models.MULTIPLE_CHOICE:

            if form.instance.test.type == models.BOOLEAN:
                ref_type = models.BOOLEAN
            else:
                ref_type = models.NUMERICAL
            val = form["reference_value"].value()
            if val not in ("", None):
                if not(test_info.reference and test_info.reference.value == float(val)):
                    try:
                        ref = models.Reference.objects.filter(value=val, type=ref_type)[0]
                    except IndexError:
                        ref = models.Reference(
                            value=val,
                            type=ref_type,
                            created_by=request.user,
                            modified_by=request.user,
                            name="%s %s" % (test_info.unit.name, test_info.test.name)[:255]
                        )
                        ref.save()
                    test_info.reference = ref
            else:
                test_info.reference = None

        super(UnitTestInfoAdmin, self).save_model(request, test_info, form, change)

    def lookup_allowed(self, lookup, value):
        if lookup in ['test__testlistmembership__test_list__id__exact']:
            return True
        return super(UnitTestInfoAdmin, self).lookup_allowed(lookup, value)

    @mark_safe
    def history(self, obj):
        hist = list(obj.unittestinfochange_set.select_related(
            "reference",
            "tolerance",
            "changed_by",
        ).order_by("-changed"))
        old_news = zip([obj] + hist[1:], hist)
        return loader.render_to_string('admin/unittestinfo_history.html', {'history': old_news})


class TestListAdminForm(forms.ModelForm):
    """Form for handling validation of TestList creation/editing"""

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        dup = models.TestList.objects.exclude(pk=self.instance.pk).filter(slug=slug)
        if dup:
            raise forms.ValidationError("A test list with the slug '%s' already exists in the database" % slug)
        return slug

    def clean(self):
        retest = re.compile("^testlistmembership_set-\d+-test$")
        test_ids = [x[1] for x in self.data.items() if retest.findall(x[0]) and x[1]]
        slugs = list(models.Test.objects.filter(id__in=test_ids).values_list("slug", flat=True))

        rechild = re.compile("^children-\d+-child$")
        child_ids = [x[1] for x in self.data.items() if rechild.findall(x[0]) and x[1]]
        for tl in models.TestList.objects.filter(id__in=child_ids):
            slugs.extend(tl.all_tests().values_list("slug", flat=True))

        duplicates = list(set([sn for sn in slugs if slugs.count(sn) > 1]))
        if duplicates:
            msg = (
                "The following test macro names are duplicated (either in this test list or one of its sublists) :: " +
                ",".join(duplicates)
            )
            raise forms.ValidationError(msg)

        return self.cleaned_data


class TestListMembershipInlineFormSet(forms.models.BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        qs = kwargs["queryset"].filter(test_list=kwargs["instance"]).select_related("test")
        kwargs["queryset"] = qs
        super(TestListMembershipInlineFormSet, self).__init__(*args, **kwargs)


class SublistInlineFormSet(forms.models.BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        qs = kwargs["queryset"].filter(parent=kwargs["instance"])
        kwargs["queryset"] = qs
        super(SublistInlineFormSet, self).__init__(*args, **kwargs)

    def clean(self):
        """Make sure there are no duplicated slugs in a TestList"""
        super(SublistInlineFormSet, self).clean()

        if not hasattr(self, "cleaned_data"):
            # something else went wrong already
            return {}

        children = [f.instance.child for f in self.forms if hasattr(f.instance, 'child') and not f.cleaned_data["DELETE"]]  # noqa: E501
        if self.instance and self.instance in children:
            raise forms.ValidationError(
                "A test list can not be its own child. Please remove Sublist ID %d and try again" % (self.instance.pk)
            )

        return self.cleaned_data


def macro_name(obj):
    return obj.test.slug


class TestListMembershipForm(forms.ModelForm):

    model = models.TestListMembership

    def validate_unique(self):
        """skip unique validation.

        The uniqueness of ('test_list','test',) is already independently checked
        by the formset (looks for duplicate macro names).

        By making validate_unique here a null function, we eliminate a DB call
        per test list membership when saving test lists in the admin.
        """


class SublistForm(forms.ModelForm):

    model = models.Sublist

    def validate_unique(self):
        """skip unique validation.

        The uniqueness of ('test_list','test',) is already independently checked
        by the formset (looks for duplicate macro names).

        By making validate_unique here a null function, we eliminate a DB call
        per test list membership when saving test lists in the admin.
        """


class TestListMembershipInline(DynamicRawIDMixin, admin.TabularInline):

    model = models.TestListMembership
    formset = TestListMembershipInlineFormSet
    form = TestListMembershipForm
    extra = 5
    template = "admin/qa/testlistmembership/edit_inline/tabular.html"
    readonly_fields = (macro_name,)
    dynamic_raw_id_fields = ("test",)

    def label_for_value(self, value):  # TODO: is this called ever?
        try:
            name = self.test_names[value]
            return '&nbsp;<strong>%s</strong>' % escape(Truncator(name).words(14, truncate='...'))
        except (ValueError, KeyError):
            return ''

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        # copied from django.contrib.admin.wigets (and dynamic_raw_id admin.py)
        # so we can override the label_for_value function for the test raw id widget
        db = kwargs.get('using')
        if db_field.name == "test":
            rel = db_field.remote_field if VERSION[0] == 2 else db_field.rel
            widget = DynamicRawIDWidget(rel, self.admin_site)
            widget.label_for_value = self.label_for_value
            kwargs['widget'] = widget
            return db_field.formfield(**kwargs)
        elif db_field.name in self.dynamic_raw_id_fields:
            rel = db_field.remote_field if VERSION[0] == 2 else db_field.rel
            kwargs['widget'] = DynamicRawIDWidget(rel, self.admin_site)
            return db_field.formfield(**kwargs)
        elif db_field.name in self.raw_id_fields:
            kwargs['widget'] = widgets.ForeignKeyRawIdWidget(db_field.rel,
                                                             self.admin_site, using=db)
        elif db_field.name in self.radio_fields:
            kwargs['widget'] = widgets.AdminRadioSelect(attrs={
                'class': options.get_ul_class(self.radio_fields[db_field.name]),
            })
            kwargs['empty_label'] = db_field.blank and _('None') or None
        return db_field.formfield(**kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        # hacky method for getting test names so they don't need to be looked up again
        # in the label_for_value in contrib/admin/widgets.py
        if obj:
            self.test_names = dict(obj.tests.values_list("pk", "name"))
        else:
            self.test_names = {}
        return super(TestListMembershipInline, self).get_formset(request, obj, **kwargs)


class SublistInline(DynamicRawIDMixin, admin.TabularInline):

    model = models.Sublist
    fk_name = "parent"
    formset = SublistInlineFormSet
    form = SublistForm
    extra = 1
    template = "admin/qa/testlistmembership/edit_inline/tabular.html"
    dynamic_raw_id_fields = ("child",)

    def label_for_value(self, value):  # TODO: Is this called ever?
        try:
            name = self.test_list_names[value]
            return '&nbsp;<strong>%s</strong>' % escape(Truncator(name).words(14, truncate='...'))
        except (ValueError, KeyError):
            return ''

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        # copied from django.contrib.admin.wigets so we can override the label_for_value function
        # for the test raw id widget
        db = kwargs.get('using')
        if db_field.name == "child":
            rel = db_field.remote_field if VERSION[0] == 2 else db_field.rel
            widget = DynamicRawIDWidget(rel, self.admin_site)
            widget.label_for_value = self.label_for_value
            kwargs['widget'] = widget
            return db_field.formfield(**kwargs)

        elif db_field.name in self.dynamic_raw_id_fields:
            rel = db_field.remote_field if VERSION[0] == 2 else db_field.rel
            kwargs['widget'] = DynamicRawIDWidget(rel, self.admin_site)
            return db_field.formfield(**kwargs)

        elif db_field.name in self.raw_id_fields:
            kwargs['widget'] = widgets.ForeignKeyRawIdWidget(db_field.rel,
                                                             self.admin_site, using=db)
        elif db_field.name in self.radio_fields:
            kwargs['widget'] = widgets.AdminRadioSelect(attrs={
                'class': options.get_ul_class(self.radio_fields[db_field.name]),
            })
            kwargs['empty_label'] = db_field.blank and _('None') or None
        return db_field.formfield(**kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        # hacky method for getting test names so they don't need to be looked up again
        # in the label_for_value in contrib/admin/widgets.py
        if obj:
            self.test_list_names = dict(obj.sublist_set.values_list("pk", "child__name"))
        else:
            self.test_list_names = {}
        return super(SublistInline, self).get_formset(request, obj, **kwargs)


class ActiveTestListFilter(admin.SimpleListFilter):

    NOACTIVEUTCS = 'noactiveutcs'
    HASACTIVEUTCS = 'hasactiveutcs'

    title = _('Active Unit Assignments')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'activeutcs'

    def lookups(self, request, model_admin):
        return (
            (self.NOACTIVEUTCS, _('No Active Unit Assignments')),
            (self.HASACTIVEUTCS, _('At Least One Active Unit Assignment')),
        )

    def queryset(self, request, qs):
        active_tl_ids = models.get_utc_tl_ids(active=True)
        active_sub_tl_ids = list(models.TestList.objects.filter(
            id__in=active_tl_ids, children__isnull=False
        ).values_list('children__child__id', flat=True).distinct())

        if self.value() == self.NOACTIVEUTCS:
            return qs.exclude(
                Q(id__in=active_tl_ids) |
                Q(id__in=active_sub_tl_ids)
            )
        elif self.value() == self.HASACTIVEUTCS:
            return qs.filter(
                Q(id__in=active_tl_ids) |
                Q(id__in=active_sub_tl_ids)
            )
        return qs


class UnitTestListFilter(admin.SimpleListFilter):

    title = _('Assigned to Unit')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'assignedtounit'

    def lookups(self, request, model_admin):
        return Unit.objects.values_list("pk", "name")

    def queryset(self, request, qs):

        if self.value():
            unit = Unit.objects.get(pk=self.value())
            unit_tl_ids = models.get_utc_tl_ids(units=[unit])
            return qs.filter(id__in=unit_tl_ids)

        return qs


class FrequencyTestListFilter(admin.SimpleListFilter):

    title = _('Assigned To Units by Frequency')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'assignedbyfreq'

    def lookups(self, request, model_admin):
        return models.Frequency.objects.values_list("pk", "name")

    def queryset(self, request, qs):

        if self.value():
            freq = models.Frequency.objects.get(pk=self.value())
            freq_tl_ids = models.get_utc_tl_ids(frequencies=[freq])
            return qs.filter(id__in=freq_tl_ids)

        return qs


class TestListAdmin(AdminViews, SaveUserMixin, SaveInlineAttachmentUserMixin, admin.ModelAdmin):

    admin_views = (
        ('Export Test Pack', 'export_testpack'),
        ('Import Test Pack', 'import_testpack'),
    )

    prepopulated_fields = {'slug': ('name',)}
    search_fields = ("name", "description", "slug",)
    filter_horizontal = ("tests", )

    actions = ['export_test_lists']
    list_display = ("name", "slug", "modified", "modified_by",)
    list_filter = [ActiveTestListFilter, UnitTestListFilter, FrequencyTestListFilter]

    form = TestListAdminForm
    inlines = [TestListMembershipInline, SublistInline, get_attachment_inline("testlist")]
    save_as = True

    class Media:
        js = (
            settings.STATIC_URL + "js/jquery-ui.init.js",
            settings.STATIC_URL + "js/jquery-ui.min.js",
            settings.STATIC_URL + "js/m2m_drag_admin_testlist.js",
            settings.STATIC_URL + "js/admin_description_editor.js",
            settings.STATIC_URL + "ace/ace.js",
        )

    def export_testpack(self, *args, **kwargs):
        return redirect(reverse("qa_export_testpack"))

    def import_testpack(self, *args, **kwargs):
        return redirect(reverse("qa_import_testpack"))


class TestForm(forms.ModelForm):

    class Meta:
        model = models.Test
        fields = '__all__'

    def clean(self):
        """if test already has some history don't allow for the test type to be changed"""

        cleaned_data = super().clean()

        test_type = cleaned_data.get("type")
        user_changing_type = self.instance.type != test_type
        has_history = models.TestInstance.objects.filter(unit_test_info__test=self.instance).exists()
        if user_changing_type and has_history:
            msg = (
                "You can't change the test type of a test that has already been performed. "
                "Revert to '%s' before saving."
            )
            ttype_index = [ttype for ttype, label in models.TEST_TYPE_CHOICES].index(self.instance.type)
            ttype_label = models.TEST_TYPE_CHOICES[ttype_index][1]
            self.add_error('type', forms.ValidationError(msg % ttype_label))

        if test_type not in models.NUMERICAL_TYPES:
            cleaned_data['formatting'] = ''
        else:
            fmt = cleaned_data.get('formatting')
            if fmt:
                try:
                    format_qa_value(123.4, fmt)
                except:  # noqa: E722
                    self.add_error("formatting", forms.ValidationError("Invalid numerical format"))

        return cleaned_data


class TestListMembershipFilter(admin.SimpleListFilter):
    NOMEMBERSHIPS = 'nomemberships'
    HASMEMBERSHIPS = 'hasmemberships'

    title = _('Test List Membership')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'tlmembership'

    def lookups(self, request, model_admin):
        return (
            (self.NOMEMBERSHIPS, _('No TestList Membership')),
            (self.HASMEMBERSHIPS, _('At Least One TestList Membership')),
        )

    def queryset(self, request, queryset):
        qs = queryset.annotate(tlcount=Count("testlistmembership"))
        if self.value() == self.NOMEMBERSHIPS:
            return qs.filter(tlcount=0)
        elif self.value() == self.HASMEMBERSHIPS:
            return qs.filter(tlcount__gt=0)
        return qs


class TestAdmin(SaveUserMixin, SaveInlineAttachmentUserMixin, admin.ModelAdmin):

    inlines = [get_attachment_inline("test")]
    list_display = ["name", "slug", "category", "type", 'obj_created', 'obj_modified']
    list_filter = ["category", "type", TestListMembershipFilter, "testlistmembership__test_list"]
    search_fields = ["name", "slug", "category__name"]
    save_as = True

    form = TestForm

    class Media:
        js = (
            settings.STATIC_URL + "js/jquery-1.7.1.min.js",
            settings.STATIC_URL + "js/test_admin.js",
            settings.STATIC_URL + "js/admin_description_editor.js",
            settings.STATIC_URL + "ace/ace.js",
            settings.STATIC_URL + "select2/js/select2.js",
        )
        css = {
            'all': (
                settings.STATIC_URL + "qatrack_core/css/admin.css",
                settings.STATIC_URL + "select2/css/select2.css",
            ),
        }

    def save_model(self, request, obj, form, change):
        if 'calculation_procedure' in form.changed_data:
            cp = obj.calculation_procedure or ""
            if "pyplot" in cp or "pylab" in cp:
                warning = (
                    "Warning: Instead of using pyplot or pylab, it is recommended that you use "
                    "the object oriented interface to matplotlib."
                )
                messages.add_message(request, messages.WARNING, warning)

        if obj.procedure:
            if not obj.procedure.startswith("http"):
                warning = "Warning: test procedure links should usually begin with http:// or https://"
                messages.add_message(request, messages.WARNING, warning)

        super(TestAdmin, self).save_model(request, obj, form, change)

    @mark_safe
    def obj_created(self, obj):
        fmt = '<abbr title="Created by %s">%s</abbr>'
        return fmt % (obj.created_by, obj.created.strftime(settings.INPUT_DATE_FORMATS[0]))
    obj_created.admin_order_field = "created"
    obj_created.short_description = "Created"

    @mark_safe
    def obj_modified(self, obj):
        fmt = '<abbr title="Modified by %s">%s</abbr>'
        return fmt % (obj.modified_by, obj.modified.strftime(settings.INPUT_DATE_FORMATS[0]))
    obj_modified.admin_order_field = "modified"
    obj_modified.short_description = "Modified"


def unit_name(obj):
    return obj.unit.name
unit_name.admin_order_field = "unit__name"  # noqa: E305
unit_name.short_description = "Unit"


def freq_name(obj):
    return obj.frequency.name if obj.frequency else "Ad Hoc"
freq_name.admin_order_field = "frequency__name"  # noqa: E305
freq_name.short_description = "Frequency"


def assigned_to_name(obj):
    return obj.assigned_to.name
assigned_to_name.admin_order_field = "assigned_to__name"  # noqa: E305
assigned_to_name.short_description = "Assigned To"


class UnitFilter(admin.SimpleListFilter):

    title = _('Unit')
    parameter_name = "unitfilter"

    def lookups(self, request, model_admin):
        return models.Unit.objects.values_list('pk', 'name')

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(unit=self.value())

        return queryset


class FrequencyFilter(admin.SimpleListFilter):

    title = _('Frequency')
    parameter_name = "freqfilter"

    def lookups(self, request, model_admin):
        return models.Frequency.objects.values_list('pk', 'name')

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(frequency=self.value())

        return queryset


class AssignedToFilter(admin.SimpleListFilter):

    title = _('Assigned To')
    parameter_name = "assignedtoname"

    def lookups(self, request, model_admin):
        return models.Group.objects.values_list('pk', 'name')

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(assigned_to=self.value())

        return queryset


class ActiveFilter(admin.SimpleListFilter):

    title = _('Active')
    parameter_name = "activefilter"

    def lookups(self, request, model_admin):
        return (
            (1, _('Active')),
            (0, _('Not active'))
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(active=self.value())

        return queryset


class UnitTestCollectionForm(forms.ModelForm):

    unit = forms.TypedChoiceField(label=_l("Unit"), coerce=int)

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        def site_unit_type(u):
            return "%s :: %s" % (u.site.name if u.site else "Other", u.type.name)

        def site_unit_name(u):
            return "%s :: %s" % (u.site.name if u.site else "Other", u.name)

        units = Unit.objects.select_related("site", "type").order_by("site__name", "type__name", "name")
        choices = [(ut, list(us)) for (ut, us) in groupby(units, key=site_unit_type)]
        choices = [(ut, [(u.id, site_unit_name(u)) for u in us]) for (ut, us) in choices]
        choices = [("", "---------")] + choices

        self.fields['unit'].choices = choices

        freq = self.fields['frequency']
        freq.queryset = freq.queryset.order_by("name")

    def _clean_readonly(self, f):
        data = self.cleaned_data.get(f, None)
        if f == "unit" and data:
            data = Unit.objects.get(pk=data)

        if self.instance.pk and f in self.changed_data:
            if f == "object_id":
                orig = str(self.instance.tests_object)
            else:
                orig = getattr(self.instance, f)
            err_msg = (
                "To prevent data loss, you can not change the Unit, TestList or TestListCycle "
                "of a UnitTestCollection after it has been created. The original value was: %s"
            ) % orig
            self.add_error(f, err_msg)

        return data

    def clean_content_type(self):
        return self._clean_readonly("content_type")

    def clean_object_id(self):
        return self._clean_readonly("object_id")

    def clean_unit(self):
        if self.instance.pk:
            return self._clean_readonly("unit")

        unit = self.cleaned_data.get('unit')
        if unit:
            return Unit.objects.get(pk=unit)


class UnitTestCollectionAdmin(admin.ModelAdmin):
    # readonly_fields = ("unit","frequency",)
    filter_horizontal = ("visible_to",)
    list_display = ['name', unit_name, freq_name, assigned_to_name, "active"]
    list_filter = [UnitFilter, FrequencyFilter, AssignedToFilter, ActiveFilter]
    search_fields = ['name', "unit__name", "frequency__name"]
    change_form_template = "admin/treenav/menuitem/change_form.html"
    list_editable = ["active"]
    save_as = True
    form = UnitTestCollectionForm

    class Media:
        js = (
            settings.STATIC_URL + "js/jquery-ui.init.js",
            settings.STATIC_URL + "js/jquery-ui.min.js",
            settings.STATIC_URL + "js/select2.min.js",
        )

    def get_queryset(self, *args, **kwargs):
        qs = super(UnitTestCollectionAdmin, self).get_queryset(*args, **kwargs)
        return qs.select_related(
            "unit",
            "frequency",
            "assigned_to"
        )


class TestListCycleMembershipInline(DynamicRawIDMixin, admin.TabularInline):

    model = models.TestListCycleMembership
    dynamic_raw_id_fields = ("test_list",)


class TestListCycleAdmin(SaveUserMixin, SaveInlineAttachmentUserMixin, admin.ModelAdmin):
    """Admin for daily test list cycles"""
    inlines = [TestListCycleMembershipInline, get_attachment_inline("testlistcycle")]
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ("name", "slug",)
    list_display = ["name", "all_lists"]

    class Media:
        js = (
            settings.STATIC_URL + "js/jquery-ui.init.js",
            settings.STATIC_URL + "js/jquery-ui.min.js",
            settings.STATIC_URL + "js/collapsed_stacked_inlines.js",
            settings.STATIC_URL + "js/m2m_drag_admin.js",
            settings.STATIC_URL + "js/admin_description_editor.js",
            settings.STATIC_URL + "ace/ace.js",
        )

    def all_lists(self, obj):
        return ', '.join("%s: %s" % x for x in enumerate(obj.all_lists().values_list("name", flat=True)))

    def get_queryset(self, request):
        qs = super(TestListCycleAdmin, self).get_queryset(request)
        return qs.prefetch_related("test_lists")


class FrequencyAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    model = models.Frequency
    fields = (
        "name",
        "slug",
        "window_start",
        "window_end",
        "recurrences",
    )

    list_display = (
        "name",
        "get_recurrences",
        "window_start",
        "window_end",
    )

    class Media:
        js = (
            settings.STATIC_URL + "js/jquery-1.7.1.min.js",
            settings.STATIC_URL + "js/jquery-ui.min.js",
            settings.STATIC_URL + "moment/js/moment.min.js",
            settings.STATIC_URL + "moment/js/moment-timezone-with-data.min.js",
            settings.STATIC_URL + "rrule/js/rrule-tz.min.js",
            settings.STATIC_URL + "d3/js/d3-3.5.6.min.js",
            settings.STATIC_URL + "cal-heatmap/js/cal-heatmap.min.js",
            settings.STATIC_URL + "js/frequency_admin.js",
        )
        css = {
            'all': [settings.STATIC_URL + "cal-heatmap/css/cal-heatmap.css"],
        }

    def save_model(self, request, obj, form, change):
        """set user and modified date time"""
        if not obj.pk:
            from_ = timezone.datetime(2012, 1, 1, tzinfo=timezone.get_current_timezone())
            obj.recurrences.dtstart = from_
        super().save_model(request, obj, form, change)

    @mark_safe
    def get_recurrences(self, obj):
        rules = str(obj.recurrences).replace("RRULE:", "").split("\n")[1:]
        processed = []
        for rule in rules:
            if rule.startswith("EXDATE") or rule.startswith("RDATE"):
                date = rule.split(":")[-1]
                date = "%s-%s-%s" % (date[:4], date[4:6], date[6:8])
                inc = "Exclude" if rule.startswith("EXDATE") else "Include"
                rule = "%s: %s" % (inc, date)

            processed.append(rule)

        return "<br/>".join(processed)
    get_recurrences.short_description = "Recurrences"


class StatusAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    model = models.TestInstanceStatus

    list_display = (
        'name',
        'is_default',
        'requires_review',
        'valid',
        'get_colour',
    )

    class Media:
        js = (
            settings.STATIC_URL + "jquery/js/jquery.min.js",
            settings.STATIC_URL + "colorpicker/js/bootstrap-colorpicker.min.js",
            settings.STATIC_URL + "qatrack_core/js/admin_colourpicker.js",

        )
        css = {
            'all': (
                settings.STATIC_URL + "bootstrap/css/bootstrap.min.css",
                settings.STATIC_URL + "colorpicker/css/bootstrap-colorpicker.min.css",
                settings.STATIC_URL + "qatrack_core/css/admin.css",
            ),
        }

    @mark_safe
    def get_colour(self, obj):
        return '<div style="display: inline-block; width: 20px; height:20px; background-color: %s;"></div>' % obj.colour
    get_colour.short_description = "Color"


def utc_unit_name(obj):
    return obj.unit_test_collection.unit.name
utc_unit_name.admin_order_field = "unit_test_collection__unit__name"  # noqa: E305
utc_unit_name.short_description = "Unit"


class TestListInstanceAdmin(SaveInlineAttachmentUserMixin, admin.ModelAdmin):
    list_display = ["__str__", utc_unit_name, "test_list", "work_completed", "created_by"]
    list_filter = ["unit_test_collection__unit", "test_list", ]
    inlines = [get_attachment_inline("testlistinstance")]

    def render_delete_form(self, request, context):
        instance = context['object']

        # Find related Service events with rtsqa and with initiated by
        ServiceEvent = apps.get_model('service_log', 'ServiceEvent')
        ServiceEventStatus = apps.get_model('service_log', 'ServiceEventStatus')
        se_rtsqa_qs = ServiceEvent.objects.filter(
            returntoserviceqa__test_list_instance=context['object']
        )
        se_ib_qs = instance.serviceevents_initiated.all()
        default_ses = ServiceEventStatus.get_default()
        context.update({
            'se_rtsqa_qs': se_rtsqa_qs,
            'se_ib_qs': se_ib_qs,
            'default_ses': default_ses
        })
        return super().render_delete_form(request, context)


class TestInstanceAdmin(SaveInlineAttachmentUserMixin, admin.ModelAdmin):

    list_display = [
        "__str__",
        "test_list_instance",
        "test_name",
        "unit_name",
        "test_list_name",
        "work_completed",
        "created_by",
    ]
    inlines = [get_attachment_inline("testinstance")]

    def get_queryset(self, request):
        qs = super(TestInstanceAdmin, self).get_queryset(request)
        return qs.select_related(
            "test_list_instance",
            "test_list_instance__test_list",
            "unit_test_info",
            "unit_test_info__test",
            "created_by"
        )

    def test_list_name(self, obj):
        return obj.test_list_instance.test_list.name
    test_list_name.short_description = _("Test List Name")
    test_list_name.admin_order_field = "test_list_instance__test_list__name"

    def test_name(self, obj):
        return obj.unit_test_info.test.name
    test_name.short_description = _("Test Name")
    test_name.admin_order_field = "unit_test_info__test__name"

    def unit_name(self, obj):
        return obj.unit_test_info.unit
    unit_name.short_description = _("Unit Name")
    unit_name.admin_order_field = "unit_test_info__unit__number"

    def has_add_permission(self, request):
        """testlistinstancess are created via front end only"""
        return False


class ToleranceForm(forms.ModelForm):

    model = models.Tolerance

    def validate_unique(self):
        super(ToleranceForm, self).validate_unique()
        if not self.instance.pk:
            params = forms.model_to_dict(self.instance)
            params.pop("id")
            if models.Tolerance.objects.filter(**params).count() > 0:
                errs = ["Duplicate Tolerance. A Tolerance with these values already exists"]
                self._update_errors({forms.models.NON_FIELD_ERRORS: errs})


class ToleranceAdmin(BasicSaveUserAdmin):
    form = ToleranceForm
    list_filter = ["type"]

    class Media:
        js = (
            settings.STATIC_URL + "jquery/js/jquery.min.js",
            settings.STATIC_URL + "js/tolerance_admin.js",
        )

    def get_queryset(self, *args, **kwargs):
        qs = super(ToleranceAdmin, self).get_queryset(*args, **kwargs)
        return qs.exclude(type=models.BOOLEAN)

    def has_change_permission(self, request, obj=None):

        if obj and obj.type == models.BOOLEAN:
            return False
        return super(ToleranceAdmin, self).has_change_permission(request, obj)


class AutoReviewAdmin(admin.ModelAdmin):
    list_display = (str, "pass_fail", "status")
    list_editable = ["pass_fail", "status"]


admin.site.register([models.Tolerance], ToleranceAdmin)
admin.site.register([models.AutoReviewRule], AutoReviewAdmin)
admin.site.register([models.Category], CategoryAdmin)
admin.site.register([models.TestList], TestListAdmin)
admin.site.register([models.Test], TestAdmin)
admin.site.register([models.UnitTestInfo], UnitTestInfoAdmin)
admin.site.register([models.UnitTestCollection], UnitTestCollectionAdmin)

admin.site.register([models.TestListCycle], TestListCycleAdmin)
admin.site.register([models.Frequency], FrequencyAdmin)
admin.site.register([models.TestInstanceStatus], StatusAdmin)
admin.site.register([models.TestInstance], TestInstanceAdmin)
admin.site.register([models.TestListInstance], TestListInstanceAdmin)
