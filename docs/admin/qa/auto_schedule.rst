Configuring Auto-Schedule for all currently assigned test lists
===============================================================

As of version 0.2.6 of QATrack+ there is a `Django management
command <https://docs.djangoproject.com/en/dev/howto/custom-management-commands/>`__
``auto_schedule`` that allows you to enable or disable
`auto-scheduling <assign_to_unit.md>`__ for all test lists currently
assigned to a unit. It will also allow you to update the due dates for
all tests lists assigned to a unit based on their last performed date
and assigned frequency. This is usually not necessary but might be
useful if you have manually overriden many due dates and want to "reset"
all of them.

All of these commands must be run from the git bash shell from the root
of your QATrack+ directory (with your virtualenv activated).

*The following command will disable the ``auto_schedule`` flag for all
test list assignments:*

::

    #! bash
    python manage.py auto_schedule disable-all

*The following command will enable the ``auto_schedule`` flag for all
test list assignments:*

::

    #! bash
    python manage.py auto_schedule enable-all

*The following command will update the scheduled due date for all test
list assignments based on the date they were last completed and their
assigned frequency:*

::

    #! bash
    python manage.py auto_schedule schedule-all

*The following command will "unset" the due date for all test list
assignments (i.e. they will all show as Not Due):*

::

    #! bash
    python manage.py auto_schedule unschedule-all
