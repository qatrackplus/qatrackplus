.. _commands_appendix:

Appendix: command reference
===========================

Every table on this page is generated when the documentation is built, from
the code it describes, so none of them can drift from it. If a row is wrong,
the fix is in the task, command or Makefile, not here.

.. _poe_tasks_appendix:

poe tasks
---------

Read from the ``help`` line of each task in ``poe_tasks/*.toml``; ``poe`` with
no arguments prints the same list. The tasks you need day to day are the six in
:ref:`the task runner <task-runner-poe>`. A help line that begins **WIP** marks
a task that is unverified and not part of the ordinary workflow. Internal
helpers (names beginning with ``_``) are omitted, and a task without a help
line fails the documentation build.

.. include:: _poe_tasks.rst

.. _manage_commands_appendix:

manage.py commands
------------------

The commands QATrack+ adds to Django's ``manage.py``, read from each command's
``help`` attribute. Django's own commands (``migrate``, ``createsuperuser``,
``collectstatic`` and the rest) are not listed; ``python manage.py help``
prints everything. Run these from the QATrack+ directory with the virtual
environment active, or in Docker with ``docker compose exec django``
in front.

.. include:: _manage_commands.rst

.. _make_targets_appendix:

Makefile targets
----------------

The ``Makefile`` is a thin mirror of the ``poe`` tasks for anyone who prefers
Make; new work goes into the tasks. Descriptions come from ``make help`` where
the Makefile gives one, otherwise from the comment directly above the target.

.. include:: _make_targets.rst
