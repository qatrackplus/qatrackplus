from django.core.serializers.json import DjangoJSONEncoder
import numpy as np

NP_INT_TYPES = (
    np.int_,
    np.intc,
    np.intp,
    np.int8,
    np.int16,
    np.int32,
    np.int64,
    np.uint8,
    np.uint16,
    np.uint32,
    np.uint64,
)

NP_FLOAT_TYPES = (
    np.float_,
    np.float16,
    np.float32,
    np.float64,
)

serializing_methods = [
    'tolist',  # np.array,
    'to_list',
    'to_dict',  # pd.DataFrame,
]


class QATrackJSONEncoder(DjangoJSONEncoder):
    # inspired by https://github.com/illagrenan/django-numpy-json-encoder

    def default(self, o):
        if isinstance(o, NP_INT_TYPES):
            return int(o)
        elif isinstance(o, NP_FLOAT_TYPES):
            return float(o)
        elif isinstance(o, (range, zip, set,)):
            return list(o)

        for m in serializing_methods:
            method = getattr(o, m, None)
            if callable(method):
                return method()

        return super().default(o)
