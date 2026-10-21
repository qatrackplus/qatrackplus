Initial Setup
=============

Docker Installation
-------------------

Ubuntu Linux
^^^^^^^^^^^^

At present, this project provides instructions for Ubuntu Linux.

To install Docker Engine, see
`Install Docker Engine on Ubuntu <https://docs.docker.com/engine/install/ubuntu/>`_.

Other Operating Systems
^^^^^^^^^^^^^^^^^^^^^^^

Other Linux distributions
.........................

If you are on a different Linux distribution, refer to the
`official Docker Engine installation docs <https://docs.docker.com/engine/install/>`_, 
or your distribution's documentation.


Windows
.......

Running QATrack+ with  Docker on Windows is not a configuration we can support
at the moment due to the restrictive license of Docker Desktop.

In theory, it should be possible to have a working Docker installation with
Windows Subsystems for Linux (WSL), which can run the Apache 2.0-licensed Docker Engine
in a Linux environment from within Windows, but at present this is neither supported nor
tested.


Post-Install Steps
^^^^^^^^^^^^^^^^^^

After installation, Docker recommends a few extra steps. Follow
`Linux post-installation steps for Docker Engine <https://docs.docker.com/engine/install/linux-postinstall/>`_

By following these instructions, you will:
    * Ensure that you can manage Docker with your non-root user.
    * Configure Docker to start automatically with the system.

There is no need to configure a default logging driver, as this configuration
is included in QATrack+'s Docker deployment already.

Before continuing please verify that you can successfully run ``docker run hello-world``
in a terminal.

Git
---

To retrieve files from GitHub you will need Git installed. Use the installation
method provided by your distribution. For Ubuntu:

.. code-block:: console

    $ sudo apt install git


Installing QATrack+
-------------------

Changing to the Directory Where Application Files Will Be Stored
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In a terminal, change to a directory of your choice for cloning the QATrack+
project.

Say that, for example, all our files are going to be located within our user's
home in the QATrack+ directory, then we would want to do the following:

.. code-block:: console

    $ mkdir ~/qatrack
    $ cd ~/qatrack

.. _docker_line_endings:

.. note::

    Files under ``deploy/docker`` run inside Linux containers and must have LF line
    endings. Git checks them out that way on every platform. A clone made before
    QATrack+ 4.0.2 on Windows may still have CRLF copies. To check them out again,
    run the following from the ``qatrackplus`` folder. It replaces the tracked files
    under ``deploy/docker`` with fresh copies, so the first and last lines save your
    own changes to them (your ``.env``, and any edits to ``nginx.conf`` or the
    compose files) and put them back. These are git commands only, so they work the
    same in Command Prompt, PowerShell or a Linux terminal. Untracked folders such
    as ``user-data`` and ``backups`` are not touched.

    .. code-block:: console

        git diff HEAD --output=../qatrack-docker-local.patch -- deploy/docker
        git rm -r --cached -q deploy/docker
        git checkout HEAD -- deploy/docker
        git apply --allow-empty ../qatrack-docker-local.patch

    ``--allow-empty`` needs git 2.35 or newer. The patch file holds your ``.env``,
    including the database password, so delete ``qatrack-docker-local.patch`` once
    you have checked that QATrack+ starts.

Downloading QATrack+
^^^^^^^^^^^^^^^^^^^^

At this point QATrack+ files need to be cloned from the Git repository.  Do
the following:

.. code-block:: console

    $ git clone https://github.com/qatrackplus/qatrackplus.git
    $ cd qatrackplus
    $ git checkout v4.0.0  # to check out a stable, released version

.. note::

    To use a stable released version, you should check out a Git *tag* 
    corresponding to the version you want. In the example above, we checked
    out the ``v4.0.0`` tag. For a list of available tags, consult the
    `QATrack+ repository on Github <https://github.com/qatrackplus>`_.

To run any `docker compose` commands you need to be within the
`qatrackplus/deploy/docker/` directory. So lets change to there now:

.. code-block:: console

    $ cd deploy/docker

