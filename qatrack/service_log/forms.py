
from django import forms
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Field, ObjectDoesNotExist, Q
from django.forms.utils import flatatt
from django.forms.widgets import Select
from django.utils import timezone
from django.utils.dateparse import parse_duration
from django.utils.encoding import force_text
from django.utils.html import conditional_escape, format_html, escape
from django.utils.safestring import mark_safe
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

    if seconds > 0 and minutes < 1 and hours == 0:
        return '00:01'

    return '{:02d}:{:02d}'.format(hours, minutes)


class SelectWithOptionTitles(Select):

    def __init__(self, attrs=None, choices=(), model=None):
        super(SelectWithOptionTitles, self).__init__(attrs=attrs, choices=choices)
        self.model = model

    def render_option(self, selected_choices, option_value, option_label):
        if option_value in [None, '']:
            option_value = ''
            title = '------'
        else:
            objekt = self.model.objects.get(pk=option_value)
            title = objekt.description or ''
        option_value = force_text(option_value)
        if option_value in selected_choices:
            selected_html = mark_safe(' selected="selected"')
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''

        return format_html('<option value="{}" title="{}" {}>{}</option>', option_value, title, selected_html, force_text(option_label))


class HoursMinDurationField(forms.DurationField):

    def __init__(self, *args, **kwargs):
        super(HoursMinDurationField, self).__init__(*args, **kwargs)
        self.widget.attrs.update({'class': 'inputmask'})

    def prepare_value(self, value):
        if isinstance(value, timezone.timedelta):
            return duration_string_hours_mins(value)
        return value

    def to_python(self, value):
        print(value)
        if value is not None:
            if value == '__:__':
                return None
            value = value.replace('_', '0').replace(':', '')
        if value in self.empty_values:
            return None
        if isinstance(value, timezone.timedelta):
            return value
        value = '{:04d}'.format(int(value))
        value = parse_duration(force_text(':'.join([value[:2], value[2:], '00'])))
        if value is None:
            raise ValidationError(self.error_messages['invalid'], code='invalid')

        return value


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
        time_classes += ' max-width-100'
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

    # def clean_time(self):
    #
    #     time = self.cleaned_data['time']
    #     print('------------------------')
    #     print(self.data['service_time'])
    #     print(time)
    #     # service_time = self.cle
    #     return time


HoursFormset = forms.inlineformset_factory(models.ServiceEvent, models.Hours, form=HoursForm, extra=2)


class FollowupForm(forms.ModelForm):

    unit_test_collection = forms.ModelChoiceField(queryset=qa_models.UnitTestCollection.objects.none())
    test_list_instance = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    all_reviewed = forms.BooleanField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = models.QAFollowup
        fields = ('unit_test_collection', 'test_list_instance', 'all_reviewed')

    def __init__(self, *args, **kwargs):
        self.service_event_instance = kwargs.pop('service_event_instance')
        self.unit_field = kwargs.pop('unit_field')
        super(FollowupForm, self).__init__(*args, **kwargs)

        if 'unit_field' in self.data and self.data['unit_field']:
            self.unit_field = u_models.Unit.objects.get(pk=self.data['unit_field'])

        if self.unit_field:
            uf_cache = cache.get('active_unit_test_collections_for_unit_%s' % self.unit_field.id, None)
            if not uf_cache:
                uf_cache = qa_models.UnitTestCollection.objects.filter(
                    unit=self.unit_field,
                    active=True
                ).order_by('name')
                cache.set('active_unit_test_collections_for_unit_%s' % self.unit_field.id, uf_cache)
            self.fields['unit_test_collection'].queryset = uf_cache

        else:
            self.fields['unit_test_collection'].widget.attrs.update({'disabled': True})

        if self.instance.test_list_instance:
            self.fields['unit_test_collection'].widget.attrs.update({'disabled': True})
            self.fields['unit_test_collection'].disabled = True
            self.initial['test_list_instance'] = self.instance.test_list_instance.id
            self.initial['all_reviewed'] = int(self.instance.test_list_instance.all_reviewed)
        else:
            self.initial['all_reviewed'] = 0

        self.fields['unit_test_collection'].widget.attrs.update({'class': 'followup-utc select2', 'data-prefix': self.prefix})
        self.fields['test_list_instance'].widget.attrs.update({'class': 'tli-instance'})
        self.fields['all_reviewed'].widget.attrs.update({'class': 'tli-all-reviewed'})

    def clean_unit_test_collection(self):
        utc = self.cleaned_data['unit_test_collection']
        return utc

    def clean_test_list_instance(self):
        tli_id = self.cleaned_data['test_list_instance']
        if tli_id is not None:
            return qa_models.TestListInstance.objects.get(pk=tli_id)
        return None


