Installing & Deploying QATrack+ with Docker
===========================================

.. warning::

    This is a developmental install method. It is quite simple to get up and
    running but has not been battle tested in production yet!

.. warning::

    This install method has not yet been updated for version 3.1.X


Prerequisites by OS
-------------------

Docker installations are supported on Ubuntu 24.04 LTS, and the instructions
have also been tested on Ubuntu 22.04 LTS, the same releases as the
:ref:`Linux installation guide <linux_install_40>`. The Windows 10 section below
predates QATrack+ 4.0. Depending on which system you are using there are
different ways to install the required dependencies. Follow the section that
applies to your specific machine.

.. _docker_minimum_versions:

Minimum Docker versions
~~~~~~~~~~~~~~~~~~~~~~~

Whichever system you use, QATrack+ needs:

* **Docker Compose 2.17 or newer.** QATrack+'s ``compose.yaml`` passes your
  :ref:`own Python packages <docker_site_packages>` to the build in a way older
  Compose releases don't understand. With one of them, the commands that build
  or create containers (``up``, ``build``, ``run``, ``create`` and ``pull``), as
  well as ``config``, stop with:

  .. code-block:: text

      services.django.build Additional property additional_contexts is not allowed

  Containers that are already running carry on, and ``ps``, ``logs``, ``exec``,
  ``stop``, ``start`` and ``restart`` still work on them. What you can't do is
  build or start a new release, or create containers again after
  ``docker compose down``, until Docker is updated.

* **Docker Engine 23.0 or newer.** The image build relies on BuildKit features
  that Docker Engine 20.10 and earlier don't include.

Check what you have with:

.. code-block:: console

    docker compose version
    docker version --format '{{.Server.Version}}'

The first prints the Compose version (for example ``Docker Compose version
v2.27.0``) and the second the Engine version. If either is too old, update
Docker by following Docker's own instructions linked below (on Ubuntu, Docker's
``apt`` repository updates both the Engine and the ``docker-compose-plugin``
package), or update Docker Desktop on Windows. Docker's current releases are
well above both minimums.

Windows 10 Professional or Enterprise with Hyper-V
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The aim of this setup is to have a complete installation of QATrack+ on a
Windows 10 Professional or Enterprise machine. Backups are covered in
:ref:`docker_backups`.

Ensure Virtualisation is enabled
................................

This setup uses Hyper-V. To use Hyper-V you need Windows 10 Professional or
Enterprise with virtualisation enabled. To verify that virtualisation is
enabled open the task manager, select `More details`, click on the
`Performance` tab and verify that in the bottom right it states
`Virtualisation: Enabled` as in the following screenshot:

.. figure:: https://docs.docker.com/docker-for-windows/images/virtualization-enabled.png
    :alt: Virtualization enabled

    Virtualisation enabled

If this says disabled then this will need to be enabled within your machines
BIOS before continuing.

See https://docs.docker.com/docker-for-windows/troubleshoot/#virtualization for
further troubleshooting if required.

Chocolatey
..........

To simplify this guide all installation will be done via the chocolatey package
manager. To install chocoletey run the following in a command prompt with
administrative privileges.

.. code-block:: console

    @"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))" && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"

For more information on chocolatey see https://chocolatey.org/

Docker for Windows, and Git
...........................

To install Docker for Windows, Docker Compose and Git run the following within
and administrative command prompt:

.. code-block:: console

    choco install git docker-for-windows -y

Reboot your machine.

