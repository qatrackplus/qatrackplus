
from django import forms
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Field, ObjectDoesNotExist, Q
from django.forms.utils import flatatt
from django.forms.widgets import DateTimeInput
from django.utils import timezone
from django.utils.dateparse import parse_duration
from django.utils.encoding import force_text
from django.utils.html import conditional_escape, format_html, html_safe
from django.utils.translation import ugettext as _
from form_utils.forms import BetterModelForm

from qatrack.service_log import models
from qatrack.qa import models as qa_models
from qatrack.units import models as u_models


def duration_string_hours_mins(duration):

    seconds = duration.seconds
    minutes = seconds // 60

    hours = minutes // 60
    minutes %= 60
    hours %= 60

    if minutes < 1 and hours == 0:
        return '00:01'

    return '{:02d}:{:02d}'.format(hours, minutes)


class HoursMinDurationField(forms.DurationField):

    def __init__(self, *args, **kwargs):
        super(HoursMinDurationField, self).__init__(*args, **kwargs)
        self.widget.attrs.update({'class': 'inputmask'})

    def prepare_value(self, value):
        if isinstance(value, timezone.timedelta):
            return duration_string_hours_mins(value)
        return value

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, timezone.timedelta):
            return value
        value += ':00'
        value = parse_duration(force_text(value))
        if value is None:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        return value


class ProblemTypeModelChoiceField(forms.ModelChoiceField):

    def to_python(self, value):
        try:
            return super(ProblemTypeModelChoiceField, self).to_python(value)
        except ValidationError as e:
            if e.code == 'invalid_choice':
                models.ProblemType.objects.create(name=value)
                self.queryset = models.ProblemType.objects.all()
        return super(ProblemTypeModelChoiceField, self).to_python(value)


class UTCModelChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return obj.test_objects_name()


class UserModelChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, user):
        return user.username if not user.first_name or not user.last_name else user.last_name + ', ' + user.first_name
        # return user.get_full_name()


class HoursForm(forms.ModelForm):

    user_or_thirdparty = forms.ChoiceField(label='User or third party')
    time = HoursMinDurationField(help_text='Hours : Minutes')

    class Meta:
        model = models.Hours
        fields = ('time', 'user_or_thirdparty')

    def __init__(self, *args, **kwargs):
        super(HoursForm, self).__init__(*args, **kwargs)

        choices = [(None, '---------')]
        perm = Permission.objects.get(codename='can_have_hours')
        if self.instance.user:
            users = User.objects.filter(Q(groups__permissions=perm, is_active=True) | Q(user_permissions=perm, is_active=True) | Q(pk=self.instance.user.id)).distinct().order_by('last_name')
        else:
            users = User.objects.filter(Q(groups__permissions=perm, is_active=True) | Q(user_permissions=perm, is_active=True)).distinct().order_by('last_name')
        for user in users:
            name = user.username if not user.first_name or not user.last_name else user.last_name + ', ' + user.first_name
            choices.append(('user-' + str(user.id), name))
        for tp in models.ThirdParty.objects.all():
            choices.append(('tp-' + str(tp.id), str(tp)))
        self.fields['user_or_thirdparty'].choices = choices

        self.fields['user_or_thirdparty'].widget.attrs.update({'class': 'select2'})
        time_classes = self.fields['time'].widget.attrs.get('class', '')
        time_classes += ' max-width-75'
        self.fields['time'].widget.attrs.update({'class': time_classes})

        if self.instance.user:
            self.initial['user_or_thirdparty'] = 'user-' + str(self.instance.user.id)
        elif self.instance.third_party:
            self.initial['user_or_thirdparty'] = 'tp-' + str(self.instance.third_party.id)

    def clean_user_or_thirdparty(self):

        u_or_tp = self.cleaned_data['user_or_thirdparty']
        obj_type, obj_id = u_or_tp.split('-')

        if not obj_type == 'user' and not obj_type == 'tp':
            raise ValidationError('Not a User or Third Party object.')

        return u_or_tp


