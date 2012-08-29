from django.utils import timezone
import models
#----------------------------------------------------------------------
def due_status(last_done,frequency):

    if last_done is None:
        return models.NOT_DUE

    day_delta = (timezone.now().date()-timezone.localtime(last_done).date()).days

    if day_delta >= frequency.overdue_interval:
        return models.OVERDUE
    elif day_delta >= frequency.due_interval:
        return models.DUE

    return models.NOT_DUE

#----------------------------------------------------------------------
def due_date(last_done_date,frequency):
    return timezone.localtime(last_done_date+frequency.due_delta())


#----------------------------------------------------------------------
def tests_history(tests,unit,from_date,selected_related=None):
    all_instances = models.TestInstance.objects.filter(
        unit_test_info__test__in = tests,
        unit_test_info__unit = unit,
        work_completed__gte = from_date,
    ).select_related(
        "status",
        "unit_test_info__test__pk"
    ).order_by("-work_completed")


    hist_dict = {}
    for instance in all_instances:
        hist = (instance.work_completed,instance.value,instance.pass_fail,instance.status)
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
        dates |=  set([x[0] for x in uti.history])
    history_dates = list(sorted(dates,reverse=True))[:5]

    #change history to only show values from 5 most recent dates
    for uti in unit_test_infos:
        new_history = []
        for d in history_dates:
            hist = [None]*4
            for h in uti.history:
                if h[0] == d:
                    hist = h
                    break
            new_history.append(hist)
        uti.history = new_history
    return unit_test_infos, history_dates