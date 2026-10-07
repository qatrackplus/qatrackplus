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

    def value_to_string(self, obj):
        """``value_to_string`` would otherwise call ``str`` on the value, which
        turns our dictionary into a Python repr that is not valid JSON. Return
        the object itself and let the serializer encode it."""
        return self.value_from_object(obj)

    def get_db_prep_save(self, value, *args, **kwargs):
        if value == "":
            return None
        if isinstance(value, dict):
            value = json.dumps(value, cls=DjangoJSONEncoder)
        return value