HoursFormset = forms.inlineformset_factory(models.ServiceEvent, models.Hours, form=HoursForm, extra=2)


class FollowupForm(forms.ModelForm):

    unit_test_collection = UTCModelChoiceField(queryset=qa_models.UnitTestCollection.objects.none())
    test_list_instance = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = models.QAFollowup
        fields = ('unit_test_collection', 'test_list_instance')

    def __init__(self, *args, **kwargs):
        self.service_event_instance = kwargs.pop('service_event_instance')
        self.unit_field = kwargs.pop('unit_field')
        super(FollowupForm, self).__init__(*args, **kwargs)

        if self.unit_field:
            testlist_ct = ContentType.objects.get(app_label="qa", model="testlist")
            self.fields['unit_test_collection'].queryset = qa_models.UnitTestCollection.objects.filter(
                unit_id=self.unit_field,
                active=True,
                content_type=testlist_ct
            ).order_by('test_list__name')

        else:
            self.fields['unit_test_collection'].widget.attrs.update({'disabled': True})

        if self.instance.test_list_instance:
            self.fields['unit_test_collection'].widget.attrs.update({'disabled': True})
            self.fields['unit_test_collection'].disabled = True
            self.initial['test_list_instance'] = self.instance.test_list_instance.id

        self.fields['unit_test_collection'].widget.attrs.update({'class': 'followup-utc select2'})

    def is_valid(self):
        valid = super(FollowupForm, self).is_valid()
        return valid

    def clean_unit_test_collection(self):
        utc = self.cleaned_data['unit_test_collection']
        return utc

    def clean_test_list_instance(self):
        tli_id = self.cleaned_data['test_list_instance']
        if tli_id is not None:
            return qa_models.TestListInstance.objects.get(pk=tli_id)
        return None


FollowupFormset = forms.inlineformset_factory(models.ServiceEvent, models.QAFollowup, form=FollowupForm, extra=2)


class ServiceEventRelatedField(forms.ModelMultipleChoiceField):

    def clean(self, value):

        key = self.to_field_name or 'pk'
        # deduplicate given values to avoid creating many querysets or
        # requiring the database backend deduplicate efficiently.
        try:
            value = frozenset(value)
        except TypeError:
            # list of lists isn't hashable, for example
            raise ValidationError(
                self.error_messages['list'],
                code='list',
            )
        for pk in value:
            try:
                self.queryset.filter(**{key: pk})
            except (ValueError, TypeError):
                raise ValidationError(
                    self.error_messages['invalid_pk_value'],
                    code='invalid_pk_value',
                    params={'pk': pk},
                )
        qs = models.ServiceEvent.objects.filter(**{'%s__in' % key: value})
        pks = set(force_text(getattr(o, key)) for o in qs)
        for val in value:
            if force_text(val) not in pks:
                raise ValidationError(
                    self.error_messages['invalid_choice'],
                    code='invalid_choice',
                    params={'value': val},
                )
        return qs


class TLIInitiatedField(forms.IntegerField):

    label = ''
    required = False
    widget = forms.HiddenInput()

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            tli = qa_models.TestListInstance.objects.get(pk=value)
        except (ValueError, TypeError, qa_models.TestListInstance.DoesNotExist) as e:
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
        return tli


