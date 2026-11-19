.. _startup_checks:

Appendix: start-up checks
=========================

QATrack+ adds its own checks to Django's ``manage.py check``, and runs them
every time the site starts. Each has an id of the form ``qatrack.Wnnn``
(a warning: the site starts) or ``qatrack.Ennn`` (an error: it does not). The
table is generated when the documentation is built, from the code that raises
each check, so it lists every id the code can produce; a message shown as
composed at run time is one whose text is assembled from what the check
found. To silence a warning you have judged acceptable, add its id to
``SILENCED_SYSTEM_CHECKS`` in ``local_settings.py``.

.. include:: _startup_checks.rst
