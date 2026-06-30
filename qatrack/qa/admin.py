import re

from django import VERSION, forms
from django.apps import apps
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import helpers, options, widgets
from django.contrib.admin.helpers import flatten_fieldsets
from django.db.models import Count, Q
from django.template import loader
from django.template.defaultfilters import date as date_formatter
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import escape, format_html_join
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django_mptt_admin.admin import DjangoMpttAdmin
from dynamic_raw_id.admin import DynamicRawIDMixin
from dynamic_raw_id.widgets import DynamicRawIDWidget

from qatrack.attachments.admin import (
    SaveInlineAttachmentUserMixin,
    get_attachment_inline,
)
from qatrack.qa import models
from qatrack.qa.utils import format_qc_value
from qatrack.qa.views import admin as admin_views
from qatrack.qatrack_core import scheduling
from qatrack.qatrack_core.admin import (
    BaseQATrackAdmin,
    BasicSaveUserAdmin,
    SaveUserMixin,
)
from qatrack.units.forms import unit_site_unit_type_choices
from qatrack.units.models import Site, Unit

admin.site.disable_action("delete_selected")


class CategoryAdmin(DjangoMpttAdmin):
    """QC categories admin"""
    prepopulated_fields = {
        'slug': ('name',)
    }
    list_display = (
        "name",
        "get_description",
    )

    def get_description(self, obj):
        """Just used to disable ordering by description"""
        return obj.description if obj else ""

    get_description.short_name = _l("Description")


class UnitTestInfoForm(forms.ModelForm):
    """Form for UnitTestInfo model"""

    reference_value = forms.CharField(label=_("New reference value"), required=False)
    reference_set_by = forms.CharField(label=_("Set by"), required=False)
    reference_set = forms.CharField(label=_("Date"), required=False)
    test_type = forms.CharField(required=False)
    comment = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text=_("Include an optional comment about why this reference/tolerance is being updated")
    )

    class Meta:
        model = models.UnitTestInfo
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        readonly = (
            "test_type",
            "reference_set_by",
            "reference_set",
        )
        instance = kwargs.get('instance')

        if instance and instance.test:
            # Set test type
            self.fields['test_type'].initial = instance.test.get_type_display()

            # Set reference information if reference exists
            if instance.reference:
                self.fields['reference_set_by'].initial = getattr(instance.reference, 'created_by', 'Unknown')
                # Format the date to be more readable and in user's timezone
                created_date = getattr(instance.reference, 'created', None)
                if created_date:
                    # Use Django's timezone handling which respects site timezone settings
                    if timezone.is_aware(created_date):
                        local_date = timezone.localtime(created_date)
                    else:
                        local_date = created_date
                    self.fields['reference_set'].initial = local_date.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    self.fields['reference_set'].initial = 'Unknown'

            # Filter tolerances based on test type
            if instance.test.type == models.BOOLEAN:
                self.fields['tolerance'].queryset = models.Tolerance.objects.filter(type=models.BOOLEAN)
                self.fields['reference_value'] = forms.ChoiceField(
                    choices=[("", "---"), (0, "No"), (1, "Yes")], required=False, label=_("New reference value")
                )
            elif instance.test.type == models.MULTIPLE_CHOICE:
                self.fields['tolerance'].queryset = models.Tolerance.objects.filter(type=models.MULTIPLE_CHOICE)
                self.fields['reference_value'].widget = forms.HiddenInput()
            else:
                # For numerical tests, exclude boolean and multiple choice tolerances
                self.fields['tolerance'].queryset = models.Tolerance.objects.exclude(
                    type__in=[models.BOOLEAN, models.MULTIPLE_CHOICE]
                )
                self.fields['reference_value'].widget = forms.TextInput()

        for field in readonly:
            self.fields[field].widget.attrs['readonly'] = True

    def clean(self):
        cleaned_data = super().clean()

        if not self.instance or not self.instance.test:
            return cleaned_data

        reference_value = cleaned_data.get("reference_value", "")
        tolerance = cleaned_data.get("tolerance")

        # Validate percent tolerance requires numerical reference
        if tolerance and tolerance.type == models.PERCENT:
            if not reference_value:
                self.add_error('reference_value', _("A reference value is required when using a percent tolerance"))
            else:
                try:
                    val = float(reference_value)
                    if val == 0:
                        self.add_error(
                            'reference_value', _("Reference value cannot be zero when using a percent tolerance")
                        )
                except ValueError:
                    self.add_error(
                        'reference_value', _("A numerical reference value is required when using a percent tolerance")
                    )

        # Validate wraparound tests
        if self.instance.test.type == models.WRAPAROUND:
            try:
                if reference_value:
                    val = float(reference_value)
                    if val < self.instance.test.wrap_low or val > self.instance.test.wrap_high:
                        self.add_error(
                            'reference_value',
                            _("Reference value must be between %(low)s and %(high)s for wraparound tests") % {
                                'low': self.instance.test.wrap_low,
                                'high': self.instance.test.wrap_high
                            }
                        )
            except ValueError:
                self.add_error('reference_value', _("Reference value must be a number for wraparound tests"))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Handle reference value conversion
        reference_value = self.cleaned_data.get('reference_value')

        # Get the user from the form's initial data (set by FormWithRequest)
        user = self.initial.get('modified_by')

        if reference_value is not None and reference_value != '':  # Non-empty reference value
            if instance.test.type == models.BOOLEAN:
                value = bool(int(reference_value))
            elif instance.test.type == models.MULTIPLE_CHOICE:
                value = reference_value
            else:
                # For numerical tests, try to preserve the original type from the form data
                # If the original form data contained a numeric type, keep it as a number
                # If it was a string, keep it as a string
                original_value = self.data.get('reference_value')
                if original_value and not isinstance(original_value, str):
                    # Original was numeric, convert to float
                    try:
                        value = float(reference_value)
                    except (ValueError, TypeError):
                        value = reference_value
                else:
                    # Original was string or None, keep as string
                    value = reference_value

            ref = models.Reference(
                value=value,
                name=str(value),
                created_by=user,
                modified_by=user,
            )
            ref.save()
            instance.reference = ref
        elif 'reference_value' in self.cleaned_data:
            # reference_value field was in the form but empty - clear the reference
            instance.reference = None

        if commit:
            instance.save()
        return instance


