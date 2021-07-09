from django.apps import apps
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.text import slugify
import recurrence

from qatrack.accounts.tests.utils import create_group, create_user
from qatrack.qa import models
from qatrack.qatrack_core.tests.utils import get_next_id
from qatrack.units.tests.utils import create_unit


def exists(app, model, field, value):
    a_model = apps.get_model(app, model)
    results = a_model.objects.filter(**{field: value})
    if len(results) > 0:
        return True
    return False


def create_category(name="cat", slug="cat", description="cat"):
    c, _ = models.Category.objects.get_or_create(name=name, slug=slug, description=description)
    c.save()
    return c


def create_status(name=None, slug=None, is_default=True, requires_review=True):

    if name is None:
        name = 'status_%04d' % get_next_id(models.TestInstanceStatus.objects.order_by('id').last())
    if slug is None:
        slug = 'status_%04d' % get_next_id(models.TestInstanceStatus.objects.order_by('id').last())

    status = models.TestInstanceStatus(name=name, slug=slug, is_default=is_default, requires_review=requires_review)
    status.save()
    return status


def create_test(
    name=None,
    test_type=models.SIMPLE,
    choices=None,
    procedure=None,
    constant_value=None,
    category=None,
    wrap_low=None,
    wrap_high=None,
):
    user = create_user()
    if name is None or models.Test.objects.filter(name=name).count() > 0:
        name = "test_%d" % models.Test.objects.count()
    test = models.Test(
        name=name,
        slug=name,
        description="desc",
        type=test_type,
        category=category or create_category(),
        created_by=user,
        modified_by=user,
        choices=choices,
        wrap_high=wrap_high,
        wrap_low=wrap_low,
        procedure=procedure,
        constant_value=constant_value
    )
    test.save()
    return test


def create_test_list(name=None):

    if name is None:
        name = 'test_list_%04d' % get_next_id(models.TestList.objects.order_by('id').last())
    user = create_user()
    test_list = models.TestList(
        name=name,
        slug=slugify(name),
        description="desc",
        created_by=user,
        modified_by=user,
    )
    test_list.save()
    return test_list


def create_test_list_instance(
    unit_test_collection=None, work_completed=None, created_by=None, test_list=None, day=0, in_progress=False
):
    if unit_test_collection is None:
        unit_test_collection = create_unit_test_collection()
    if test_list is None:
        day, test_list = unit_test_collection.get_list(day)
    if work_completed is None:
        work_completed = timezone.now()
    work_started = work_completed - timezone.timedelta(seconds=60)
    if created_by is None:
        created_by = create_user()

    tli = models.TestListInstance(
        unit_test_collection=unit_test_collection,
        created_by=created_by,
        modified_by=created_by,
        modified=timezone.now(),
        work_completed=work_completed,
        work_started=work_started,
        test_list=test_list,
        day=day,
        in_progress=in_progress
    )
    tli.save()
    return tli


def create_cycle(test_lists=None, name=None):

    if name is None:
        name = 'test_list_cycle_%04d' % get_next_id(models.TestListCycle.objects.order_by('id').last())

    user = create_user()
    cycle = models.TestListCycle(
        name=name,
        slug=name,
        created_by=user,
        modified_by=user
    )
    cycle.save()
    if test_lists:
        for order, test_list in enumerate(test_lists):
            tlcm = models.TestListCycleMembership(
                test_list=test_list,
                cycle=cycle,
                order=order
            )
            tlcm.save()

    return cycle


def create_test_list_membership(test_list=None, test=None, order=0):

    if test_list is None:
        test_list = create_test_list()
    if test is None:
        test = create_test()

    tlm = models.TestListMembership(test_list=test_list, test=test, order=order)
    tlm.save()
    return tlm


