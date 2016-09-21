
from django.core import exceptions, validators, checks
from django.core.exceptions import ValidationError
from django.db.models import Field
from django.forms import ModelForm, ModelChoiceField, Textarea
from django.forms.utils import flatatt, to_current_timezone
from django.utils.html import conditional_escape, format_html, html_safe
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

import models


class SelectizeModelChoiceField(ModelChoiceField):

    def to_python(self, value):
        try:
            return super(SelectizeModelChoiceField, self).to_python(value)
        except ValidationError:
            print '---------------------------'
            print self.queryset
            models.ProblemType.objects.create(name=value)
        return super(SelectizeModelChoiceField, self).to_python(value)


class ServiceEventForm(ModelForm):

    unit_field = ModelChoiceField(queryset=models.Unit.objects.all())
    service_area_field = ModelChoiceField(queryset=models.ServiceArea.objects.all())

    class Meta:

        model = models.ServiceEvent
        fields = (
            'unit_field',
            'service_area_field',
            'service_type',
            'service_event_related',
            'service_status',
            'user_physicist_reported_to',
            'user_therapist_reported_to',
            'problem_type',
            'datetime_service',
            'srn',
            'safety_precautions',
            'problem_description',
            'work_description',
            'duration_service_time',
            'duration_lost_time'
        )

