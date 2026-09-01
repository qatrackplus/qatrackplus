.. _common_issues:

Common Issues & Solutions
=========================

This section documents problems that QATrack+ users encounter repeatedly along
with step-by-step solutions. It is maintained collaboratively by the community —
if you have solved a problem that isn't listed here, please consider
:ref:`contributing it <contributing_common_issues>`.

.. toctree::
   :maxdepth: 1
   :caption: Issues & Solutions

   contributing
   installation_issues
   upgrade_issues
   email_notifications
   performance

----

.. _contributing_common_issues:

Contributing to this section
-----------------------------

Community contributions to this section are strongly encouraged. You do **not**
need to be a developer to contribute — if you solved a problem, write it up.

**Quick steps:**

1. Fork the repository and create a branch named ``docs/<short-description>``.
2. Copy ``docs/common_issues/contributing.rst`` as a starting template for your
   new file.
3. Name the file after the problem, for example ``missing_migrations.rst``.
4. Add your file to the ``toctree`` in ``docs/common_issues/index.rst``.
5. Build the docs locally (``cd docs && make html``) to check for errors.
6. Open a pull request against the ``Dev`` branch.

See `CONTRIBUTING.md <https://github.com/qatrackplus/qatrackplus/blob/Dev/CONTRIBUTING.md>`_
at the root of the repository for full details.