class ServiceEventForm(BetterModelForm):

    unit_field = forms.ModelChoiceField(queryset=models.Unit.objects.all(), label='Unit')
    service_area_field = forms.ModelChoiceField(
        queryset=models.ServiceArea.objects.all(), label='Service area',
        help_text=_('Select service area (must select unit first)')
    )
    duration_service_time = HoursMinDurationField(label=_('Service time'), required=False)
    duration_lost_time = HoursMinDurationField(label=_('Lost time'), required=False)
    problem_type = ProblemTypeModelChoiceField(
        queryset=models.ProblemType.objects.all(), required=False, to_field_name='name'
    )
    service_event_related_field = ServiceEventRelatedField(required=False, queryset=models.ServiceEvent.objects.none())
    is_approval_required = forms.BooleanField(required=False, label=_('Approval required'))

    test_list_instance_initiated_by = TLIInitiatedField()

    initiated_utc_field = forms.ModelChoiceField(
        queryset=qa_models.UnitTestCollection.objects.none(), label='Initiated by'
    )

    _classes = ['form-control']

    class Meta:

        model = models.ServiceEvent

        fieldsets = [
            ('hidden_fields', {
                'fields': ['test_list_instance_initiated_by'],
            }),
            ('required_fields', {
                'fields': [
                    'datetime_service', 'unit_field', 'service_area_field', 'service_type', 'is_approval_required',
                    'service_status', 'problem_description'
                ],
            }),
            ('optional_fields', {
                'fields': [
                    'problem_type', 'service_event_related_field', 'initiated_utc_field', 'work_description',
                    'safety_precautions'
                ],
            }),
            ('time_fields', {
                'fields': ['duration_service_time', 'duration_lost_time'],
            }),
        ]

    def __init__(self, *args, **kwargs):
        self.group_linkers = kwargs.pop('group_linkers', [])
        self.user = kwargs.pop('user', None)
        super(ServiceEventForm, self).__init__(*args, **kwargs)

        is_new = self.instance.id is None
        is_bound = self.is_bound

        g_fields = []
        self.g_link_dict = {}
        for g_link in self.group_linkers:
            field_name = 'group_linker_%s' % g_link.id

            self.g_link_dict[field_name] = {
                'g_link': g_link,
                # 'instance': None
            }
            # if not is_new:
            try:
                g_link_instance = models.GroupLinkerInstance.objects.get(group_linker=g_link, service_event=self.instance)
                self.initial[field_name] = g_link_instance.user
                queryset = User.objects.filter(Q(groups=g_link.group, is_active=True) | Q(pk=g_link_instance.user.id)).distinct().order_by('last_name')
                # self.g_link_dict[field_name]['instance'] = g_link_instance
            except ObjectDoesNotExist:
                queryset = User.objects.filter(groups=g_link.group, is_active=True).order_by('last_name')

            self.fields[field_name] = UserModelChoiceField(
                queryset=queryset,
                help_text=g_link.help_text, label=g_link.name, required=False
            )
            self.fields[field_name].widget.attrs.update({'class': 'select2'})

            g_fields.append(field_name)
        self._fieldsets.append(('g_link_fields', {'fields': g_fields}))

        # If there is no saved instance yet
        if is_new:

            if 'service_event_related_field' in self.data:
                self.fields['service_event_related_field'].queryset = models.ServiceEvent.objects.filter(
                    pk__in=self.data.getlist('service_event_related_field')
                )

            if 'unit_field' not in self.data:
                self.fields['service_area_field'].widget.attrs.update({'disabled': True})
                self.fields['service_event_related_field'].widget.attrs.update({'disabled': True})
                self.fields['initiated_utc_field'].widget.attrs.update({'disabled': True})

            else:
                if self.data['unit_field']:
                    self.fields['service_area_field'].queryset = models.ServiceArea.objects.filter(units=self.data['unit_field'])
                else:
                    self.fields['service_area_field'].widget.attrs.update({'disabled': True})
                    self.fields['service_event_related_field'].widget.attrs.update({'disabled': True})
                    self.fields['initiated_utc_field'].widget.attrs.update({'disabled': True})

            if not self.user.has_perm('service_log.can_approve_service_event'):
                self.fields['service_status'].queryset = models.ServiceEventStatus.objects.filter(is_approval_required=True)

            # some data wasn't attempted to be submitted already
            if not is_bound:
                self.initial['service_status'] = models.ServiceEventStatus.get_default()
                self.initial['datetime_service'] = timezone.now()

        # if we are editing a saved instance
        else:
            try:
                unit = u_models.Unit.objects.get(pk=self.data['unit_field'])
            except (ObjectDoesNotExist, KeyError):
                unit = self.instance.unit_service_area.unit
            # self.fields['unit_field'].widget.attrs.update({'disabled': True})
            self.initial['unit_field'] = unit
            self.initial['service_area_field'] = self.instance.unit_service_area.service_area
            # self.fields['service_event_related'].queryset = models.ServiceEvent.objects.exclude(id=self.instance.id)
            self.initial['service_event_related_field'] = self.instance.service_event_related.all()
            self.fields['service_event_related_field'].queryset = self.initial['service_event_related_field']
            self.fields['service_area_field'].queryset = models.ServiceArea.objects.filter(units=unit)
            self.initial['problem_type'] = self.instance.problem_type

            if self.instance.service_type.is_approval_required:
                self.fields['is_approval_required'].widget.attrs.update({'disabled': True})

            if not self.user.has_perm('service_log.can_approve_service_event'):
                self.fields['service_status'].queryset = models.ServiceEventStatus.objects.filter(
                    Q(is_approval_required=True) | Q(pk=self.instance.service_status.id)
                ).distinct()

            if self.instance.test_list_instance_initiated_by:
                self.initial['initiated_utc_field'] = self.instance.test_list_instance_initiated_by.unit_test_collection
                self.initial['test_list_instance_initiated_by'] = self.instance.test_list_instance_initiated_by.id

            self.fields['initiated_utc_field'].queryset = qa_models.UnitTestCollection.objects.filter(unit=unit, active=True)

        for f in ['safety_precautions', 'problem_description', 'work_description']:
            self.fields[f].widget.attrs.update({'rows': 3, 'class': 'autosize'})

        select2_fields = [
            'unit_field', 'service_area_field', 'service_type', 'service_event_related_field', 'service_status',
            'problem_type', 'initiated_utc_field'
        ]
        for f in select2_fields:
            self.fields[f].widget.attrs['class'] = 'select2'

        for f in ['datetime_service']:
            self.fields[f].widget.attrs['class'] = 'daterangepicker-input'
            self.fields[f].widget.format = settings.INPUT_DATE_FORMATS[0]
            self.fields[f].input_formats = settings.INPUT_DATE_FORMATS
            self.fields[f].widget.attrs["title"] = settings.DATETIME_HELP
            self.fields[f].help_text = settings.DATETIME_HELP

        for f in ['duration_service_time', 'duration_lost_time']:
            classes = self.fields[f].widget.attrs.get('class', '')
            classes += ' max-width-100'
            self.fields[f].widget.attrs.update({'class': classes})

        for f in self.fields:
            classes = self.fields[f].widget.attrs.get('class', '')
            classes += ' %s' % self.classes
            self.fields[f].widget.attrs.update({'class': classes})

        for f in ['is_approval_required']:
            classes = self.fields[f].widget.attrs.get('class', '')
            classes = classes.replace('form-control', '')
            self.fields[f].widget.attrs.update({'class': classes})

        self.fields['initiated_utc_field'].widget.attrs.update({'data-link': reverse('tli_select')})

    def save(self, *args, **kwargs):
        print('--- ServiceEventForm.save ---')
        unit = self.cleaned_data.get('unit_field')
        service_area = self.cleaned_data.get('service_area_field')
        usa = models.UnitServiceArea.objects.get(unit=unit, service_area=service_area)
        # service_event_related = self.cleaned_data.get('service_event_related_field')[1:-1].replace("'", "").split(',')
        if self.cleaned_data['service_type'].is_approval_required:
            self.instance.is_approval_required = True

        # service_event_related = self.cleaned_data.get('service_event_related_field')
        # try:
        #     sers = models.ServiceEvent.objects.filter(pk__in=service_event_related)
        # except ValueError:
        #     sers = []
        self.instance.test_list_instance_initiated_by = self.cleaned_data.get('test_list_instance_initiated_by')
        self.instance.unit_service_area = usa
        super(ServiceEventForm, self).save(*args, **kwargs)
        # self.instance.save()
        # models.ServiceEvent.save()

        return self.instance

    @property
    def classes(self):
        return ' '.join(self._classes)


