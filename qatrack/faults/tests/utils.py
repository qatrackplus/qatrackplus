import random
import string

from django.utils import timezone
from qatrack.faults import models
from qatrack.qa.tests import utils as qa_utils


def create_fault(unit=None, occurred=None, fault_type=None, user=None, modality=None):

    user = user or qa_utils.create_user()
    unit = unit or qa_utils.create_unit()
    fault_type = fault_type or create_fault_type()
    occurred = occurred or timezone.now()

    f = models.Fault.objects.create(
        unit=unit,
        modality=modality,
        created_by=user,
        modified_by=user,
        occurred=occurred,
    )
    try:
        for ft in fault_type:
            f.fault_types.add(ft)
    except TypeError:
        f.fault_types.add(fault_type)

    return f


def create_fault_type(code="", slug="", description=""):
    code = code or ''.join(random.choices(string.ascii_letters, k=10))
    return models.FaultType.objects.create(
        code=code,
        slug=slug,
        description=description,
    )


def create_fault_review_group(group=None, required=True):

    group = group or qa_utils.create_group()
    return models.FaultReviewGroup.objects.create(
        group=group,
        required=required,
    )


def create_fault_review(fault=None, review_group=None, reviewed_by=None, reviewed=None):

    reviewed = reviewed or timezone.now()
    if review_group is False:
        review_group = None
    elif review_group is None:
        review_group = create_fault_review_group()

    fault = fault or create_fault()
    reviewed_by = reviewed_by or qa_utils.create_user()

    return models.FaultReviewInstance.objects.create(
        reviewed=reviewed,
        reviewed_by=reviewed_by,
        fault=fault,
        fault_review_group=review_group,
    )
