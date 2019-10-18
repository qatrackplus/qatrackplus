from qatrack.qa import models
from qatrack.qa.utils import copy_unit_config
from qatrack.units import models as umodels


def run(*args):

    from_number, to_number = args
    from_ = umodels.Unit.objects.get(number=from_number)
    to_ = umodels.Unit.objects.get(number=to_number)

    copy_unit_config(from_, to_)
