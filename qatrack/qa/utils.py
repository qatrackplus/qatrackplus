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
