from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify

from qatrack.accounts.tests.utils import create_group, create_user
from qatrack.parts import models as p_models
from qatrack.qa import models as qa_models
from qatrack.qa.tests import utils as qa_utils
from qatrack.qatrack_core.tests.utils import get_next_id
from qatrack.service_log import models
from qatrack.units import models as u_models


def create_service_area(name=None):

    if name is None:
        name = 'service_area_%04d' % get_next_id(models.ServiceArea.objects.order_by('id').last())

    sa, _ = models.ServiceArea.objects.get_or_create(name=name)

    return sa


def create_unit_service_area(unit=None, service_area=None):

    if unit is None:
        unit = qa_utils.create_unit()
    if service_area is None:
        service_area = create_service_area()

    usa, _ = models.UnitServiceArea.objects.get_or_create(unit=unit, service_area=service_area)

    return usa


def create_service_event_status(name=None, is_default=False, is_review_required=True,
                                rts_qa_must_be_reviewed=False, colour=settings.DEFAULT_COLOURS[0]):

    if name is None:
        name = 'service_event_status_%04d' % get_next_id(models.ServiceEventStatus.objects.order_by('id').last())

    ses, _ = models.ServiceEventStatus.objects.get_or_create(
        name=name, is_default=is_default, is_review_required=is_review_required,
        rts_qa_must_be_reviewed=rts_qa_must_be_reviewed, colour=colour
    )

    return ses


def create_service_type(name=None, is_review_required=False, is_active=True):

    if name is None:
        name = 'service_type_%04d' % get_next_id(models.ServiceType.objects.order_by('id').last())

    st, _ = models.ServiceType.objects.get_or_create(
        name=name, is_review_required=is_review_required, is_active=is_active
    )

    return st


def create_service_event(unit_service_area=None, service_type=None, service_status=None, user_created_by=None,
                         datetime_service=timezone.now(), problem_description='problem_description',
                         is_review_required=False, datetime_created=timezone.now(),
                         add_test_list_instance_initiated_by=False, service_time=None, lost_time=None):

    if unit_service_area is None:
        unit_service_area = create_unit_service_area()
    if service_type is None:
        service_type = create_service_type()
    if service_status is None:
        service_status = create_service_event_status()
    if user_created_by is None:
        user_created_by = create_user()

    se, _ = models.ServiceEvent.objects.get_or_create(
        unit_service_area=unit_service_area, service_type=service_type, service_status=service_status,
        user_created_by=user_created_by, datetime_service=datetime_service, problem_description=problem_description,
        is_review_required=is_review_required, datetime_created=datetime_created, duration_service_time=service_time,
        duration_lost_time=lost_time
    )

    if add_test_list_instance_initiated_by:
        if isinstance(add_test_list_instance_initiated_by, models.TestListInstance):
            se.test_list_instance_initiated_by = add_test_list_instance_initiated_by
        else:
            utc = qa_utils.create_unit_test_collection(unit=unit_service_area.unit)
            se.test_list_instance_initiated_by = qa_utils.create_test_list_instance(unit_test_collection=utc)
        se.save()

    return se


def create_third_party(vendor=None, first_name=None, last_name=None):

    if vendor is None:
        vendor = qa_utils.create_vendor()
    if first_name is None:
        first_name = 'first_name_%04d' % get_next_id(models.ThirdParty.objects.order_by('id').last())
    if last_name is None:
        last_name = 'last_name_%04d' % get_next_id(models.ThirdParty.objects.order_by('id').last())

    tp, _ = models.ThirdParty.objects.get_or_create(vendor=vendor, first_name=first_name, last_name=last_name)

    return tp


def create_hours(service_event=None, third_party=None, user=None, time=timezone.timedelta(hours=1)):

    if service_event is None:
        service_event = create_service_event()
    if third_party is None and user is None:
        user = create_user()

    h, _ = models.Hours.objects.get_or_create(
        service_event=service_event, third_party=third_party, user=user, time=time
    )

    return h


