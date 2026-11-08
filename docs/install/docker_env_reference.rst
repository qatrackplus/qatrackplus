.. _docker_env_reference:

Appendix: every Docker ``.env`` setting
=======================================

This page reproduces ``deploy/docker/.env.example`` from the source tree at
the time the documentation was built, so it cannot drift from the file you
copy to ``.env`` when :ref:`setting up <docker_setup>`. The comments in it are
the documentation of each setting; a line that starts with ``#`` is a setting
left at its default. The database password shown is the example file's
placeholder, which :ref:`the setup page <docker_setup>` has you replace.

.. literalinclude:: ../../deploy/docker/.env.example
   :language: shell
