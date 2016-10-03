from django.dispatch import receiver, Signal
from django.db.models.signals import pre_save, post_save, post_delete

from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType

from . import models


def loaded_from_fixture(kwargs):
    return kwargs.get("raw", False)


testlist_complete = Signal(providing_args=["instance", "created"])


def update_last_instances(test_list_instance):
    try:
        last_instance = models.TestListInstance.objects.complete().filter(
            unit_test_collection=test_list_instance.unit_test_collection
        ).latest("work_completed")
    except models.TestListInstance.DoesNotExist:
        last_instance = None
    except models.UnitTestCollection.DoesNotExist:
        # this will occur when a UnitTestCollection deletion cascades and
        # deletes all test_list_instances associated with it.
        # in that case it doesn't make sense to try to update anything
        return

    cycle_ids = models.TestListCycle.objects.filter(
        test_lists=test_list_instance.test_list
    ).values_list("pk", flat=True)
    cycle_ct = ContentType.objects.get_for_model(models.TestListCycle)

    test_list_ids = [test_list_instance.test_list.pk]
    list_ct = ContentType.objects.get_for_model(models.TestList)

    to_update = [(cycle_ct, cycle_ids), (list_ct, test_list_ids)]

    for ct, object_ids in to_update:

        utcs = models.UnitTestCollection.objects.filter(
            content_type=ct,
            object_id__in=object_ids,
            unit=test_list_instance.unit_test_collection.unit,
        )

        for utc in utcs:
            utc.last_instance = last_instance
            due_date = utc.calc_due_date()

            # Use update here rather than just calling utc.save()
            # since utc.save kicks off a bunch of other db queries
            # due to the UnitTestCollection post_save signal
            models.UnitTestCollection.objects.filter(pk=utc.pk).update(
                due_date=due_date,
                last_instance=last_instance,
            )


def get_or_create_unit_test_info(unit, test, assigned_to=None, active=True):

    uti, created = models.UnitTestInfo.objects.get_or_create(
        unit=unit,
        test=test,
    )

    if created:
        uti.assigned_to = assigned_to
        uti.active = active
        uti.save()
    return uti


def find_assigned_unit_test_collections(collection):
    """take a test collection (eg test list, sub list or test list cycle) and return
    the units that it is a part of
    """

    all_parents = {
        ContentType.objects.get_for_model(collection): [collection],
    }

    parent_types = [x._meta.model_name + "_set" for x in models.TestCollectionInterface.__subclasses__()]

    for parent_type in parent_types:

        if hasattr(collection, parent_type):
            parents = getattr(collection, parent_type).all()
            if parents.count() > 0:
                ct = ContentType.objects.get_for_model(parents[0])
                try:
                    all_parents[ct].extend(list(parents))
                except KeyError:
                    all_parents[ct] = list(parents)

    assigned_utcs = []
    for ct, objects in list(all_parents.items()):
        utcs = models.UnitTestCollection.objects.filter(
            object_id__in=[x.pk for x in objects],
            content_type=ct,
        ).select_related("unit", "assigned_to")
        assigned_utcs.extend(utcs)
    return list(set(assigned_utcs))


def update_unit_test_infos(collection):
    """find out which units this test_list is assigned to and make
    sure there are UnitTestInfo's for each Unit, Test pair"""

    all_tests = collection.all_tests()

    assigned_utcs = find_assigned_unit_test_collections(collection)

    for utc in assigned_utcs:
        existing_uti_units = models.UnitTestInfo.objects.filter(
            unit=utc.unit,
            test__in=all_tests,
        ).select_related("test")

        existing_tests = [x.test for x in existing_uti_units]
        missing_utis = [x for x in all_tests if x not in existing_tests]
        for test in missing_utis:
            get_or_create_unit_test_info(
                unit=utc.unit,
                test=test,
                assigned_to=utc.assigned_to,
                active=True
            )


@receiver(pre_save, sender=models.Test)
def on_test_save(*args, **kwargs):
    """Ensure that model validates on save"""
    if not loaded_from_fixture(kwargs):

        test = kwargs["instance"]
        if test.type is not models.BOOLEAN:
            return

        unit_assignments = models.UnitTestInfo.objects.filter(test=test)

        for ua in unit_assignments:
            if ua.reference and ua.reference.value not in (0., 1.,):
                raise ValidationError("Can't change test type to %s while this test is still assigned to %s with a non-boolean reference" % (test.type, ua.unit.name))


@receiver(post_save, sender=models.TestListInstance)
def on_test_list_instance_saved(*args, **kwargs):
    """set last instance for UnitTestInfo"""

    if not loaded_from_fixture(kwargs):
        update_last_instances(kwargs["instance"])


@receiver(post_delete, sender=models.TestListInstance)
def on_test_list_instance_deleted(*args, **kwargs):
    """update last_instance if available"""
    update_last_instances(kwargs["instance"])


@receiver(post_save, sender=models.UnitTestCollection)
def list_assigned_to_unit(*args, **kwargs):
    """UnitTestCollection was saved.  Create UnitTestInfo's for all Tests."""
    if not loaded_from_fixture(kwargs):
        utc = kwargs["instance"]
        tests_object = utc.content_type.get_object_for_this_type(pk=utc.object_id)
        update_unit_test_infos(tests_object)


@receiver(post_save, sender=models.TestListMembership)
def test_added_to_list(*args, **kwargs):
    """
    Test was added to a list (or sublist). Find all units this list
    is performed on and create UnitTestInfo for the Unit, Test pair.
    """
    if (not loaded_from_fixture(kwargs)):
        update_unit_test_infos(kwargs["instance"].test_list)


@receiver(post_save, sender=models.TestList)
def test_list_saved(*args, **kwargs):
    """TestList was saved. Recreate any UTI's that may have been deleted in past"""
    if not loaded_from_fixture(kwargs):
        update_unit_test_infos(kwargs["instance"])


@receiver(post_save, sender=models.TestListCycleMembership)
def test_list_added_to_cycle(*args, **kwargs):
    """
    Test List was added to a cycle . Find all units this list
    is performed on and create UnitTestInfo for the Unit, Test pair.
    """
    if (not loaded_from_fixture(kwargs)):
        update_unit_test_infos(kwargs["instance"].test_list)
