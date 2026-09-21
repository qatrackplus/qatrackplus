Installing & Deploying QATrack+ with Docker
===========================================

.. warning::

    This is a developmental install method. It is quite simple to get up and
    running but has not been battle-tested in production yet!


Prerequisites by OS
-------------------

Depending on which system you are using there are different ways to install the
required dependencies. Follow the section that applies to your specific machine.

In general, follow the instructions found at:

* https://docs.docker.com/desktop/setup/install/windows-install/
* https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/topics/#topics-for-windows

Note that Docker Desktop has two backends: WSL 2 and Hyper-V. These require
certain Windows features to be enabled prior to being able to use Docker Desktop
on top of virtualisation enabled in the BIOS of your host machine. See
https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/topics/#docker-desktop-fails-due-to-virtualization-not-working
for more details.

In general, you can use one backend or the other. At the time of writing, Docker
is recommending the WSL 2 backend.

Docker for Windows, and Git
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To install Docker Desktop and Git run the following within an administrative
command prompt:

.. code-block:: console

    winget install -e --id Git.Git --source winget
    winget install -e --id Docker.DockerDesktop

Reboot your machine.

To test that docker is working as expected run the following in a command
prompt:

.. code-block:: console

    docker run hello-world

Linux
~~~~~

Follow your distribution's documentation to install docker, or refer to Docker's
`official installation docs`(https://docs.docker.com/engine/install/). 


Make docker work without sudo on Linux
......................................

You will also need to implement the following to be able to run docker without
sudo:

* https://docs.docker.com/engine/install/linux-postinstall/

After completing these post install tasks please reset your computer.

Before continuing please verify that you can run `docker run hello-world` in a
terminal.

Git
~~~

To retrieve files from GitHub you will need git installed. Use the installation
method provided by your distribution. For example, for Ubuntu:

.. code-block:: console

    sudo apt install git

On other systems follow the instructions at
https://www.atlassian.com/git/tutorials/install-git.


Installing QATrack+
-------------------

This part is OS independent. The language used will be tuned for a Windows
user, but equivalent steps can be followed on Linux.

Changing to the directory where all server files will be stored
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open a command prompt with just user priveleges and change your directory to
the directory where all of the QATrack+ server files will be stored.

Lets say, for example, all our files are going to be located within the
`D:` drive at `D:\QATrack+` then we would want to do the following:

.. code-block:: console

    D:
    cd QATrack+

Downloading
~~~~~~~~~~~

At this point QATrack+ files need to be pulled from the git repository.  Do
the following:

.. code-block:: console

    git clone https://github.com/qatrackplus/qatrackplus.git
    cd qatrackplus
    git checkout v4.0.0  # to check out a stable, released version

To run any `docker compose` commands you need to be within the
`qatrackplus\\deploy\\docker` directory. So lets change to there now:

.. code-block:: console

    cd deploy\\docker


Layout under deploy\\docker
---------------------------

* ``compose.yaml``: The production-ready defaults.
* ``compose.override.yaml``: Development overrides (e.g., binding local source code).
* ``django/``: Multi-stage Dockerfile and entrypoint script for the Django app.
* ``nginx/``: NGINX configuration and server blocks.
* ``backup/``: A lightweight Alpine container that automatically runs database
  and media backups via cron.

How to Run
----------

Environment Setup
~~~~~~~~~~~~~~~~~

1. Copy the provided ``.env.example`` to ``.env``.

   .. code-block:: bash

      cp .env.example .env

2. Set your PostgreSQL credentials in the ``.env`` file.
3. Set ``ALLOWED_HOSTS`` in your ``.env`` file to include the IP address or
   hostname you will use to access the server (e.g.
   ``ALLOWED_HOSTS=localhost,127.0.0.1,ubuntu-test``). To allow all hosts
   temporarily, use ``ALLOWED_HOSTS=*``.
4. Set a unique value for ``SECRET_KEY``.
5. Set ``QATDEV=1`` if you are developing locally, or set it to ``QATDEV=0``
   for production.
6. **Install the ``just`` command runner** (see
   https://github.com/casey/just#installation).

   This will simplify the commands needed to use the docker deployment by having
   complicated command lines reduced to commands that are easy to type and remember.

Development
~~~~~~~~~~~

By default, Docker Compose will read both ``compose.yaml`` and
``compose.override.yaml``. The override file maps your local source code into
the container for live reloading.

``just`` will automatically use ``compose.override.yaml`` if ``QATDEV`` is set
to ``1``. Make sure ``QATDEV=1`` is set in ``.env``.

To build the images and run the services:

.. code-block:: bash

   just compose up --build

Production
~~~~~~~~~~

1. Configure strong, secure passwords in your ``.env`` file.
2. On your host, place the certificate file and certificate key file in a
   directory. Set ``SSL_DIR`` to be this directory in ``.env``. Similarly, set
   ``NGINX_SSL_CERTIFICATE_FILE`` and
   ``NGINX_SSL_CERTIFICATE_KEY_FILE`` in ``.env`` to be the file names of the
   certificate and certificate key.
3. Set a value for ``BACKUPS_DIR`` in ``.env``. Make sure it points to a
   directory that will be writable by the user.
4. Set ``QATDEV=0`` in ``.env``.
5. Build and start the containers using **only** the production file
   (ignoring the local code bind-mounts):

   .. code-block:: bash

      just compose up --build
    
    When ``QATDEV=0``, ``just compose`` only uses ``compose.yaml``.

First Run Setup
~~~~~~~~~~~~~~~

When booting a fresh database for the first time, you must create a superuser
(admin) account.

To do so, simply set ``DJANGO_SUPERUSER_USERNAME``,
``DJANGO_SUPERUSER_PASSWORD`` and optionally
``DJANGO_SUPERUSER_EMAIL``. These are standard Django environment variables
that will allow the superuser to be automatically created upon the first time
the services are started.

Advanced usage tips
-------------------

Accessing the Django shell
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you need to access the Django shell run the following in another terminal:

.. code-block:: console

    just manage shell

This requires that the containers are already running.

Making QATrack+ start on boot and run in the background
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To have QATrack+ start on boot  add the `-d` flag to the up command to detach
the process:

.. code-block:: console

    just compose up -d

Shutdown the server
~~~~~~~~~~~~~~~~~~~

To shutdown the server run:

.. code-block:: console

    just compose stop

You can also single press `Ctrl + C` within the server terminal that you ran
`just compose up` to gracefully shutdown the server.

Shutdown the server, remove the containers and docker volumes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

WARNING: if you store your database data in a docker volume, *this will delete
your database*. The next time you start the containers, a fresh empty database
will be created.

To shutdown the server, remove the containers and the docker volumes, run:

.. code-block:: console

    just compose down -v

Update server
~~~~~~~~~~~~~

First, review the release notes of the new version.
Second, make sure you have backups of your DB that you can restore successfully.

To update the server from github run:

.. code-block:: console

    just compose stop
    git pull
    # Then, checkout whichever git tag you want to update to.
    git checkout v.4.x.x

Once any files have changed in the qatrackplus directory you need to run the following:

.. code-block:: console

    just compose build
    just compose up  # or just compose up -d

Delete docker data
~~~~~~~~~~~~~~~~~~

If for some reason you need to, the following commands will delete all docker
data from all docker projects (**WARNING: IRREVERSIBLE, erases volumes**):

.. code-block:: console

    docker system prune -f -a --volumes
