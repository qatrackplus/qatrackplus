.. danger::

   This document is for version 0.3.1 which has not been released yet!  See
   https://docs.qatrackplus.com/en/latest/ for documentation of the latest
   release.

===================================
Installation and Deployment Options
===================================


Selecting a platform for QATrack+
---------------------------------

Currently there are two "officially" supported platforms for deploying QATrack+
on: 1) Ubuntu Linux (14.04+) with PostgreSql (or MySQL) and 2) Windows Server
2012+ with SQL Server.  There are many, many, more operating systems/database
combinations but it is overwhelming to create and keep documentation updated
for all of them.  That said, if you have a different preference of platform,
adapting the Ubuntu instructions to another \*nix system should be relatively
straightforward.

The platform you choose will generally depend on what type of system you or
your clinic has the most expertise in and / or your budget (Microsoft tools can
be expensive!).

.. toctree::
   :maxdepth: 2
   :caption: Officially Supported Platforms

   linux
   win


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
   :maxdepth: 2

   config
   active_directory
   backup