@admin.display(ordering="test__name")
def test_name(obj):
    return obj.test.name


@admin.display(ordering="test__type")
def test_type(obj):
    for tt, display in models.TEST_TYPE_CHOICES:
        if obj.test.type == tt:
            return display


class SetMultipleReferencesAndTolerancesForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    contenttype = forms.CharField(widget=forms.HiddenInput, required=False)
    tolerance = forms.ModelChoiceField(
        queryset=models.Tolerance.objects.all(),
        required=False,
        empty_label=_("No Tolerance Set"),
    )
    reference = forms.FloatField(required=False)
    comment = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text=_("Include an optional comment about why these references/tolerances are being updated")
    )


# see http://stackoverflow.com/questions/851636/default-filter-in-django-admin
class ActiveUnitTestInfoFilter(admin.SimpleListFilter):

    NOTACTIVE = 'notactive'
    ACTIVE = 'active'

    title = _('Active Unit Assignments')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'activeassignment'

    def lookups(self, request, model_admin):
        return (
            (None, _('All')),
            (self.ACTIVE, _('At Least One Active Unit Assignment')),
            (self.NOTACTIVE, _('No Active Unit Assignments')),
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

    def queryset(self, request, qs):
        if self.value() == self.NOTACTIVE:
            return models.UnitTestInfo.objects.inactive(qs)
        elif self.value() == self.ACTIVE:
            return models.UnitTestInfo.objects.active(qs)
        return qs


class UnitTestInfoAdmin(BaseQATrackAdmin):
    """Admin interface for UnitTestInfo model"""

    change_list_template = "admin/qa/unittestinfo/change_list.html"
    form = UnitTestInfoForm

    fieldsets = (
        (None, {
            'fields': (
                'unit',
                'test',
                'reference',
                'tolerance',
            )
        }),
        (
            _('Reference Value'), {
                'fields': (
                    'test_type',
                    'reference_value',
                    'reference_set_by',
                    'reference_set',
                    'comment',
                ),
            }
        ),
        (_('History'), {
            'fields': ('history',),
        }),
    )

    list_display = [test_name, "unit", test_type, "reference", "tolerance"]
    list_filter = [
        ActiveUnitTestInfoFilter, "unit__site", "unit", "test__category", "test__testlistmembership__test_list"
    ]
    readonly_fields = ("reference", "test", "unit", "history")
    search_fields = ("test__name", "test__display_name", "test__slug", "unit__name")

    def get_fields(self, request, obj=None):
        """Override to ensure form-only fields are included"""
        form = self.get_form(request, obj, fields=None)
        return list(form.base_fields) + list(self.get_readonly_fields(request, obj))

    def get_form(self, request, obj=None, **kwargs):
        """Override to ensure form-only fields are handled correctly"""
        if 'fields' in kwargs:
            fields = kwargs.pop('fields')
        else:
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        FormClass = super().get_form(request, obj, fields=fields, **kwargs)

        class FormWithRequest(FormClass):

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.initial['modified_by'] = request.user

        return FormWithRequest

    @admin.display(description=_("Reference & Tolerance History"))
    def history(self, obj):
        """Display history of reference and tolerance changes"""
        if not obj:
            return _("No history available")

        changes = models.UnitTestInfoChange.objects.filter(unit_test_info=obj).order_by('-changed')

        if not changes:
            return _("No history available")

        # Create pairs of changes to show old and new values
        history = []
        current = {
            'reference': obj.reference,
            'tolerance': obj.tolerance,
        }

        for change in changes:
            history.append((current, change))
            current = {
                'reference': change.reference,
                'tolerance': change.tolerance,
            }

        t = loader.get_template("admin/qa/unittestinfo/history.html")
        return t.render({'history': history})

    def save_model(self, request, test_info, form, change):
        # Fetch the old instance from the DB before saving changes
        if test_info.pk:
            old = models.UnitTestInfo.objects.get(pk=test_info.pk)
            old_reference = old.reference
            old_tolerance = old.tolerance
        else:
            old_reference = None
            old_tolerance = None

        # Save the new values
        super().save_model(request, test_info, form, change)

        # Now create the history record using the old values
        if any(k in form.changed_data for k in ['comment', 'reference_value', 'tolerance']):
            if form.instance and form.instance.pk:
                models.UnitTestInfoChange.objects.create(
                    unit_test_info=form.instance,
                    comment=form.cleaned_data["comment"],
                    reference=old_reference,
                    reference_changed=old_reference != form.instance.reference,
                    tolerance=old_tolerance,
                    tolerance_changed=old_tolerance != form.instance.tolerance,
                    changed_by=request.user,
                )

    @admin.action(description=_("Set references and tolerances for selected tests"))
    def set_multiple_references_and_tolerances(self, request, queryset):
        """Set references and tolerances for multiple UnitTestInfo objects"""
        if request.POST.get('post') == 'yes':
            tolerance_id = request.POST.get('tolerance')
            reference_value = request.POST.get('reference')

            if tolerance_id:
                try:
                    tolerance = models.Tolerance.objects.get(pk=tolerance_id)
                except models.Tolerance.DoesNotExist:
                    self.message_user(request, _("Invalid tolerance selected"), level=messages.ERROR)
                    return None
            else:
                tolerance = None

            # Check if all tests are of the same type
            test_types = set(uti.test.type for uti in queryset)
            if len(test_types) > 1:
                self.message_user(
                    request,
                    _("Cannot set the same reference value for tests of different types"),
                    level=messages.ERROR
                )
                return None

            test_type = test_types.pop() if test_types else None

            # Check for incompatible tolerance/test type combinations
            if test_type and tolerance:
                incompatible = False

                # Boolean tests can only use boolean tolerances
                if test_type == models.BOOLEAN and tolerance.type != models.BOOLEAN:
                    incompatible = True
                # Multiple choice tests can only use multiple choice tolerances
                elif test_type == models.MULTIPLE_CHOICE and tolerance.type != models.MULTIPLE_CHOICE:
                    incompatible = True
                # Boolean/MC tolerances can only be used with their respective test types
                elif tolerance.type == models.BOOLEAN and test_type != models.BOOLEAN:
                    incompatible = True
                elif tolerance.type == models.MULTIPLE_CHOICE and test_type != models.MULTIPLE_CHOICE:
                    incompatible = True

                if incompatible:
                    self.message_user(
                        request, _("The selected tolerance is not compatible with the test type"), level=messages.ERROR
                    )
                    return None

            for uti in queryset:
                changed = False

                if tolerance:
                    uti.tolerance = tolerance
                    changed = True

                if reference_value:
                    if uti.test.type == models.BOOLEAN:
                        try:
                            value = bool(int(reference_value))
                        except (ValueError, TypeError):
                            self.message_user(request, _("Invalid boolean value"), level=messages.ERROR)
                            return None
                    elif uti.test.type == models.MULTIPLE_CHOICE:
                        if not uti.test.choices or reference_value not in uti.test.choices.split(","):
                            self.message_user(
                                request, _("Invalid choice for multiple choice test"), level=messages.ERROR
                            )
                            return None
                        value = reference_value
                    else:
                        try:
                            # For numerical tests, convert to float since the test expects float values
                            value = float(reference_value)
                        except (ValueError, TypeError):
                            self.message_user(request, _("Invalid numerical value"), level=messages.ERROR)
                            return None

                    ref = models.Reference(
                        value=value,
                        name=str(value),
                        created_by=request.user,
                        modified_by=request.user,
                    )
                    ref.save()
                    uti.reference = ref
                    changed = True

                if changed:
                    uti.save()

            self.message_user(request, _("Successfully updated references and tolerances"))
            return None

        context = {
            'title': _("Set references and tolerances"),
            'queryset': queryset,
            'opts': self.model._meta,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        }
        return TemplateResponse(request, 'admin/qa/unittestinfo/set_multiple.html', context)

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'jquery/js/jquery.min.js',
            "select2/js/select2.js",
            "js/unittestinfo_admin.js",
        )
        css = {
            'all': (
                "qatrack_core/css/admin.css",
                "select2/css/select2.css",
            ),
        }

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'copy-refs-tols/',
                self.admin_site.admin_view(admin_views.CopyReferencesTolerancesView.as_view()),
                name='qa_copy_refs_and_tols'
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['copy_refs_tols_url'] = reverse('admin:qa_copy_refs_and_tols')
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, *args, **kwargs):
        """just display active ref/tols"""
        qs = models.UnitTestInfo.objects.select_related(
            "reference",
            "tolerance",
            "unit",
            "test",
        ).exclude(
            test__hidden=True,
        )
        return qs

    def has_add_permission(self, request):
        """unittestinfo's are created automatically"""
        return False


