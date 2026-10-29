===================================
Installation and Deployment Options
===================================


Selecting a platform for QATrack+
---------------------------------

Currently there are three "officially" supported ways to deploy QATrack+: 1)
Ubuntu Linux 24.04 LTS with PostgreSQL (recommended; 22.04 LTS is also tested,
and MySQL remains supported for existing installations), 2) Windows Server 2022+
with SQL Server, and 3) Docker on a Linux server.

QATrack+ 4.0 needs Python 3.12, which rules out Ubuntu releases older than
22.04: 20.04 and 18.04 do not package it.

The platform you choose will generally depend on what type of system you or
your clinic has the most expertise in and / or your budget (Microsoft tools can
be expensive!).

.. toctree::
   :maxdepth: 2
   :caption: Ubuntu Linux

   linux
   linux_upgrade_from_3
   linux_upgrade_from_4_0
   linux_upgrade_from_4_0_1


.. toctree::
   :maxdepth: 2
   :caption: Windows Server

   win
   win_upgrade_from_3
   win_upgrade_from_4_0
   win_upgrade_from_4_0_1


Docker runs QATrack+ and its database in containers on a Linux server. It needs
Docker Engine 23.0 or newer and Docker Compose 2.17 or newer; running it on
Windows, including with Docker Desktop, isn't supported. To get started, see
:doc:`docker`.

.. toctree::
   :maxdepth: 2
   :caption: Docker (Linux)

   docker
   docker_upgrade_from_4_0
   docker_upgrade_from_4_0_1


Configuring your QATrack+ Instance
----------------------------------

After installing QATrack+ you will likely want to customize some of the
settings for QATrack+.  All of the available settings and how to set them is
described here:

.. toctree::
   :maxdepth: 1

   config
   authentication_backends
   backup