def create_return_to_service_qa(service_event=None, unit_test_collection=None, user_assigned_by=None,
                                datetime_assigned=timezone.now(), add_test_list_instance=False):

    if service_event is None:
        service_event = create_service_event()
    if unit_test_collection is None:
        unit_test_collection = qa_utils.create_unit_test_collection()
    if user_assigned_by is None:
        user_assigned_by = create_user()

    rtsqa, _ = models.ReturnToServiceQA.objects.get_or_create(
        service_event=service_event, unit_test_collection=unit_test_collection, user_assigned_by=user_assigned_by,
        datetime_assigned=datetime_assigned
    )

    if add_test_list_instance:
        if isinstance(add_test_list_instance, qa_models.TestListInstance):
            tli = add_test_list_instance
        else:
            tli = qa_utils.create_test_list_instance(unit_test_collection=unit_test_collection)
        rtsqa.test_list_instance = tli
        rtsqa.save()

    return rtsqa


def create_group_linker(group=None, name=None):

    if group is None:
        group = create_group()
    if name is None:
        name = 'group_linker_%04d' % get_next_id(models.GroupLinker.objects.order_by('id').last())

    gl, _ = models.GroupLinker.objects.get_or_create(group=group, name=name)

    return gl


def create_group_linker_instance(group_linker=None, user=None, service_event=None, datetime_linked=timezone.now()):

    if group_linker is None:
        group_linker = create_group_linker()
    if user is None:
        user = create_user()
    if service_event is None:
        service_event = create_service_event()

    gli, _ = models.GroupLinkerInstance.objects.get_or_create(
        group_linker=group_linker, user=user, service_event=service_event, datetime_linked=datetime_linked
    )

    return gli


def create_part_category(name=None):

    if name is None:
        name = 'part_category_%04d' % get_next_id(p_models.PartCategory.objects.order_by('id').last())

    pc, _ = p_models.PartCategory.objects.get_or_create(name=name)

    return pc


def create_part(part_category=None, part_number=None, name='description', add_storage=False, quantity_min=0,
                quantity_current=1, alt_part_number=None):

    if part_category is None:
        part_category = create_part_category()
    if part_number is None:
        part_number = str(get_next_id(p_models.PartCategory.objects.order_by('id').last()))

    p, _ = p_models.Part.objects.get_or_create(
        part_category=part_category, part_number=part_number, name=name, quantity_min=quantity_min,
        quantity_current=quantity_current, alt_part_number=alt_part_number
    )

    if add_storage:
        s = create_storage()
        create_part_storage_collection(part=p, storage=s, quantity=quantity_current)
        p.save()

    return p


def create_storage(room=None, location='shelf', quantity=1):

    if room is None:
        room = create_room()

    s, _ = p_models.Storage.objects.get_or_create(room=room, location=location)

    return s


def create_room(site=None, name=None):

    if name is None:
        name = 'room_%04d' % get_next_id(p_models.Room.objects.order_by('id').last())
    if site is None:
        site = create_site()

    r, _ = p_models.Room.objects.get_or_create(name=name, site=site)

    return r


def create_site(name=None):

    if name is None:
        name = 'site_%04d' % get_next_id(u_models.Site.objects.order_by('id').last())

    slug = slugify(name)
    s, _ = u_models.Site.objects.get_or_create(name=name, slug=slug)

    return s


def create_supplier(name=None):

    if name is None:
        name = 'supplier_%04d' % get_next_id(p_models.Supplier.objects.order_by('id').last())

    s, _ = p_models.Supplier.objects.get_or_create(name=name)

    return s


def create_part_storage_collection(part=None, storage=None, quantity=1):

    if part is None:
        part = create_part()
    if storage is None:
        storage = create_storage()

    psc, _ = p_models.PartStorageCollection.objects.get_or_create(
        part=part, storage=storage, quantity=quantity
    )

    return psc
