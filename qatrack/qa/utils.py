from django.utils import timezone
import models
#----------------------------------------------------------------------
def due_status(last_done,frequency):

    if last_done is None:
        return models.NOT_DUE

    day_delta = (timezone.now().date()-last_done.date()).days

    if day_delta >= frequency.overdue_interval:
        return models.OVERDUE
    elif day_delta >= frequency.due_interval:
        return models.DUE

    return models.NOT_DUE

#----------------------------------------------------------------------
def due_date(last_done_date,frequency):
    return last_done_date+frequency.due_delta()


#----------------------------------------------------------------------
def tests_history(tests,unit,from_date,selected_related=None):
    all_instances = models.TestInstance.objects.filter(
        unit_test_info__test__in = tests,
        unit_test_info__unit = unit,
        work_completed__gte = from_date,
    ).select_related(
        "status",
        "unit_test_info__test__pk"
    ).order_by("work_completed")


    hist_dict = {}
    for instance in all_instances:
        hist = (instance.work_completed,instance.value,instance.pass_fail,instance.status)
        try:
            hist_dict[instance.unit_test_info.test.pk].append(hist)
        except KeyError:
            hist_dict[instance.unit_test_info.test.pk] = [hist]

    return hist_dict
