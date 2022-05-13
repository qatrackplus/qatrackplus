class SchedulingMixin:
    """A mixin class to be used when assigning 'tasks' to a unit with a
    frequency object"""

    def calc_due_date(self):
        """return the next due date of this Unit/TestList pair """

        if self.auto_schedule and self.frequency:
            if not self.last_instance:
                # Done before but no valid lists
                return timezone.now()
            elif self.last_instance and self.last_instance.datetime_service:
                return utils.calc_due_date(self.last_instance.datetime_service, self.due_date, self.frequency)

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
            return q_models.NO_DUE_DATE

        today = timezone.localtime(timezone.now()).date()
        due = timezone.localtime(self.due_date).date()

        if today < due:
            return q_models.NOT_DUE

        if self.frequency is not None:
            overdue = due + timezone.timedelta(days=self.frequency.window_end)
        else:
            overdue = due + timezone.timedelta(days=1)

        if today < overdue:
            return q_models.DUE
        return q_models.OVERDUE
