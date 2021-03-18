import random
import string

from django.utils import timezone
from qatrack.faults import models
from qatrack.qa.tests import utils as qa_utils


def create_fault(unit=None, occurred=None, fault_type=None, user=None):

    user = user or qa_utils.create_user()
    unit = unit or qa_utils.create_unit()
    fault_type = fault_type or create_fault_type()
    occurred = occurred or timezone.now()

    return models.Fault.objects.create(
        unit=unit,
        created_by=user,
        modified_by=user,
        occurred=occurred,
        fault_type=fault_type,
    )


def create_fault_type(code="", slug="", description=""):
    code = code or ''.join(random.choices(string.ascii_letters, k=10))
    return models.FaultType.objects.create(
        code=code,
        slug=slug,
        description=description,
    )
