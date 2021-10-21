from django.utils import timezone

from qatrack.qatrack_core.dates import end_of_day, start_of_day

# due date choices. For convenience with colors/icons these are the same as the
# pass fail choices

NO_DUE_DATE = "no_tol"
NOT_DUE = "ok"
DUE = "tolerance"
OVERDUE = "action"


def calc_due_date(completed, due_date, frequency):
    """Calculate the next due date after completed for input frequency. If
    completed is prior to qc window the due date return will be the same as
    input due_date."""

    if frequency is None:
        return None

    is_classic_offset = frequency.window_start is None
    if is_classic_offset or due_date is None:
        return frequency.recurrences.after(completed, dtstart=completed)

    if due_date is None:
        return calc_initial_due_date(completed, frequency)

    if should_update_schedule(completed, due_date, frequency):

        # ok, we're inside or beyond QC window so get next due date
        next_due_date = frequency.recurrences.after(completed, dtstart=due_date)

        # now, it's possible that we performed the test long after the due
        # date and now we're inside the next QC window so we have to check
        # if we should move the next one!
        # See TestCalcDueDate.test_first_of_month_performed_long_after_inside_next_window
        if should_update_schedule(completed, next_due_date, frequency):
            next_due_date = frequency.recurrences.after(next_due_date, dtstart=next_due_date)

        return next_due_date

    return due_date


def calc_initial_due_date(completed, frequency):
    """if due date is None, check whether completed date falls within the
    window for the next occurence. If it does return second occurence,
    otherwise return next occurence."""

    next_occurence = frequency.recurrences.after(completed, dtstart=completed)
    if should_update_schedule(completed, next_occurence, frequency):
        return frequency.recurrences.after(next_occurence, dtstart=next_occurence)
    return next_occurence


def qc_window(due_date, frequency):
    """Calculate the qc window around due_date for given frequency"""

    #    assert False, "need to use day start and end I think"
    if frequency is None or due_date is None:
        return (None, None)

    start = None
    if frequency.window_start is not None:
        start = start_of_day(due_date - timezone.timedelta(days=frequency.window_start))

    end = end_of_day(due_date + timezone.timedelta(days=frequency.window_end))

    return (start, end)


def should_update_schedule(date, due_date, frequency):
    """Return true if date falls after start of qc_window for due_date"""
    start, end = qc_window(due_date, frequency)
    return start is None or start <= date


def calc_nominal_interval(frequency):
    """Calculate avg number of days between tests for ordering purposes"""
    tz = timezone.get_current_timezone()
    occurrences = frequency.recurrences.occurrences(
        dtstart=tz.localize(timezone.datetime(2012, 1, 1)),
        dtend=end_of_day(tz.localize(timezone.datetime(2012, 12, 31))),
    )
    deltas = [(t2 - t1).total_seconds() / (60 * 60 * 24) for t1, t2 in zip(occurrences, occurrences[1:])]
    return sum(deltas) / len(deltas)


class SchedulingMixin:
    """
    A mixin class to be used when assigning 'tasks' to a unit with a
    frequency object.
    """

    def calc_due_date(self):
        """return the next due date of this Unit/TestList pair """

        if self.auto_schedule and self.frequency:
            last_valid = self.last_instance_for_scheduling()
            if not last_valid and self.last_instance and self.last_instance.include_for_scheduling:
                # Done before but no valid lists
                return timezone.now()
            elif (last_valid and last_valid.work_completed):
                return calc_due_date(last_valid.work_completed, self.due_date, self.frequency)

        # return existing due date (could be None)
        return self.due_date

    def set_due_date(self, due_date=None):
        """Set due date field for this UTC. Note model is not saved to db.
        Saving be done manually"""

        if self.auto_schedule and due_date is None and self.frequency is not None:
            due_date = self.calc_due_date()

        if due_date is not None:
            # use update here instead of save so post_save and pre_save signals are not
            # triggered
            self.due_date = due_date
            self._meta.model.objects.filter(pk=self.pk).update(due_date=due_date)

    def due_status(self):
        if not self.due_date:
            return NO_DUE_DATE

        today = timezone.localtime(timezone.now()).date()
        due = timezone.localtime(self.due_date).date()

        if today < due:
            return NOT_DUE

        if self.frequency is not None:
            overdue = due + timezone.timedelta(days=self.frequency.window_end)
        else:
            overdue = due + timezone.timedelta(days=1)

        if today < overdue:
            return DUE
        return OVERDUE

    def window(self):

        if self.due_date is None:
            return None

        if not self.frequency:
            return (self.due_date, self.due_date)

        if self.frequency.classical:
            return (self.due_date, (self.due_date + timezone.timedelta(days=self.frequency.window_end)))

        start = self.due_date - timezone.timedelta(days=self.frequency.window_start)
        end = self.due_date + timezone.timedelta(days=self.frequency.window_end)
        return (start, end)
