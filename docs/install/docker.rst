Installing & Deploying QATrack+ with Docker
===========================================

.. warning::

    This is a developmental install method. It is quite simple to get up and
    running but has not been battle-tested in production yet!

.. note::

    **The Docker deployment runs on PostgreSQL only.** QATrack+ itself supports
    four database backends, but this deployment builds its image for PostgreSQL
    and configures the application for it, so a site running SQL Server or
    MySQL cannot use these instructions as they stand. Install by one of the
    other methods instead - see :ref:`linux_install_40` or
    :ref:`win_install_40`.


.. toctree::
   :maxdepth: 2

   docker_setup


.. toctree::
   :maxdepth: 2

   docker_layout


.. toctree::
   :maxdepth: 2

   docker_config


.. toctree::
   :maxdepth: 2

   docker_production


.. toctree::
   :maxdepth: 2

   docker_development


.. toctree::
   :maxdepth: 2

   docker_usage
