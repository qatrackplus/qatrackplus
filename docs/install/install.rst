===================================
Installation and Deployment Options
===================================


Selecting a platform for QATrack+
---------------------------------

Currently there are two "officially" supported platforms for deploying QATrack+
on: 1) Ubuntu Linux (18.04+) with PostgreSql (or MySQL) and 2) Windows Server
2017+ with SQL Server.

The platform you choose will generally depend on what type of system you or
your clinic has the most expertise in and / or your budget (Microsoft tools can
be expensive!).

.. toctree::
   :maxdepth: 2
   :caption: Ubuntu Linux

   linux
   linux_upgrade_from_3
   linux_upgrade_from_030
   linux_upgrade_from_02X


.. toctree::
   :maxdepth: 2
   :caption: Windows Server

   win
   win_upgrade_from_3
   win_upgrade_from_030
   win_upgrade_from_02X


Note there is no official support for the platforms listed below.  That doesn't
necessarily mean they are unreliable, just that you may be on your own if you
run into any issues.  Of course you can always look for help on the
:mailinglist:`mailing list <>`.

.. toctree::
   :maxdepth: 2

   docker


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
