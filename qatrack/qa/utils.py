from django.db.models import Q
from django.conf import settings
from django.utils import timezone
import math
import models
import StringIO
import tokenize
import token

#----------------------------------------------------------------------
def due_status(last_instance,frequency):
    if last_instance is None:
        return models.NOT_DUE

    last_done = last_instance.work_completed

    invalids = [1 for x in last_instance.testinstance_set.all() if not x.status.valid]
    if invalids:
        return models.OVERDUE

    day_delta = (timezone.localtime(timezone.now()).date()-timezone.localtime(last_done).date()).days

    if day_delta >= frequency.overdue_interval:
        return models.OVERDUE
    elif day_delta >= frequency.due_interval:
        return models.DUE

    return models.NOT_DUE

#----------------------------------------------------------------------
def due_date(last_instance,frequency):
    invalids = [1 for x in last_instance.testinstance_set.all() if not x.status.valid]
    if invalids:
        return timezone.localtime(timezone.datetime.now())
    last_done = last_instance.work_completed
    return timezone.localtime(last_done+frequency.due_delta())


#----------------------------------------------------------------------
def tests_history(tests,unit,from_date,test_list=None):
    all_instances = models.TestInstance.objects.filter(
        unit_test_info__test__in = tests,
        unit_test_info__unit = unit,
        work_completed__gte = from_date,
        status__export_by_default=True,
    ).select_related(
        "status",
        "tolerance",
        "reference",
        "unit_test_info__test__pk",
        "created_by"
    ).order_by("-work_completed")

    if test_list is not None:
        all_instances = all_instances.filter(
            Q(test_list_instance__test_list=test_list) |
            Q(test_list_instance__test_list__testlistcycle__test_lists=test_list)
        )

    hist_dict = {}
    for instance in all_instances:
        hist = {
            "work_completed":instance.work_completed,
            "value":instance.value_display(),
            "pass_fail":instance.pass_fail,
            "status":instance.status,
            "created_by":instance.created_by,
            "diff":instance.diff_display(),
        }
        try:
            hist_dict[instance.unit_test_info.test.pk].append(hist)
        except KeyError:
            hist_dict[instance.unit_test_info.test.pk] = [hist]

    return hist_dict

#----------------------------------------------------------------------
def add_history_to_utis(unit_test_infos,histories):
    #figure out 5 most recent dates that a test from this list was performed
    dates = set()
    for uti in unit_test_infos:
        uti.history = histories.get(uti.test.pk,[])
        dates |=  set([x["work_completed"] for x in uti.history])
    history_dates = list(sorted(dates,reverse=True))[:settings.NHIST]

    #change history to only show values from NHIST most recent dates
    for uti in unit_test_infos:
        new_history = []
        for d in history_dates:
            hist = [None]*settings.NHIST
            for h in uti.history:
                if h["work_completed"] == d:
                    hist = h
                    break
            new_history.append(hist)
        uti.history = new_history
    return unit_test_infos, history_dates



#----------------------------------------------------------------------
def tokenize_composite_calc(calc_procedure):
    """tokenize a calculation procedure"""
    tokens = tokenize.generate_tokens(StringIO.StringIO(calc_procedure).readline)
    return [t[token.NAME] for t in tokens if t[token.NAME]]

#----------------------------------------------------------------------
def unique(seq,idfun=None):
    """f5 from http://www.peterbe.com/plog/uniqifiers-benchmark"""
    # order preserving
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        if marker in seen:
            continue
        seen[marker] = 1
        result.append(item)
    return result


#----------------------------------------------------------------------
def almost_equal(a,b,significant=7):
    """determine if two numbers are nearly equal to significant figures
    copied from numpy.testing.assert_approx_equal
    """
    a, b = map(float, (a, b))
    if b==a:
        return
    # Normalized the numbers to be in range (-10.0,10.0)
    # scale = float(pow(10,math.floor(math.log10(0.5*(abs(b)+abs(a))))))
    try:
        scale = 0.5*(abs(b) + abs(a))
        scale = math.pow(10,math.floor(math.log10(scale)))
    finally:
        pass

    try:
        sc_b = b/scale
    except ZeroDivisionError:
        sc_b = 0.0
    try:
        sc_a = a/scale
    except ZeroDivisionError:
        sc_a = 0.0

    return abs(sc_b - sc_a) <= math.pow(10.,-(significant-1))

