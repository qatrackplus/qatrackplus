from django.utils import timezone
import models
import StringIO
import tokenize
import token

#----------------------------------------------------------------------
def due_status(last_done,frequency):

    if last_done is None:
        return models.NOT_DUE

    day_delta = (timezone.localtime(timezone.now()).date()-timezone.localtime(last_done).date()).days

    if day_delta >= frequency.overdue_interval:
        return models.OVERDUE
    elif day_delta >= frequency.due_interval:
        return models.DUE

    return models.NOT_DUE

#----------------------------------------------------------------------
def due_date(last_done_date,frequency):
    return timezone.localtime(last_done_date+frequency.due_delta())


#----------------------------------------------------------------------
def tests_history(tests,unit,number=5):
    all_instances = models.TestInstance.objects.filter(
        unit_test_info__test__in = tests,
        unit_test_info__unit = unit,
    ).select_related(
        "status",
        "unit_test_info__test__pk",
        "created_by"
    ).order_by("-work_completed")[:number]


    hist_dict = {}
    for instance in all_instances:
        hist = {
            "work_completed":instance.work_completed,
            "value":instance.value_display(),
            "pass_fail":instance.pass_fail,
            "status":instance.status,
            "created_by":instance.created_by,
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
        uti.history = histories.get(uti.test.pk,[])[:5]
        dates |=  set([x["work_completed"] for x in uti.history])
    history_dates = list(sorted(dates,reverse=True))[:5]

    #change history to only show values from 5 most recent dates
    for uti in unit_test_infos:
        new_history = []
        for d in history_dates:
            hist = [None]*4
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