class TestListAdminForm(forms.ModelForm):
    """Form for handling validation of TestList creation/editing"""

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        dup = models.TestList.objects.exclude(pk=self.instance.pk).filter(slug=slug)
        if dup:
            raise forms.ValidationError(
                _("A test list with the slug '%(test_name)s' already exists in the database") % {'test_name': slug}
            )
        return slug

    def clean(self):
        retest = re.compile(r"^testlistmembership_set-\d+-test$")
        test_ids = [x[1] for x in self.data.items() if retest.findall(x[0]) and x[1]]
        slugs = list(models.Test.objects.filter(id__in=test_ids).values_list("slug", flat=True))

        rechild = re.compile(r"^children-\d+-child$")
        child_ids = [x[1] for x in self.data.items() if rechild.findall(x[0]) and x[1]]
        for tl in models.TestList.objects.filter(id__in=child_ids):
            slugs.extend(tl.all_tests().values_list("slug", flat=True))

        if len(slugs) > settings.MAX_TESTS_PER_TESTLIST:
            msg = _("This test list has {test_count} tests but the maximum number allowed is {max_tests}.").format(
                test_count=len(slugs), max_tests=settings.MAX_TESTS_PER_TESTLIST
            )
            raise forms.ValidationError(msg)

        duplicates = list(set([sn for sn in slugs if slugs.count(sn) > 1]))
        if duplicates:
            msg = _(
                "The following test macro names are duplicated (either in this test list or one of its sublists) :: "
            )
            msg += ",".join(duplicates)
            raise forms.ValidationError(msg)

        return self.cleaned_data


