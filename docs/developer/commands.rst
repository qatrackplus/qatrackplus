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

The ``Makefile`` is frozen - it carries its own implementations, nothing in it
calls ``poe``, and it is **removed during the 4.1 cycle**. New work goes into
the tasks. Every target below is also available as ``poe make-<target>`` (a
dotted target loses the dot, because poe forbids one in a task name), and the
documentation build fails if one of them has no mirror.

Descriptions come from the mirror's ``help`` line, falling back to ``make
help`` and then to the comment above the target. The mirror is asked first
because the frozen Makefile's own help text cannot be corrected, and two of its
lines are already stale: ``test`` claims to include the GUI tests that are now
skipped by default, and ``test_simple`` claims to be the one without them. They
have done the same thing since the GUI tests started skipping.

.. include:: _make_targets.rst
