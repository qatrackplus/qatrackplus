import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class JSONField(models.TextField):

    def to_python(self, value):
        if value == "":
            return None

        try:
            if isinstance(value, str):
                return json.loads(value)
        except ValueError:
            pass
        return value

    def from_db_value(self, value, *args):
        return self.to_python(value)

    def get_db_prep_save(self, value, *args, **kwargs):
        if value == "":
            return None

        if isinstance(value, str):
            # ensure we are actually saving a valid JSON string
            json.dumps(json.loads(value))
        if isinstance(value, dict):
            value = json.dumps(value, cls=DjangoJSONEncoder)
        return value

    def value_to_string(self, obj):
        """value_to_string normally just calls
        `str(self.value_from_object(obj)` to serialize the field value, but we
        want to let the json serializer handle our dictionary/object so we skip
        stringifying here"""
        return self.value_from_object(obj)