class TestListMembershipInlineFormSet(forms.models.BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        if instance is None:
            # When creating a new TestList, there are no existing memberships
            qs = kwargs["queryset"].none()
        else:
            qs = kwargs["queryset"].filter(test_list=instance).select_related("test")
        kwargs["queryset"] = qs
        super().__init__(*args, **kwargs)


class SublistInlineFormSet(forms.models.BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        if instance is None:
            # When creating a new TestList, there are no existing sublists
            qs = kwargs["queryset"].none()
        else:
            qs = kwargs["queryset"].filter(parent=instance)
        kwargs["queryset"] = qs
        super().__init__(*args, **kwargs)

    def clean(self):
        """Make sure there are no duplicated slugs in a TestList"""
        super().clean()

        if not hasattr(self, "cleaned_data"):
            # something else went wrong already
            return {}

        children = [
            f.instance.child for f in self.forms if hasattr(f.instance, 'child') and not f.cleaned_data.get("DELETE")
        ]  # noqa: E501
        children_with_child = [child for child in children if child.children.exists()]
        if self.instance and self.instance in children:
            raise forms.ValidationError(
                _("A Test List can not be its own child. Please remove Sublist ID %(sublist_id)d and try again") %
                {'sublist_id': self.instance.pk}
            )
        elif children_with_child:
            names = ', '.join(c.name for c in children_with_child)
            raise forms.ValidationError(
                _(
                    "Test Lists can not be nested more than 1 level. Test List(s) "
                    "%(test_list_names)s already has(have) a sublist and therefore can't be used as a sublist."
                ) % {'test_list_names': names}
            )
        elif self.instance and self.instance.pk and self.instance.sublist_set.exists() and children:
            raise forms.ValidationError(
                _(
                    "This Test List is a Sublist of Test Lists: %(sublist_name)s"
                    " and therefore can't have sublists of its own."
                ) % {'sublist_name': ', '.join(self.instance.sublist_set.values_list("parent__name", flat=True))}
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
            rel = db_field.remote_field if VERSION[0] >= 2 else db_field.rel
            widget = DynamicRawIDWidget(rel, self.admin_site)
            widget.label_for_value = self.label_for_value
            kwargs['widget'] = widget
            return db_field.formfield(**kwargs)
        elif db_field.name in self.dynamic_raw_id_fields:
            rel = db_field.remote_field if VERSION[0] >= 2 else db_field.rel
            kwargs['widget'] = DynamicRawIDWidget(rel, self.admin_site)
            return db_field.formfield(**kwargs)
        elif db_field.name in self.raw_id_fields:
            kwargs['widget'] = widgets.ForeignKeyRawIdWidget(
                db_field.remote_field if VERSION[0] >= 2 else db_field.rel, self.admin_site, using=db
            )
        elif db_field.name in self.radio_fields:
            kwargs['widget'] = widgets.AdminRadioSelect(
                attrs={
                    'class': options.get_ul_class(self.radio_fields[db_field.name]),
                }
            )
            kwargs['empty_label'] = db_field.blank and _('None') or None
        return db_field.formfield(**kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        # hacky method for getting test names so they don't need to be looked up again
        # in the label_for_value in contrib/admin/widgets.py
        if obj:
            self.test_names = dict(obj.tests.values_list("pk", "name"))
        else:
            self.test_names = {}
        return super().get_formset(request, obj, **kwargs)


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
            rel = db_field.remote_field if VERSION[0] >= 2 else db_field.rel
            widget = DynamicRawIDWidget(rel, self.admin_site)
            widget.label_for_value = self.label_for_value
            kwargs['widget'] = widget
            return db_field.formfield(**kwargs)

        elif db_field.name in self.dynamic_raw_id_fields:
            rel = db_field.remote_field if VERSION[0] >= 2 else db_field.rel
            kwargs['widget'] = DynamicRawIDWidget(rel, self.admin_site)
            return db_field.formfield(**kwargs)

        elif db_field.name in self.raw_id_fields:
            kwargs['widget'] = widgets.ForeignKeyRawIdWidget(
                db_field.remote_field if VERSION[0] >= 2 else db_field.rel, self.admin_site, using=db
            )
        elif db_field.name in self.radio_fields:
            kwargs['widget'] = widgets.AdminRadioSelect(
                attrs={
                    'class': options.get_ul_class(self.radio_fields[db_field.name]),
                }
            )
            kwargs['empty_label'] = db_field.blank and _('None') or None
        return db_field.formfield(**kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        # hacky method for getting test names so they don't need to be looked up again
        # in the label_for_value in contrib/admin/widgets.py
        if obj:
            self.test_list_names = dict(obj.sublist_set.values_list("pk", "child__name"))
        else:
            self.test_list_names = {}
        return super().get_formset(request, obj, **kwargs)


class ActiveTestListFilter(admin.SimpleListFilter):

    NOACTIVEUTCS = 'noactiveutcs'
    HASACTIVEUTCS = 'hasactiveutcs'

    title = _l('Active Unit Assignments')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'activeutcs'

    def lookups(self, request, model_admin):
        return (
            (self.NOACTIVEUTCS, _l('No Active Unit Assignments')),
            (self.HASACTIVEUTCS, _l('At Least One Active Unit Assignment')),
        )

    def queryset(self, request, qs):
        active_tl_ids = models.get_utc_tl_ids(active=True)
        active_sub_tl_ids = list(
            models.TestList.objects.filter(id__in=active_tl_ids,
                                           children__isnull=False).values_list('children__child__id',
                                                                               flat=True).distinct()
        )

        if self.value() == self.NOACTIVEUTCS:
            return qs.exclude(Q(id__in=active_tl_ids) | Q(id__in=active_sub_tl_ids))
        elif self.value() == self.HASACTIVEUTCS:
            return qs.filter(Q(id__in=active_tl_ids) | Q(id__in=active_sub_tl_ids))
        return qs


class UnitTestListFilter(admin.SimpleListFilter):

    title = _l('Assigned to Unit')

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


class SiteTestListFilter(admin.SimpleListFilter):

    title = _l('Assigned to Site')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'assignedtosite'

    def lookups(self, request, model_admin):
        return Site.objects.values_list("pk", "name")

    def queryset(self, request, qs):

        if self.value():
            site = Site.objects.get(pk=self.value())
            units = Unit.objects.filter(site=site)
            unit_tl_ids = models.get_utc_tl_ids(units=units)
            return qs.filter(id__in=unit_tl_ids)

        return qs


class FrequencyTestListFilter(admin.SimpleListFilter):

    title = _l('Assigned To Units by Frequency')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'assignedbyfreq'

    def lookups(self, request, model_admin):
        return [("adhoc", _("Ad Hoc"))] + list(models.Frequency.objects.values_list("pk", "name"))

    def queryset(self, request, qs):

        v = self.value()
        if v:
            if v == "adhoc":
                freq = None
            else:
                freq = models.Frequency.objects.get(pk=v)
            freq_tl_ids = models.get_utc_tl_ids(frequencies=[freq])
            return qs.filter(id__in=freq_tl_ids)

        return qs


class TestListAdmin(SaveUserMixin, SaveInlineAttachmentUserMixin, BaseQATrackAdmin):

    prepopulated_fields = {
        'slug': ('name',)
    }
    search_fields = ("name", "description", "slug", "sublist__parent__name", "sublist__child__name")
    readonly_fields = ("id",)

    filter_horizontal = ("tests",)

    actions = ['export_test_lists']
    list_display = (
        "name",
        "id",
        "slug",
        "parent_of",
        "child_of",
        "modified",
        "modified_by",
    )
    list_filter = [ActiveTestListFilter, SiteTestListFilter, UnitTestListFilter, FrequencyTestListFilter]

    form = TestListAdminForm
    inlines = [TestListMembershipInline, SublistInline, get_attachment_inline("testlist")]
    save_as = True

    fieldsets = [
        (
            "Test List",
            {
                'fields': ['id', 'name', 'slug', 'description', 'javascript', 'warning_message']
            },
        ),
        (
            "Sublist Memberships",
            {
                'fields': [],
            },
        ),
    ]

    class Media:
        js = (
            "admin/js/jquery.init.js",
            'jquery/js/jquery.min.js',
            "js/jquery-ui.init.js",
            "js/jquery-ui.min.js",
            "js/m2m_drag_admin_testlist.js",
            "js/admin_description_editor.js",
            "ace/ace.js",
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'export-testpack/',
                self.admin_site.admin_view(admin_views.ExportTestPack.as_view()),
                name='qa_export_testpack'
            ),
            path(
                'import-testpack/',
                self.admin_site.admin_view(admin_views.ImportTestPack.as_view()),
                name='qa_import_testpack'
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['export_testpack_url'] = reverse('admin:qa_export_testpack')
        extra_context['import_testpack_url'] = reverse('admin:qa_import_testpack')
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        return qs.prefetch_related(
            "sublist_set",
            "sublist_set__parent",
            "children",
            "children__child",
        )

    @mark_safe
    def child_of(self, obj):
        title = _("Click to view parent test list")
        links = [(sl.parent.name, reverse("admin:qa_testlist_change", args=(sl.parent.pk,)))
                 for sl in obj.sublist_set.all()]
        html_links = format_html_join(
            ", ", '<a href="{}" title="{}" target="_blank">{}</a>', ((url, title, name) for (name, url) in links)
        )
        return html_links

    @mark_safe
    def parent_of(self, obj):
        title = _("Click to view child test list")
        links = [(sl.child.name, reverse("admin:qa_testlist_change", args=(sl.child.pk,))) for sl in obj.children.all()]
        html_links = format_html_join(
            ", ", '<a href="{}" title="{}" target="_blank">{}</a>', ((url, title, name) for (name, url) in links)
        )
        return html_links


class TestForm(forms.ModelForm):

    class Meta:
        model = models.Test
        fields = "__all__"

    def clean(self):
        """if test already has some history don't allow for the test type to be changed"""

        cleaned_data = super().clean()

        test_type = cleaned_data.get("type")
        user_changing_type = self.instance.type != test_type
        has_history = models.TestInstance.objects.filter(unit_test_info__test=self.instance).exists()
        if user_changing_type and has_history and not models.Test.allow_type_transition(self.instance.type, test_type):
            msg = _(
                "You can't change the test type from %(old_test_type)s to %(new_test_type)s for a test that "
                "has already been performed. Revert to '%(old_test_type)s' before saving or create a new test with "
                "'Save as New'."
            )
            old_ttype_index = [ttype for ttype, label in models.TEST_TYPE_CHOICES].index(self.instance.type)
            old_ttype_label = models.TEST_TYPE_CHOICES[old_ttype_index][1]
            new_ttype_index = [ttype for ttype, label in models.TEST_TYPE_CHOICES].index(test_type)
            new_ttype_label = models.TEST_TYPE_CHOICES[new_ttype_index][1]
            self.add_error(
                'type',
                forms.ValidationError(msg % {
                    'old_test_type': old_ttype_label,
                    'new_test_type': new_ttype_label,
                })
            )

        if test_type not in models.NUMERICAL_TYPES:
            cleaned_data['formatting'] = ''
        else:
            fmt = cleaned_data.get('formatting')
            if fmt:
                try:
                    format_qc_value(123.4, fmt)
                except:  # noqa: E722
                    self.add_error("formatting", forms.ValidationError(_("Invalid numerical format")))

        editing_hidden = self.instance.pk is not None and cleaned_data.get("hidden")
        if editing_hidden:
            existing_ref_tols = models.UnitTestInfo.objects.filter(test=self.instance).exclude(
                reference=None,
                tolerance=None,
            )
            if existing_ref_tols.exists():
                links = []
                for uti, name in existing_ref_tols.order_by("unit__name").values_list("pk", "unit__name"):
                    url = reverse(
                        "admin:qa_unittestinfo_change", args=(uti,)
                    )
                    links.append((url, name))

                title = _(_("Click to edit the reference and tolerance l(opens in new window)"))
                html_links = format_html_join(
                    ", ", '<a href="{}" title="{}" target="_blank">{}</a>', ((u, title, l) for (u, l) in links)
                )
                msg = _(
                    "Hidden tests can not have references and tolerances set. Please remove the references "
                    "and tolerances for this test on the following units before making it hidden: "
                ) + html_links
                self.add_error("hidden", mark_safe(msg))
        return cleaned_data


class TestListMembershipFilter(admin.SimpleListFilter):
    NOMEMBERSHIPS = 'nomemberships'
    HASMEMBERSHIPS = 'hasmemberships'

    title = _l('Test List Membership')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'tlmembership'

    def lookups(self, request, model_admin):
        return (
            (self.NOMEMBERSHIPS, _l('No TestList Membership')),
            (self.HASMEMBERSHIPS, _l('At Least One TestList Membership')),
        )

    def queryset(self, request, queryset):
        qs = queryset.annotate(tlcount=Count("testlistmembership"))
        if self.value() == self.NOMEMBERSHIPS:
            return qs.filter(tlcount=0)
        elif self.value() == self.HASMEMBERSHIPS:
            return qs.filter(tlcount__gt=0)
        return qs


class TestAdmin(SaveUserMixin, SaveInlineAttachmentUserMixin, BaseQATrackAdmin):

    inlines = [get_attachment_inline("test")]
    list_display = ["name", "id", "slug", "category", "type", 'obj_created', 'obj_modified']
    list_filter = ["category", "type", TestListMembershipFilter, "testlistmembership__test_list"]
    search_fields = ["name", "slug", "category__name"]
    readonly_fields = ("id",)
    save_as = True

    form = TestForm
    fieldsets = [
        (
            "Test ID",
            {
                'fields': ['id']
            },
        ),
        (
            "Test options",
            {
                'fields': ['name', 'display_name', 'slug', 'description', 'procedure', 'category'],
            },
        ),
        (
            "Test type options",
            {
                'fields': [
                    'type',
                    'flag_when',
                    'choices',
                    'constant_value',
                    'wrap_low',
                    'wrap_high',
                    'calculation_procedure',
                    'display_image',
                    'hidden',
                    'chart_visibility',
                    'skip_without_comment',
                    'require_comment',
                    'formatting',
                ],
            },
        ),
        (
            "Autoreview Rules",
            {
                'fields': ['autoreviewruleset'],
            },
        ),
        (
            "Memberships & Assignments",
            {
                'fields': [],
            },
        ),
    ]

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'jquery/js/jquery.min.js',
            "js/test_admin.js",
            "js/admin_description_editor.js",
            "ace/ace.js",
            "select2/js/select2.js",
        )
        css = {
            'all': (
                "qatrack_core/css/admin.css",
                "select2/css/select2.css",
            ),
        }

    def save_model(self, request, obj, form, change):
        if 'calculation_procedure' in form.changed_data:
            cp = obj.calculation_procedure or ""
            if "pyplot" in cp or "pylab" in cp:
                warning = _(
                    "Warning: Instead of using pyplot or pylab, it is recommended that you use "
                    "the object oriented interface to matplotlib."
                )
                messages.add_message(request, messages.WARNING, warning)

        if obj.procedure:
            if not obj.procedure.startswith("http"):
                warning = _("Warning: test procedure links should usually begin with http:// or https://")
                messages.add_message(request, messages.WARNING, warning)

        super().save_model(request, obj, form, change)

    @admin.display(
        description=_l("Created"),
        ordering="created",
    )
    @mark_safe
    def obj_created(self, obj):
        link_title = _("Created by %(username)s") % {'username': obj.created_by}
        dt = date_formatter(timezone.localtime(obj.created), "DATETIME_FORMAT")
        return '<abbr title="%s">%s</abbr>' % (link_title, dt)

    @admin.display(
        description=_l("Modified"),
        ordering="modified",
    )
    @mark_safe
    def obj_modified(self, obj):
        link_title = _("Modified by %(username)s") % {'username': obj.modified_by}
        dt = date_formatter(timezone.localtime(obj.modified), "DATETIME_FORMAT")
        return '<abbr title="%s">%s</abbr>' % (link_title, dt)


@admin.display(
    description=_l("Unit"),
    ordering="unit__name",
)
def unit_name(obj):
    return obj.unit.name


@admin.display(
    description=_l("Site"),
    ordering="unit__site__name",
)
def site_name(obj):
    return obj.unit.site.name if obj.unit.site else _l("Other")


@admin.display(
    description=_l("Frequency"),
    ordering="frequency__name",
)
def freq_name(obj):
    return obj.frequency.name if obj.frequency else _l("Ad Hoc")


@admin.display(
    description=_l("Assigned To"),
    ordering="assigned_to__name",
)
def assigned_to_name(obj):
    return obj.assigned_to.name


class SiteFilter(admin.SimpleListFilter):

    title = _l('Site')
    parameter_name = "sitefilter"

    def lookups(self, request, model_admin):
        return Site.objects.values_list('pk', 'name')

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(unit__site=self.value())

        return queryset


class UnitFilter(admin.SimpleListFilter):

    title = _l('Unit')
    parameter_name = "unitfilter"

    def lookups(self, request, model_admin):
        return models.Unit.objects.values_list('pk', 'name')

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(unit=self.value())

        return queryset


class FrequencyFilter(admin.SimpleListFilter):

    title = _l('Frequency')
    parameter_name = "freqfilter"

    def lookups(self, request, model_admin):
        return [("adhoc", _l("Ad Hoc"))] + list(models.Frequency.objects.values_list("pk", "name"))

    def queryset(self, request, queryset):

        v = self.value()
        if self.value():
            return queryset.filter(frequency=None if v == "adhoc" else v)

        return queryset


class AssignedToFilter(admin.SimpleListFilter):

    title = _l('Assigned To')
    parameter_name = "assignedtoname"

    def lookups(self, request, model_admin):
        return models.Group.objects.values_list('pk', 'name')

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(assigned_to=self.value())

        return queryset


class ActiveFilter(admin.SimpleListFilter):

    title = _l('Active')
    parameter_name = "activefilter"

    def lookups(self, request, model_admin):
        return ((1, _('Active')), (0, _('Not active')))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(active=self.value())

        return queryset


class UnitTestCollectionForm(forms.ModelForm):

    unit = forms.TypedChoiceField(label=_l("Unit"), coerce=int)

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['unit'].choices = unit_site_unit_type_choices(include_empty=True)

        freq = self.fields['frequency']
        freq.queryset = freq.queryset.order_by("name")
        freq.empty_label = _("Ad Hoc (Unscheduled)")

    def _clean_readonly(self, f):
        data = self.cleaned_data.get(f, None)
        if f == "unit" and data:
            data = Unit.objects.get(pk=data)

        if self.instance.pk and f in self.changed_data:
            if f == "object_id":
                orig = str(self.instance.tests_object)
            else:
                orig = getattr(self.instance, f)
            err_msg = _(
                "To prevent data loss, you can not change the Unit, TestList or TestListCycle "
                "of a UnitTestCollection after it has been created. The original value was: %(object_id)s"
            ) % {
                'object_id': orig
            }
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


class UnitTestCollectionAdmin(BaseQATrackAdmin):
    # readonly_fields = ("unit","frequency",)
    filter_horizontal = ("visible_to",)
    list_display = ['name', site_name, unit_name, freq_name, assigned_to_name, 'get_content_type', "active"]
    list_filter = [SiteFilter, UnitFilter, FrequencyFilter, AssignedToFilter, ActiveFilter]
    search_fields = ['name', "unit__name", "frequency__name"]
    change_form_template = "admin/treenav/menuitem/change_form.html"
    list_editable = ["active"]
    save_as = True
    form = UnitTestCollectionForm

    class Media:
        js = (
            'jquery/js/jquery.min.js',
            "js/jquery-ui.init.js",
            "js/jquery-ui.min.js",
            "js/select2.min.js",
        )

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        return qs.select_related("unit", "unit__site", "frequency", "assigned_to", "content_type")

    @admin.display(
        description=_l("Content Type"),
        ordering="content_type__model",
    )
    def get_content_type(self, obj):
        if obj:
            return obj.content_type.model_class().__name__
        return _("Unknown")


class TestListCycleMembershipInline(DynamicRawIDMixin, admin.TabularInline):

    model = models.TestListCycleMembership
    dynamic_raw_id_fields = ("test_list",)


class TestListCycleAdmin(SaveUserMixin, SaveInlineAttachmentUserMixin, BaseQATrackAdmin):
    """Admin for daily test list cycles"""
    inlines = [TestListCycleMembershipInline, get_attachment_inline("testlistcycle")]
    prepopulated_fields = {
        'slug': ('name',)
    }
    search_fields = (
        "name",
        "slug",
    )
    list_display = ["name", "all_lists"]

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'jquery/js/jquery.min.js',
            "js/jquery-ui.init.js",
            "js/jquery-ui.min.js",
            "js/collapsed_stacked_inlines.js",
            "js/m2m_drag_admin.js",
            "js/admin_description_editor.js",
            "ace/ace.js",
        )

    def all_lists(self, obj):
        return ', '.join("%s: %s" % x for x in enumerate(obj.all_lists().values_list("name", flat=True)))

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("test_lists")


class FrequencyForm(forms.ModelForm):

    class Meta:
        model = models.Frequency
        fields = (
            'name',
            'slug',
            'recurrences',
            'window_start',
            'window_end',
        )

    def clean(self):
        """Ensure the define frequency has a valid set of occurences"""

        super().clean()

        recurrences = self.cleaned_data.get('recurrences')
        if recurrences and not scheduling.calc_nominal_interval(recurrences):
            self.add_error(
                'recurrences', 'This frequency has zero occurences. Please adjust the schedule and try again'
            )
        elif recurrences and len(recurrences.rrules) == 0:
            self.add_error(
                'recurrences', 'This frequency has exclusion rules only. Please adjust the schedule and try again'
            )
        return self.cleaned_data


class FrequencyAdmin(BaseQATrackAdmin):
    prepopulated_fields = {
        'slug': ('name',)
    }
    form = FrequencyForm
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
            'admin/js/jquery.init.js',
            'jquery/js/jquery.min.js',
            "js/jquery-ui.min.js",
            "moment/js/moment.min.js",
            "moment/js/moment-timezone-with-data.min.js",
            "rrule/js/rrule-tz.min.js",
            "d3/js/d3-3.5.6.min.js",
            "cal-heatmap/js/cal-heatmap.min.js",
            "js/frequency_admin.js",
        )
        css = {
            'all': ["cal-heatmap/css/cal-heatmap.css"],
        }

    @admin.display(description=_l("Recurrences"))
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


class StatusAdmin(BaseQATrackAdmin):
    prepopulated_fields = {
        'slug': ('name',)
    }
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
            'admin/js/jquery.init.js',
            "jquery/js/jquery.min.js",
            "colorpicker/js/bootstrap-colorpicker.min.js",
            "qatrack_core/js/admin_colourpicker.js",
        )
        css = {
            'all': (
                "colorpicker/css/bootstrap-colorpicker.min.css",
                "qatrack_core/css/admin.css",
            ),
        }

    @admin.display(description=_l("Color"))
    @mark_safe
    def get_colour(self, obj):
        return '<div style="display: inline-block; width: 20px; height:20px; background-color: %s;"></div>' % obj.colour


@admin.display(
    description=_l("Unit"),
    ordering="unit_test_collection__unit__name",
)
def utc_unit_name(obj):
    return obj.unit_test_collection.unit.name


class TestListInstanceAdmin(SaveInlineAttachmentUserMixin, BaseQATrackAdmin):
    list_display = ["__str__", utc_unit_name, "test_list", "work_completed", "created_by"]
    list_filter = [
        "unit_test_collection__unit",
        "test_list",
    ]
    inlines = [get_attachment_inline("testlistinstance")]

    def render_delete_form(self, request, context):
        instance = context['object']

        # Find related Service events with rtsqa and with initiated by
        ServiceEvent = apps.get_model('service_log', 'ServiceEvent')
        ServiceEventStatus = apps.get_model('service_log', 'ServiceEventStatus')
        se_rtsqa_qs = ServiceEvent.objects.filter(returntoserviceqa__test_list_instance=context['object'])
        se_ib_qs = instance.serviceevents_initiated.all()
        default_ses = ServiceEventStatus.get_default()
        context.update({'se_rtsqa_qs': se_rtsqa_qs, 'se_ib_qs': se_ib_qs, 'default_ses': default_ses})
        return super().render_delete_form(request, context)

    def has_add_permission(self, request):
        """testlistinstancess are created via front end only"""
        return False


class TestInstanceAdmin(SaveInlineAttachmentUserMixin, BaseQATrackAdmin):

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
        qs = super().get_queryset(request)
        return qs.select_related(
            "test_list_instance", "test_list_instance__test_list", "unit_test_info", "unit_test_info__test",
            "created_by"
        )

    @admin.display(
        description=_l("Test List Name"),
        ordering="test_list_instance__test_list__name",
    )
    def test_list_name(self, obj):
        return obj.test_list_instance.test_list.name

    @admin.display(
        description=_l("Test Name"),
        ordering="unit_test_info__test__name",
    )
    def test_name(self, obj):
        return obj.unit_test_info.test.name

    @admin.display(
        description=_l("Unit Name"),
        ordering="unit_test_info__unit__number",
    )
    def unit_name(self, obj):
        return obj.unit_test_info.unit

    def has_add_permission(self, request):
        """testistinstancess are created via front end only"""
        return False


class ToleranceForm(forms.ModelForm):

    model = models.Tolerance

    def validate_unique(self):
        super().validate_unique()
        if not self.instance.pk:
            params = forms.model_to_dict(self.instance)
            params.pop("id")
            if models.Tolerance.objects.filter(**params).count() > 0:
                errs = [_("Duplicate Tolerance. A Tolerance with these values already exists")]
                self._update_errors({forms.models.NON_FIELD_ERRORS: errs})


class ToleranceAdmin(BasicSaveUserAdmin):
    form = ToleranceForm
    list_filter = ["type"]

    class Media:
        js = (
            "admin/js/jquery.init.js",
            'jquery/js/jquery.min.js',
            "js/tolerance_admin.js",
        )

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        return qs.exclude(type=models.BOOLEAN)

    def has_change_permission(self, request, obj=None):

        if obj and obj.type == models.BOOLEAN:
            return False
        return super().has_change_permission(request, obj)


class AutoReviewAdmin(BaseQATrackAdmin):
    list_display = (str, "pass_fail", "status")
    list_editable = ["pass_fail", "status"]


class AutoReviewRuleSetAdminForm(forms.ModelForm):

    class Meta:
        model = models.AutoReviewRuleSet
        fields = '__all__'

    def clean_is_default(self):

        is_default = self.cleaned_data['is_default']
        if is_default and not self.initial.get('is_default', False):
            if self.instance.pk is None and models.AutoReviewRuleSet.objects.filter(is_default=True).exists():
                raise forms.ValidationError(
                    _("There must be one default auto review rule set. Edit another rule set to be default first.")
                )
        return is_default


class AutoReviewRuleSetAdmin(BaseQATrackAdmin):
    list_display = ("__str__", "is_default", 'get_rules_display')

    filter_horizontal = ("rules",)

    form = AutoReviewRuleSetAdminForm

    @admin.display(description=_l("Rules"))
    @mark_safe
    def get_rules_display(self, obj):
        return "<br>".join(str(rule) for rule in obj.rules.all().order_by('pass_fail'))


class AutoSaveAdmin(BaseQATrackAdmin):
    list_display = (
        "created", "created_by", 'modified', 'modified_by', 'unit', 'unit_test_collection', 'test_list', 'recover'
    )

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        return qs.select_related(
            "created_by", "modified_by", "unit_test_collection", "unit_test_collection__unit", "test_list"
        )

    def unit(self, obj):
        return obj.unit_test_collection.unit.name

    @mark_safe
    def recover(self, obj):
        href = reverse("perform_qa", kwargs={'pk': obj.unit_test_collection_id}) + "?autosave_id=%d" % obj.pk
        title = _("Click to continue this auto saved session")
        return '<a href="%s" title="%s">%s</a>' % (href, title, _("Recover"))


admin.site.register([models.Tolerance], ToleranceAdmin)
admin.site.register([models.AutoReviewRule], AutoReviewAdmin)
admin.site.register([models.AutoReviewRuleSet], AutoReviewRuleSetAdmin)
admin.site.register([models.AutoSave], AutoSaveAdmin)
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