FollowupFormset = forms.inlineformset_factory(models.ServiceEvent, models.QAFollowup, form=FollowupForm, extra=2)


class ServiceEventMultipleField(forms.ModelMultipleChoiceField):

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


class SelectWithDisabledWidget(forms.Select):

    def render_option(self, selected_choices, option_value, option_label):
        option_value = force_text(option_value)
        if option_value in selected_choices:
            selected_html = ' selected="selected"'
        else:
            selected_html = ''
        disabled_html = ''
        title_html = ''
        if isinstance(option_label, dict):
            if dict.get(option_label, 'disabled'):
                disabled_html = ' disabled="disabled"'
            if dict.get(option_label, 'title'):
                title_html = ' title="%s"' % dict.get(option_label, 'title')
            option_label = option_label['label']
        return u'<option value="%s"%s%s%s>%s</option>' % (
            escape(option_value), selected_html, disabled_html, title_html, conditional_escape(force_text(option_label)))


class ServiceEventStatusField(forms.ChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            return models.ServiceEventStatus.objects.get(pk=value)
        except (ValueError, TypeError, ObjectDoesNotExist) as e:
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')

    def valid_value(self, ses):
        "Check to see if the provided value is a valid choice"
        if not isinstance(ses, models.ServiceEventStatus):
            return False
        return True


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

    def _coerce(self, data):
        if isinstance(data, str):
            return int(data)
        elif isinstance(data, qa_models.TestListInstance):
            return data.id
        else:
            return data


class ServiceEventForm(BetterModelForm):

    unit_field = forms.ModelChoiceField(queryset=models.Unit.objects.all(), label='Unit')
    service_area_field = forms.ModelChoiceField(
        queryset=models.ServiceArea.objects.all(), label='Service area',
        help_text=_('Select service area (must select unit first)')
    )
    duration_service_time = HoursMinDurationField(
        label=_('Service time (hh:mm)'), required=False,
        help_text=models.ServiceEvent._meta.get_field('duration_service_time').help_text
    )
    duration_lost_time = HoursMinDurationField(
        label=_('Lost time (hh:mm)'), required=False,
        help_text=models.ServiceEvent._meta.get_field('duration_lost_time').help_text
    )
    service_event_related_field = ServiceEventMultipleField(
        required=False, queryset=models.ServiceEvent.objects.none(),
        help_text=models.ServiceEvent._meta.get_field('service_event_related').help_text
    )
    is_review_required = forms.BooleanField(required=False)
    is_review_required_fake = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(), label=_('Review required'),
        help_text=models.ServiceEvent._meta.get_field('is_review_required').help_text
    )

    test_list_instance_initiated_by = TLIInitiatedField(required=False)

    initiated_utc_field = forms.ModelChoiceField(
        required=False, queryset=qa_models.UnitTestCollection.objects.none(), label='Initiated by',
        help_text=_('Test list instance that initiated this service event')
    )
    service_type = forms.ModelChoiceField(
        queryset=models.ServiceType.objects.all(), widget=SelectWithOptionTitles(model=models.ServiceType)
    )
    # service_status = ServiceEventStatusField(
    #     help_text=models.ServiceEvent._meta.get_field('service_status').help_text, widget=SelectWithDisabledWidget,
    #     queryset=models.ServiceEventStatus.objects.all()
    # )

    _classes = ['form-control']

    class Meta:

        model = models.ServiceEvent
        fieldsets = [
            ('hidden_fields', {
                'fields': ['test_list_instance_initiated_by', 'is_review_required'],
            }),
            ('service_status', {
               'fields': [
                   'service_status'
               ],
            }),
            ('left_fields', {
                'fields': [
                    'unit_field', 'service_area_field', 'service_type', 'is_review_required_fake',
                ],
            }),
            ('right_fields', {
                'fields': [
                    'datetime_service', 'service_event_related_field', 'initiated_utc_field',
                ],
            }),
            ('problem_and_safety', {
                'fields': [
                    'problem_description', 'safety_precautions',
                ]
            }),
            ('work_description', {
                'fields': [
                    'work_description'
                ]
            }),
            ('time_fields', {
                'fields': ['duration_service_time', 'duration_lost_time'],
            }),
            ('followup_fields', {
                'fields': ['qafollowup_notes'],
            })
        ]

    def __init__(self, *args, **kwargs):
        self.initial_ib = kwargs.pop('initial_ib', None)
        self.initial_u = kwargs.pop('initial_u', None)
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

        # If there are no saved instance yet
        if is_new:

            # if url param 'ib' is included
            if self.initial_ib and 'test_list_instance_initiated_by' not in self.data:
                initial_ib_tli = qa_models.TestListInstance.objects.get(id=self.initial_ib)
                self.initial['test_list_instance_initiated_by'] = initial_ib_tli.id
                initial_ib_utc = initial_ib_tli.unit_test_collection
                initial_ib_utc_u = initial_ib_utc.unit
                self.initial['unit_field'] = initial_ib_utc_u
                self.initial['initiated_utc_field'] = initial_ib_utc
                self.fields['service_area_field'].queryset = models.ServiceArea.objects.filter(units=initial_ib_utc_u)
                i_utc_f_qs = qa_models.UnitTestCollection.objects.filter(unit=initial_ib_utc_u, active=True).order_by('name')
                self.fields['initiated_utc_field'].choices = (('', '---------'),) + tuple(((utc.id, '(%s) %s' % (utc.frequency if utc.frequency else 'Ad Hoc', utc.name)) for utc in i_utc_f_qs))

            if self.initial_u and 'unit_field' not in self.data:
                try:
                    initial_unit = u_models.Unit.objects.get(pk=self.initial_u)
                    self.initial['unit_field'] = initial_unit
                    self.fields['service_area_field'].queryset = models.ServiceArea.objects.filter(units=initial_unit)
                    i_utc_f_qs = qa_models.UnitTestCollection.objects.filter(unit=initial_unit, active=True).order_by('name')
                    self.fields['initiated_utc_field'].choices = (('', '---------'),) + tuple(((utc.id, '(%s) %s' %(utc.frequency if utc.frequency else 'Ad Hoc', utc.name)) for utc in i_utc_f_qs))
                except ObjectDoesNotExist:
                    pass

            if 'service_event_related_field' in self.data:
                self.fields['service_event_related_field'].queryset = models.ServiceEvent.objects.filter(
                    pk__in=self.data.getlist('service_event_related_field')
                )

            if 'unit_field' not in self.data and 'unit_field' not in self.initial:
                self.fields['service_area_field'].widget.attrs.update({'disabled': True})
                self.fields['service_event_related_field'].widget.attrs.update({'disabled': True})
                self.fields['initiated_utc_field'].widget.attrs.update({'disabled': True})

            if 'unit_field' in self.data:
                if self.data['unit_field']:
                    self.fields['service_area_field'].queryset = models.ServiceArea.objects.filter(units=self.data['unit_field'])
                    self.fields['initiated_utc_field'].queryset = qa_models.UnitTestCollection.objects.filter(unit=self.data['unit_field'])
                else:
                    self.fields['service_area_field'].widget.attrs.update({'disabled': True})
                    self.fields['service_event_related_field'].widget.attrs.update({'disabled': True})
                    self.fields['initiated_utc_field'].widget.attrs.update({'disabled': True})

            choices = []
            for ses in models.ServiceEventStatus.objects.all():
                value = ses.id
                label = ses.name
                if not self.user.has_perm('service_log.review_serviceevent') and not ses.is_review_required:
                    choices.append(
                        (value, {'label': label, 'disabled': True, 'title': _('Cannot select status: Permission denied')})
                    )
                elif ses.rts_qa_must_be_reviewed:
                    choices.append(
                        (value, {'label': label, 'disabled': True, 'title': _('Cannot select status: Unreviewed RTS QA')})
                    )
                else:
                    choices.append((value, label))
            self.fields['service_status'] = ServiceEventStatusField(choices=choices, widget=SelectWithDisabledWidget)

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
            self.initial['unit_field'] = unit
            self.initial['service_area_field'] = self.instance.unit_service_area.service_area
            self.initial['service_event_related_field'] = self.instance.service_event_related.all()
            self.fields['service_event_related_field'].queryset = self.initial['service_event_related_field']
            self.fields['service_area_field'].queryset = models.ServiceArea.objects.filter(units=unit)

            if self.instance.service_type.is_review_required:
                self.fields['is_review_required_fake'].widget.attrs.update({'disabled': True})

            self.initial['is_review_required_fake'] = self.instance.is_review_required

            # if not self.user.has_perm('service_log.change_serviceeventstatus'):
            #     self.fields['service_status'].widget.attrs.update({'disabled': True})

            choices = []
            unreviewed_qa_status = qa_models.TestInstanceStatus.objects.filter(is_default=True).first()
            for ses in models.ServiceEventStatus.objects.all():
                value = ses.id
                label = ses.name
                if not self.user.has_perm('service_log.review_serviceevent') and not (ses.is_review_required or ses.pk == self.instance.service_status.id):
                    choices.append((value, {'label': label, 'disabled': True, 'title': 'Cannot select status: Permission denied'}))
                # elif ses.rts_qa_must_be_reviewed and self.instance.qafollowup_set.filter(Q(test_list_instance__isnull=True) | Q(test_list_instance__all_reviewed=False)).exists():
                #     choices.append((value, {'label': label, 'disabled': True, 'title': 'Cannot select status: %s RTS QA' % unreviewed_qa_status.name}))
                else:
                    choices.append((value, label))
            self.fields['service_status'] = ServiceEventStatusField(choices=choices, widget=SelectWithDisabledWidget)

            if self.instance.test_list_instance_initiated_by:
                self.initial['initiated_utc_field'] = self.instance.test_list_instance_initiated_by.unit_test_collection
                self.initial['test_list_instance_initiated_by'] = str(self.instance.test_list_instance_initiated_by.id)

            i_utc_f_qs = qa_models.UnitTestCollection.objects.select_related('frequency').filter(unit=unit, active=True).order_by('name')
            self.fields['initiated_utc_field'].choices = (('', '---------'),) + tuple(((utc.id, '(%s) %s' % (utc.frequency if utc.frequency else 'Ad Hoc', utc.name)) for utc in i_utc_f_qs))

        for f in ['safety_precautions', 'problem_description', 'work_description', 'qafollowup_notes']:
            self.fields[f].widget.attrs.update({'rows': 3, 'class': 'autosize'})

        select2_fields = [
            'unit_field', 'service_area_field', 'service_type', 'service_status',
            'initiated_utc_field'
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

        for f in ['is_review_required_fake', 'is_review_required']:
            classes = self.fields[f].widget.attrs.get('class', '')
            classes = classes.replace('form-control', '')
            self.fields[f].widget.attrs.update({'class': classes})

        self.fields['initiated_utc_field'].widget.attrs.update({'data-link': reverse('tli_select')})

    def save(self, *args, **kwargs):
        unit = self.cleaned_data.get('unit_field')
        service_area = self.cleaned_data.get('service_area_field')
        usa = models.UnitServiceArea.objects.get(unit=unit, service_area=service_area)

        if self.cleaned_data['service_type'].is_review_required:
            self.instance.is_review_required = True

        self.instance.unit_service_area = usa
        super(ServiceEventForm, self).save(*args, **kwargs)

        return self.instance

    def clean(self):
        super(ServiceEventForm, self).clean()
        if 'initiated_utc_field' in self._errors:
            del self._errors['initiated_utc_field']

        # Check for incomplete and unreviewed RTS QA if status.rts_qa_must_be_reviewed = True
        if self.cleaned_data['service_status'].rts_qa_must_be_reviewed:
            raize = False
            for k, v in self.data.items():
                if k.startswith('followup-') and k.endswith('-id'):
                    prefix = k.replace('-id', '')
                    if prefix + '-unit_test_collection' in self.data and self.data[prefix + '-unit_test_collection'] != '':
                        if prefix + '-DELETE' not in self.data or self.data[prefix + '-DELETE'] != 'on':
                            if self.data[prefix + '-test_list_instance'] == '':
                                raize = True
                                break
                    else:
                        tli_id = self.data[prefix + '-test_list_instance']
                        if tli_id != '' and not qa_models.TestListInstance.objects.get(pk=tli_id).all_reviewed:
                            raize = True
                            break
            if raize:
                self._errors['service_status'] = ValidationError(
                    'Cannot select status: %s or incomplete RTS QA' % qa_models.TestInstanceStatus.objects.filter(
                        is_default=True
                    ).first().name
                )

        return self.cleaned_data
        # TODO add message when service event status chages due to review

    @property
    def classes(self):
        return ' '.join(self._classes)
