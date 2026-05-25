from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_delete,
    pre_save,
)
from django.dispatch import Signal, receiver
from django.utils import timezone
from django_comments.models import Comment
from django_comments.signals import comment_was_posted

from qatrack.service_log import models as sl_models

from . import models


def loaded_from_fixture(kwargs):
    return kwargs.get("raw", False)


testlist_complete = Signal()


def update_last_instances(test_list_instance):
    utc = test_list_instance.unit_test_collection
    try:
        last_instance = models.TestListInstance.objects.complete().filter(
            unit_test_collection=utc
        ).latest("work_completed")
    except models.TestListInstance.DoesNotExist:
        last_instance = None
    except models.UnitTestCollection.DoesNotExist:
        # this will occur when a UnitTestCollection deletion cascades and
        # deletes all test_list_instances associated with it.
        # in that case it doesn't make sense to try to update anything
        return

    utc.last_instance = last_instance
    due_date = utc.calc_due_date()

    models.UnitTestCollection.objects.filter(pk=utc.pk).update(
        due_date=due_date,
        last_instance=last_instance,
    )


def handle_se_statuses_post_tli_delete(test_list_instance):

    se_rtsqa_qs = sl_models.ServiceEvent.objects.filter(
        returntoserviceqa__test_list_instance=test_list_instance, service_status__is_review_required=False
    )
    se_ib_qs = test_list_instance.serviceevents_initiated.filter(service_status__is_review_required=False)
    default_ses = sl_models.ServiceEventStatus.get_default()

    se_rtsqa_qs.update(service_status=default_ses)
    se_ib_qs.update(service_status=default_ses)


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


def testlistcycle_utcs(cycle):
    """
    Return all utcs which are assigned one of the above cycles
    Note: test list cycles can only be assigned directly to a UTC
    """
    if not cycle:
        return []

    parents = models.UnitTestCollection.objects.filter(
        object_id=cycle.pk,
        content_type__app_label='qa',
        content_type__model='testlistcycle',
    ).select_related("unit", "assigned_to")
    return list(parents)


def testlist_utcs(test_list):
    """Test list can be assigned to a Unit by being:
    a) directly assigned to a UTC
    b) as a sublist of a test list assigned to a UTC
    c) as part of a TLC assigned to a UTC
    d) as a sublist of a test list which is part of a TLC assigned to a UTC
    """

    test_lists = []
    cycles = []

    # case a)
    test_lists.append(test_list.pk)

    # case b)
    for sublist in test_list.sublist_set.all():
        test_lists.append(sublist.parent.pk)

        # case d
        cycles += list(sublist.parent.testlistcycle_set.values_list('pk', flat=True))

    # case c)
    cycles += list(test_list.testlistcycle_set.values_list('pk', flat=True))

    utcs_tl = models.UnitTestCollection.objects.filter(
        Q(
            object_id__in=test_lists,
            content_type__app_label='qa',
            content_type__model='testlist',
        ) | Q(
            object_id__in=cycles,
            content_type__app_label='qa',
            content_type__model='testlistcycle',
        )
    ).select_related("unit", "assigned_to")

    return list(utcs_tl)


def find_assigned_unit_test_collections(collection):
    """take a test collection (eg test list, sub list or test list cycle) and return
    the units that it is a part of
    """

    model_name = collection._meta.model_name
    if model_name == "testlist":
        return testlist_utcs(collection)
    elif model_name == "testlistcycle":
        return testlistcycle_utcs(collection)
    else:
        raise TypeError("Model type %s is not handled by find_assigned_unit_test_collections" % model_name)


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
                raise ValidationError(
                    "Can't change test type to %s while this test is still assigned to "
                    "%s with a non-boolean reference" % (test.type, ua.unit.name))


@receiver(testlist_complete)
def check_tli_flag(*args, **kwargs):
    """Flag this test list instance if required"""
    tli = kwargs["instance"]
    models.TestListInstance.objects.filter(pk=tli.pk).update(
        flagged=tli.testinstance_set.filter(
            Q(value=1, unit_test_info__test__flag_when=True) |
            Q(value=0, unit_test_info__test__flag_when=False)
        ).exists()
    )


@receiver(post_save, sender=models.TestListInstance)
def on_test_list_instance_saved(*args, **kwargs):
    """set last instance for UnitTestInfo"""

    if not loaded_from_fixture(kwargs):
        update_last_instances(kwargs["instance"])


@receiver(pre_delete, sender=models.TestListInstance)
def pre_test_list_instance_deleted(*args, **kwargs):
    """update last_instance if available"""
    handle_se_statuses_post_tli_delete(kwargs["instance"])


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


@receiver(post_save, sender=models.Sublist)
def sublist_added_to_list(*args, **kwargs):
    """
    Sublist was added to a list. Find all units this list
    is performed on and create UnitTestInfo for the Unit, Test pair.
    """
    if (not loaded_from_fixture(kwargs)):
        update_unit_test_infos(kwargs["instance"].parent)


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


@receiver(post_save, sender=models.AutoReviewRule)
@receiver(post_save, sender=models.AutoReviewRuleSet)
@receiver(post_save, sender=models.TestInstanceStatus)
@receiver(post_delete, sender=models.AutoReviewRule)
@receiver(post_delete, sender=models.AutoReviewRuleSet)
@receiver(post_delete, sender=models.TestInstanceStatus)
@receiver(m2m_changed, sender=models.AutoReviewRuleSet.rules.through)
def on_autoreviewrule_save(*args, **kwargs):
    """update auto review rule set cache"""
    if not loaded_from_fixture(kwargs):
        models.update_autoreviewruleset_cache()


@receiver(comment_was_posted, sender=Comment)
def check_approved_statuses(*args, **kwargs):

    if 'edit_tli' in kwargs and kwargs['edit_tli']:
        tli_id = kwargs['comment'].object_pk
        tli = models.TestListInstance.objects.get(pk=tli_id)

        default_status = sl_models.ServiceEventStatus.get_default()
        for f in tli.rtsqa_for_tli.all():
            if not f.service_event.service_status.is_review_required:
                f.service_event.service_status = default_status
                f.service_event.datetime_status_changed = timezone.now()
                f.service_event.user_status_changed_by = None
                f.service_event.save()