def create_test_instance(
    test_list_instance=None, unit_test_info=None, value=1., created_by=None, work_completed=None, status=None
):

    if test_list_instance is None:
        test_list_instance = create_test_list_instance()

    if unit_test_info is None:
        unit_test_info = create_unit_test_info()

    if work_completed is None:
        work_completed = timezone.now()
    work_started = work_completed - timezone.timedelta(seconds=60)

    if created_by is None:
        created_by = create_user()
    if status is None:
        status = create_status()

    ti = models.TestInstance(
        unit_test_info=unit_test_info,
        value=value,
        created_by=created_by,
        modified_by=created_by,
        status=status,
        work_completed=work_completed,
        work_started=work_started,
        test_list_instance=test_list_instance
    )

    ti.save()
    return ti


def create_reference(name="ref", ref_type=models.NUMERICAL, value=1, created_by=None):
    if created_by is None:
        created_by = create_user()

    r = models.Reference(
        name=name, type=ref_type, value=value,
        created_by=created_by, modified_by=created_by
    )
    r.save()
    return r


def create_tolerance(tol_type=models.ABSOLUTE, act_low=-2, tol_low=-1, tol_high=1, act_high=2, created_by=None,
                     mc_pass_choices='', mc_tol_choices=''):

    if created_by is None:
        created_by = create_user()

    kwargs = dict(
        type=tol_type,
        act_low=act_low,
        tol_low=tol_low,
        tol_high=tol_high,
        act_high=act_high,
        created_by=created_by, modified_by=created_by
    )

    if tol_type == models.MULTIPLE_CHOICE:
        kwargs = dict(
            type=tol_type,
            mc_tol_choices=mc_tol_choices,
            mc_pass_choices=mc_pass_choices,
            created_by=created_by, modified_by=created_by
        )

    tol = models.Tolerance(**kwargs)
    tol.save()
    return tol


def create_frequency(name=None, slug=None, interval=1, window_end=1, save=True):
    if name is None or slug is None:
        name = 'frequency_%04d' % get_next_id(models.Frequency.objects.order_by('id').last())
        slug = name

    rule = recurrence.Rule(freq=recurrence.DAILY, interval=interval)

    f = models.Frequency(
        name=name,
        slug=slug,
        recurrences=recurrence.Recurrence(
            rrules=[rule],
            dtstart=timezone.get_current_timezone().localize(timezone.datetime(2012, 1, 1)),
        ),
        window_start=None,
        window_end=window_end,
    )
    if save:
        f.save()
    return f


def create_unit_test_info(unit=None, test=None, assigned_to=None, ref=None, tol=None, active=True):

    if unit is None:
        unit = create_unit()

    if test is None:
        test = create_test()

    if assigned_to is None:
        assigned_to = create_group()

    uti = models.UnitTestInfo(
        unit=unit,
        test=test,
        reference=ref,
        tolerance=tol,
        assigned_to=assigned_to,
        active=active
    )
    uti.save()
    return uti


def create_unit_test_collection(
    unit=None, frequency=None, test_collection=None, assigned_to=None, null_frequency=False, active=True
):

    if unit is None:
        unit = create_unit()

    if test_collection is None:
        test_collection = create_test_list()

    if frequency is None and not null_frequency:
        frequency = create_frequency()

    if assigned_to is None:
        assigned_to, _ = Group.objects.get_or_create(name="group")

    utc = models.UnitTestCollection(
        unit=unit,
        object_id=test_collection.pk,
        content_type=ContentType.objects.get_for_model(test_collection),
        frequency=frequency,
        assigned_to=assigned_to,
        active=active
    )

    utc.save()
    utc.visible_to.add(*Group.objects.all())
    utc.save()
    return utc


def datetimes_same(date1, date2, nminutes=1):
    """return whether date1 and date2 are the same within nminutes minutes"""
    return abs(date1 - date2) <= timezone.timedelta(minutes=nminutes)


def create_sublist(parent_test_list=None, child_test_list=None, order=1):

    if parent_test_list is None:
        parent_test_list = create_test_list()
    if child_test_list is None:
        child_test_list = create_test_list()

    s = models.Sublist(
        parent=parent_test_list,
        child=child_test_list,
        order=order
    )
    s.save()
    return s
