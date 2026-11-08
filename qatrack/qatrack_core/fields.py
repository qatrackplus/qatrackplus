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
        """JSON text - not a Python repr, and not the dictionary itself.

        The default ``Field.value_to_string`` calls ``str()``, which turns a
        dictionary into a Python repr: single quotes, ``None``, ``True``. No JSON
        parser reads that back, so ``dumpdata`` produced a fixture ``loaddata``
        could not restore.

        Returning the dictionary instead fixes ``--format=json``, whose
        serializer encodes whatever it is handed, and breaks ``--format=xml``,
        whose writer takes characters. Django's XML serializer does encode a
        dict, but only for a field whose ``get_internal_type()`` is
        ``"JSONField"``; this one reports ``"TextField"``, because that is the
        column it has to stay. @copilot found that on c#12.

        So this returns the JSON *text*, which both serializers accept and
        ``to_python`` parses on the way back in - the round trip the fixture is
        for.
        """
        value = self.value_from_object(obj)
        if value is None:
            return value
        return json.dumps(value, cls=DjangoJSONEncoder)

    def get_db_prep_save(self, value, *args, **kwargs):
        if value == "":
            return None
        if isinstance(value, dict):
            value = json.dumps(value, cls=DjangoJSONEncoder)
        return value