Run the newly created `Docker for Windows` icon that has appeared on the
desktop. If prompted to approve the request to enable Hyper-V. Thise will once
again reboot your computer. Depending on your user priveledges you may need to
add your user account to `docker-users`
(https://github.com/docker/for-win/issues/868#issuecomment-352279510) at this
point.

You should not need to click this icon again.

After multiple reboots Docker will begin downloading and setting up its virtual
machine.  This will take some time and you may notice the PC running slow while
it is working on this.

Specifically you are waiting until the following popup is displayed:

.. figure:: https://docs.docker.com/docker-for-windows/images/docker-app-welcome.png
    :alt: Docker Welcome

    Docker Welcome

On my machine this docker initialisation process took a little over 15 minutes.

To test that docker is working as expected run the following in a command
prompt:

.. code-block:: console

    docker run hello-world

Enable shared drives within Docker for Windows
..............................................

Right click on the whale in the notification panel, then click `Settings`.
Within settings select `Shared Drives` and then tick all of the drives you wish
to be able to use within Docker containers. For this guide to work you will at
least need to share the drive where you will be keeping the QATrack+ server
files.

Docker for Windows does not support network drives.

Ubuntu 24.04 LTS
~~~~~~~~~~~~~~~~

If your server runs Ubuntu 24.04 LTS (or 22.04 LTS), follow these steps to
install the required prerequisites.

Docker Engine and Docker Compose
................................

To run this installation method you need Docker Engine with the Docker Compose
plugin, which provides the ``docker compose`` command. Install both by following
Docker's instructions for your distribution:

* `Install Docker Engine on Ubuntu <https://docs.docker.com/engine/install/ubuntu/>`__
* `Other Linux distributions <https://docs.docker.com/engine/install/>`__

Check that Compose is available, and that both meet
:ref:`the minimum versions <docker_minimum_versions>` (Compose 2.17, Engine
23.0), with:

.. code-block:: console

    docker compose version
    docker version --format '{{.Server.Version}}'

Make docker work without sudo on Linux
......................................

You will also need to implement the following to be able to run docker without
sudo:

* https://docs.docker.com/engine/installation/linux/linux-postinstall/

After completing these post install tasks please reset your computer.

Before continuing please verify that you can run `docker run hello-world` in a
terminal.

Git
...

To retrieve files from github you will need git installed by running the
following:

.. code-block:: console

    sudo apt install git

On other systems follow the instructions at
https://www.atlassian.com/git/tutorials/install-git.


Installing QATrack+
-------------------

This part is OS independent. The language used will be tuned for a Windows 10
user, but equivalent steps can be followed on Ubuntu.

Changing to the directory where all server files will be stored
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open a command prompt with just user priveledges and change your directory to
the directory where all of the QATrack+ server files will be stored.

Lets say, for example, all our files are going to be located within the
`D:` drive at `D:\QATrack+` then we would want to do the following:

.. code-block:: console

    D:
    cd QATrack+

Downloading
~~~~~~~~~~~

At this point QATrack plus files need to be pulled from the git repository.  Do
the following:

.. code-block:: console

    git clone https://github.com/qatrackplus/qatrackplus.git
    cd qatrackplus

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


Installation
~~~~~~~~~~~~

To run any `docker compose` commands you need to be within the
`qatrackplus\\deploy\\docker` directory. So lets change to there now:

.. code-block:: console

    cd deploy\docker

.. _docker_configuration:

Configuring QATrack+
....................

All of QATrack+'s Docker settings live in a file called ``.env`` in this
directory. It holds your passwords, so it is never part of the QATrack+
repository: create it from the documented template, then edit it. In Windows
Command Prompt:

.. code-block:: console

    copy .env.example .env

On Linux:

.. code-block:: console

    cp .env.example .env

At minimum, set:

* ``POSTGRES_USER`` and ``POSTGRES_PASSWORD``, before the first start. The
  database is created with them.
* ``ALLOWED_HOSTS``, the host names or IP addresses people use to reach
  QATrack+, comma-separated. nginx answers only these names, and drops requests
  for any other host before they reach QATrack+. The first name in the list is
  also used for the links in QATrack+'s emails and reports, unless you set
  ``SITE_DOMAIN``.

If people reach QATrack+ on a port other than 80 (or 443 with HTTPS), set
``SITE_DOMAIN`` to the name with the port, e.g. ``qatrack.myclinic.ca:8080``, so
links in emails work. ``SITE_NAME`` sets the name shown at the top of each page.
Both are applied every time QATrack+ starts, and replace any change made to them
in the admin's *Websites* page; leave them unset to manage them there instead.

Everything else is optional and documented in ``.env.example``: email, time
zone, HTTPS, Active Directory / LDAP sign-in, and the QC display options. Leave
a setting commented out to keep its default. ``SECRET_KEY`` is generated and
kept for you if you do not set one, but it is not in the nightly backup; see
:ref:`docker_secret_key`. After changing ``.env``, apply it with
``docker compose up -d``.

To build and start the server run the following:

.. code-block:: console

    docker compose build
    docker compose up

On initial run this will take quite some time to load.

Wait until you see something like the following within your terminal:

.. code-block:: console

    qatrack-django_1    | [2018-07-07 15:31:44 +0000] [509] [INFO] Starting gunicorn 19.3.0
    qatrack-django_1    | [2018-07-07 15:31:44 +0000] [509] [INFO] Listening at: http://0.0.0.0:8000 (509)
    qatrack-django_1    | [2018-07-07 15:31:44 +0000] [509] [INFO] Using worker: sync
    qatrack-django_1    | [2018-07-07 15:31:44 +0000] [512] [INFO] Booting worker with pid: 512
    qatrack-django_1    | [2018-07-07 15:31:44 +0000] [514] [INFO] Booting worker with pid: 514

Once the `Listening at: http://0.0.0.0:8000` line is visible go to
http://localhost in your computer's browser to see the server.

If you go to the website too early you will see the following error. This
is not an issue, it just means that the QATrack+ server has not yet finished
initialising. The first time QATrack+ starts up initialisation can take about
10 minutes depending on your internet connection.

.. figure:: images/502_error.png
    :alt: Error visible while server is starting up

.. note::

    The web server (``nginx``) and the background task service (``django-q``)
    only start once the ``django`` service reports that it is ready, and
    ``django`` is given up to 10 minutes for its first start. On a slow machine
    this may still not be enough, and ``docker compose up`` stops with
    ``dependency failed to start: container qatrackplus-django-1 is unhealthy``.
    Nothing is broken: ``django`` keeps working through its database migrations.
    Wait until ``docker compose logs django`` shows the ``Listening at`` line,
    then run ``docker compose up -d`` to start the rest. Migrations that have
    already run are not repeated.

No user account is created for you, so create one before your first login.
The `django` service runs the application, so run `createsuperuser` there and
answer its prompts:

.. code-block:: console

    docker compose exec django python manage.py createsuperuser

You can then sign in at http://localhost with the credentials you just chose.

Scheduled notifications, scheduled reports and the emails they send run in the
``django-q`` service. ``docker compose ps`` shows it, with the other services, as
``healthy``, and ``docker compose logs django-q`` shows what it has run.
``docker compose logs`` keeps at most 50 MB of each service's output, and starts
again empty when a container is recreated, for example by an upgrade.
QATrack+'s own log files (``debug.log``, ``auth.log`` and the others) are kept in
the ``logs-volume`` volume and survive upgrades; read them with
``docker compose exec django ls logs``.

.. _docker_development:

Developing with Docker
~~~~~~~~~~~~~~~~~~~~~~

The commands above run the QATrack+ code built into the image. To work on
QATrack+ itself, run your checkout instead, so code changes show up without
rebuilding. QATrack+ then writes into your checkout (its log files, for
example), so it runs as your own user. Add your user and group ids to ``.env``
once, then start with the development overlay:

.. code-block:: console

    printf '\nQATRACK_UID=%s\nQATRACK_GID=%s\n' "$(id -u)" "$(id -g)" >> .env
    docker compose -f compose.yaml -f compose.dev.yaml up -d --build

Use the same ``-f compose.yaml -f compose.dev.yaml`` on every ``docker compose``
command for that stack. QATrack+'s log files go to your checkout's ``logs``
folder, which is given to your user when the stack starts, even if an earlier
QATrack+ container created it as root.


Advanced usage tips
-------------------

Accessing the Django shell
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you need to access the Django shell run the following in another terminal:

.. code-block:: console

    docker exec -ti docker_qatrack-django_1 /bin/bash
    source deploy/docker/user-data/python-virtualenv/bin/activate
    python manage.py shell

This requires that the containers are already running.

Making QATrack+ start on boot and run in the background
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To have QATrack+ start on boot run the following command:

.. code-block:: console

    docker compose up -d

.. _docker_site_packages:

Adding Python packages
~~~~~~~~~~~~~~~~~~~~~~

Calculation procedures can import Python packages that QATrack+ does not
include. QATrack+ already includes numpy, scipy, pandas, matplotlib, pydicom,
pylinac and others; the versions it uses are in ``uv.lock`` at the top of your
QATrack+ folder. To add another package, list it in
``deploy/docker/site-requirements/requirements.txt``, one per line, with its
version:

.. code-block:: text

    pint==0.24.4

Then rebuild the image and restart:

.. code-block:: console

    docker compose build
    docker compose up -d

The packages are installed alongside QATrack+'s own, at versions that work with
them. If a package needs a different version of something QATrack+ uses (Django
or numpy, for example), ``docker compose build`` stops and names the conflict,
and your running QATrack+ is left as it was. Choose a version of the package
that works with QATrack+'s, or ask on the QATrack+ mailing list.

``requirements.txt`` and any wheel files beside it are yours: git ignores them,
so ``git pull`` leaves them alone.
Docker remembers the installed packages between builds and only installs them
again when something in ``deploy/docker/site-requirements`` or QATrack+'s own
dependencies changes. Packages that yours depend on, and that QATrack+ doesn't
already include, are picked when they are installed, so a later rebuild can get
newer versions of them. If you need every rebuild to be identical, pin those in
``requirements.txt`` too, or use wheel files as below. To install everything
afresh, run ``docker compose build --no-cache django``.

On a server without internet access, use wheel (``.whl``) files. They must suit
the image rather than the computer you download them on: Linux, CPython 3.12 and
the server's processor (``x86_64`` on most servers; ``aarch64`` on ARM). On any
computer with internet access and Python, pip can fetch the right ones, along
with everything they depend on:

.. code-block:: console

    pip download --only-binary=:all: --python-version 3.12 --implementation cp --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 -d site-wheels pint==0.24.4

Copy everything in ``site-wheels`` into ``deploy/docker/site-requirements`` (any
copies of packages QATrack+ already has do no harm), and add a line
``--no-index`` at the top of ``requirements.txt`` so your packages come only from
those files. If pip finds no wheel for a package, it needs building from source;
ask on the mailing list.

The rest of the build still needs the internet, to download the Python base
image and QATrack+'s own packages. Build the image once while the server is
connected, so Docker has those steps saved; or build it on a connected computer
and move the finished image with ``docker save`` and ``docker load``.

.. _docker_https:

Serving QATrack+ over HTTPS
~~~~~~~~~~~~~~~~~~~~~~~~~~~

nginx serves QATrack+ over HTTPS with your certificate. You need a certificate
for the host name people use, and its private key, in PEM format: from your
hospital's IT department, a certificate authority, or an origin certificate from
a proxy such as Cloudflare.

1. Put them in ``deploy/docker/user-data/ssl`` as ``cert.pem`` and ``key.pem``.
   Docker creates that folder, owned by root, the first time QATrack+ starts, so
   copy them in with ``sudo``:

   .. code-block:: console

       cd qatrackplus/deploy/docker
       sudo mkdir -p user-data/ssl
       sudo cp /path/to/your/certificate.pem user-data/ssl/cert.pem
       sudo cp /path/to/your/private.key user-data/ssl/key.pem
       sudo chmod 600 user-data/ssl/key.pem

   The certificate file should hold the full chain: your certificate first, then
   any intermediate certificates. To use other file names, set
   ``NGINX_SSL_CERTIFICATE`` and ``NGINX_SSL_CERTIFICATE_KEY`` in ``.env``.
2. In ``deploy/docker/.env``, set ``HTTP_OR_HTTPS=https``, and set
   ``ALLOWED_HOSTS`` to the name on the certificate.
3. Apply the change:

   .. code-block:: console

       docker compose up -d

nginx now listens on port 443 and redirects HTTP to HTTPS, and QATrack+ marks its
cookies secure. If nginx cannot read the certificate or key, it stops, and
``docker compose logs nginx`` says which file is missing. To renew the
certificate, replace the files and run ``docker compose restart nginx``.

.. _docker_secret_key:

Keeping the secret key safe
~~~~~~~~~~~~~~~~~~~~~~~~~~~

QATrack+ signs everyone's sign-in sessions and password-reset links with a
secret key. If ``SECRET_KEY`` is not set in ``.env``, QATrack+ generates a key
the first time it starts and saves it in the ``user-data-volume`` Docker volume,
as ``deploy/docker/user-data/secret_key.txt`` inside the containers (the
``deploy/docker/user-data`` folder on the server holds only your HTTPS
certificates). The key is kept when the containers are rebuilt or upgraded, and
each time QATrack+ starts, ``docker compose logs django`` shows a notice saying
where it is.

That volume is not part of the nightly backup. If it is lost, for example with
``docker compose down -v``, or QATrack+ is moved to another server without it,
QATrack+ generates a new key: everyone is signed out once, and password-reset
links already sent stop working. Your QC records are not affected.

The simplest way to keep the key safe is to copy it into ``.env``, with the rest
of your settings. Run this in ``deploy/docker`` while QATrack+ is running, then
apply it:

.. code-block:: console

    printf '\nSECRET_KEY=%s\n' "$(docker compose exec -T django cat deploy/docker/user-data/secret_key.txt)" >> .env
    docker compose up -d

The key is the same one, so nobody is signed out, and the notice no longer
appears in the log. On Windows, run
``docker compose exec -T django cat deploy/docker/user-data/secret_key.txt``
instead, and paste what it prints into ``.env`` after ``SECRET_KEY=``. From then
on, ``.env`` holds the key that signs your users' sessions: keep it as private
as your database password, and keep a copy with your backups.

To choose your own key instead, set ``SECRET_KEY`` in ``.env`` before QATrack+
first starts. This prints a suitable one:

.. code-block:: console

    docker compose run --rm --no-deps django python -c "import secrets; print(secrets.token_urlsafe(50))"

Avoid keys containing ``$``, such as those made by Django's
``get_random_secret_key``: Docker Compose reads ``$`` in ``.env`` as the start
of a variable and silently changes the key. Changing the key of a site already
in use signs everyone out once.

If you are upgrading from QATrack+ 4.0.0 or 4.0.1, which kept the key in a
different place, see :ref:`docker_upgrade_keep_secret_key`.

Changing from port 80 to a different port
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first number of the `ports` item within `compose.yaml` can be changed
to use a port that is different to port 80. For example, if `80:80` was changed
to `8080:80` then you would need to type http://localhost:8080 within your
browser to see QATrack+. After editing `compose.yaml` you need to rerun
`docker compose up`.

.. _docker_postgres_access:

Connecting to the database directly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Out of the box, QATrack+'s PostgreSQL database isn't published on any of the
server's network addresses, so there is nothing for other computers on your
network to connect to. Most sites never need to change that.

That doesn't make it unreachable from the server itself. On Linux, the server
can reach Docker's internal network directly, so anyone with an account on the
server who knows the database password can connect. Whether or not you turn on
the option below, it's ``POSTGRES_PASSWORD`` in ``.env`` that protects the
database, so make it long and hard to guess, and don't reuse it anywhere else.

For a quick look, you don't need to change anything. This opens ``psql`` inside
the database container (replace ``POSTGRES_USER`` and ``POSTGRES_DB`` with the
values in your ``.env``):

.. code-block:: console

    docker compose exec postgres psql -U POSTGRES_USER -d POSTGRES_DB

If a database client, a GUI tool such as pgAdmin, or a reporting tool needs to
connect, you can publish the database on the server with the optional
``compose.db-port.yaml`` file. It stays off until you turn it on.

**To turn it on**, add this line to ``.env`` (it is in ``.env.example``,
commented out):

.. code-block:: text

    COMPOSE_FILE=compose.yaml:compose.db-port.yaml

then apply it:

.. code-block:: console

    docker compose up -d

``COMPOSE_FILE`` tells every ``docker compose`` command run in
``deploy/docker`` to use ``compose.db-port.yaml`` as well as ``compose.yaml``,
so the commands you run don't change, and it carries on across restarts and
upgrades.

PostgreSQL then listens on ``127.0.0.1``, port ``5434``: on the server itself
only, on a port that doesn't clash with a PostgreSQL that may already be
installed there. To use another port, set ``POSTGRES_HOST_PORT`` in ``.env``.
``POSTGRES_HOST_ADDRESS`` sets the address, and should stay ``127.0.0.1`` (see
the warning below). These are not the same as ``POSTGRES_HOST`` and
``POSTGRES_PORT``, which tell QATrack+ how to reach the database inside Docker;
leave those alone.

Turning it on or off restarts the whole site, not just the database. Every
QATrack+ service reads its settings from ``.env``, so any change to ``.env``
(this one included) makes ``docker compose up -d`` recreate the ``django``,
``django-q``, ``backup`` and ``postgres`` containers. Expect QATrack+ to be
unavailable for about half a minute, with the browser showing a *502 Bad
Gateway* page until it's back. Do it at a quiet time, not while people are
saving QC results. **To turn it off**, remove the line (or put a ``#`` back in
front of it) and run ``docker compose up -d`` again.

If you use the :ref:`development overlay <docker_development>`, which is chosen
with ``-f``, add the file to your ``-f`` options instead, for example
``docker compose -f compose.yaml -f compose.dev.yaml -f compose.db-port.yaml up -d``.
``-f`` replaces ``COMPOSE_FILE`` rather than adding to it.

**To connect on the server**, use the user name, password and database name
from ``.env`` (``POSTGRES_USER``, ``POSTGRES_PASSWORD`` and ``POSTGRES_DB``):

.. code-block:: console

    psql -h 127.0.0.1 -p 5434 -U POSTGRES_USER -d POSTGRES_DB

``psql`` asks for the password. A GUI client takes the same host, port, user
name, password and database.

**To connect from another computer**, use an SSH tunnel rather than opening the
database to the network. This forwards port 5433 on your own computer, through
an SSH connection to the server, to the database (replace ``user@server`` with
your SSH login):

.. code-block:: console

    ssh -N -L 5433:127.0.0.1:5434 user@server

Leave it running, and point your client at ``127.0.0.1``, port ``5433``, on your
own computer. Only people who can sign in to the server over SSH can use the
tunnel, and the connection is encrypted all the way.

.. warning::

    **Do not set** ``POSTGRES_HOST_ADDRESS=0.0.0.0``. That opens the clinic's QA
    database to every network the server is connected to, protected only by the
    database password. The connection isn't encrypted, so that password and your
    data would cross the network as plain text, and Docker opens the port even
    past a firewall on the server such as ``ufw``. Use an SSH tunnel instead. If
    another system really must connect over the network, ask your IT department
    to help limit who can reach it.

Shutdown the server
~~~~~~~~~~~~~~~~~~~

To shutdown the server run:

.. code-block:: console

    docker compose stop

You can also single press `Ctrl + C` within the server terminal that you ran
`docker compose up` to gracefully shutdown the server.

Update server
~~~~~~~~~~~~~

Before you update, check that your Docker still meets
:ref:`the minimum versions <docker_minimum_versions>` (Compose 2.17, Engine
23.0). An older Compose can't build or start the new release, so if you find out
first, your site keeps running while you update Docker:

.. code-block:: console

    docker compose version
    docker version --format '{{.Server.Version}}'

Then get the new code and build it. Your site keeps running while you do this:

.. code-block:: console

    git pull
    docker compose build

Once the build has finished without errors, swap the running containers for the
new ones:

.. code-block:: console

    docker compose up -d

There's no need to stop the site first: ``up -d`` replaces each container that
has changed, so QATrack+ is only unavailable while they restart. If the build
stops with an error instead, nothing has been stopped and your site carries on
running the version it had before.

.. _docker_backups:

Backing up and restoring
~~~~~~~~~~~~~~~~~~~~~~~~

The ``backup`` service backs up QATrack+'s database and uploaded files every
night at 2 AM, into the ``deploy/docker/backups`` folder:

* ``db_YYYYMMDD_HHMMSS.dump``, the database;
* ``media_YYYYMMDD_HHMMSS.tar.gz``, the uploaded files.

Each file is read back in full as it is made, and only gets its final name once
it is complete, so an interrupted backup never looks like a finished one. Each
backup is kept for 7 days, then deleted. To back up now, or to see the backups
you have:

.. code-block:: console

    docker compose exec backup backup
    docker compose exec backup ls -lh /backups

A backup does not contain your ``.env`` file, which holds the database password
and your settings, nor the certificates in ``user-data/ssl``. Keep copies of
those as well. If you have not set ``SECRET_KEY`` in ``.env``, QATrack+ keeps a
generated one in a Docker volume, which a backup does not contain: restoring on
another server signs everyone out once and voids password-reset links.
:ref:`docker_secret_key` shows how to copy it into ``.env``, so it is kept with
your settings.

**Keep copies off the server.** ``deploy/docker/backups`` is on the same disk as
QATrack+, so a disk failure, or ransomware, that takes the server takes these
backups too. Have your IT department's backup system copy that folder to another
machine every day.

**Only root can read the backups.** They hold all of your clinic's QATrack+
records and uploaded files, and everyone's (hashed) passwords, so each backup
file is readable by root alone (mode 600) on the server. Each backup also does
the same to any backups made by earlier releases, which other users could read. To
copy them, use ``sudo`` (for example ``sudo cp`` or ``sudo rsync``), or have the
copy job run as root, and keep the copies just as private. If the folder is on a
drive that cannot hold Linux permissions, such as a Windows share, ``backup``
prints a warning but still makes the backup.

.. note::

    Uploaded files are part of QATrack+'s records: an attachment belongs to the
    test list, service event or fault it was attached to, and nothing in
    QATrack+ deletes one. The folder only grows. Plan storage for it, and never
    point a clean-up job at it.

To restore, stop QATrack+, restore the database and the uploaded files from the
same backup, and start it again:

.. code-block:: console

    docker compose stop django django-q
    docker compose run --rm --no-deps backup restore-db db_YYYYMMDD_HHMMSS.dump
    docker compose run --rm restore-media media_YYYYMMDD_HHMMSS.tar.gz
    docker compose up -d

The ``backup`` service can only read the uploaded files, so that the nightly
backup can never change them. ``restore-media`` is a separate service, set up in
``compose.yaml``, that can write to them; it only runs when you ask for it, and
``docker compose up`` never starts it. It uses the same image as ``backup``, so
it is updated whenever ``backup`` is rebuilt.

Each command checks the whole backup before it changes anything, then asks you to
confirm: type the database name for ``restore-db``, and ``RESTORE`` for
``restore-media``. Your current database and files are only replaced once the
backup has been fully unpacked beside them, so if a restore fails, or you stop it
with Ctrl-C, they are left as they were, and the command tells you so. A restore
replaces everything: anything entered since that backup is lost.

Backups made by QATrack+ 4.0.0 and 4.0.1 can be restored. When you restore a
backup from an older release, ``docker compose up -d`` applies the database
changes the current release needs. Do not restore a backup from a newer release
into an older one.

**Check the free disk space before you restore.** ``restore-db`` builds the
restored database beside your current one, so while it runs PostgreSQL needs
room for a second copy of QATrack+'s database. To see how big the current one
is, replace ``POSTGRES_USER`` and ``POSTGRES_DB`` with the values in your
``.env`` and run:

.. code-block:: console

    docker compose exec postgres psql -U POSTGRES_USER -d POSTGRES_DB -c "SELECT pg_size_pretty(pg_database_size(current_database()))"

To see how much space is free where PostgreSQL keeps its data, look at the
*Avail* column of:

.. code-block:: console

    docker compose exec postgres df -h /var/lib/postgresql/data

On Linux this is the disk that holds Docker's data, usually ``/var/lib/docker``,
so ``df -h /var/lib/docker`` on the server tells you the same. A restored
database is often smaller than the one it replaces, but plan for at least the
size of the current one. ``restore-media`` likewise unpacks a second copy of the
uploaded files before it swaps them in; ``docker compose exec backup du -sh /media``
shows how much room that needs.

Delete docker data
~~~~~~~~~~~~~~~~~~

If for some reason you need it, the following command will delete all docker
data from all docker projects (WARNING, IRREVERSABLE):

.. code-block:: console

    docker stop $(docker ps -a -q) && docker rm $(docker ps -a -q)

And this will delete all of the cache:

.. code-block:: console

    echo 'y' | docker volume prune

To just delete all postgres database data do the following:

.. code-block:: console

    docker stop docker_qatrack-postgres_1 && docker rm docker_qatrack-postgres_1 && docker volume rm docker_qatrack-postgres-volume
