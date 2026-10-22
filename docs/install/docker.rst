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

Windows 10 Professional or Enterprise with Hyper-V
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The aim of this setup is to have a complete installation of QATrack+ on a
Windows 10 Professional or Enterprise machine with the backups being scheduled
to be periodically copied to a OneDrive directory.

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

Check that Compose is available with:

.. code-block:: console

    docker compose version

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
repository: create it from the documented template, then edit it.

.. code-block:: console

    cp .env.example .env

At minimum, set:

* ``POSTGRES_USER`` and ``POSTGRES_PASSWORD``, before the first start. The
  database is created with them.
* ``ALLOWED_HOSTS``, the host names or IP addresses people use to reach
  QATrack+, comma-separated. nginx answers only these names, and drops requests
  for any other host before they reach QATrack+.

Everything else is optional and documented in ``.env.example``: email, time
zone, HTTPS, Active Directory / LDAP sign-in, and the QC display options. Leave
a setting commented out to keep its default. ``SECRET_KEY`` is generated and
kept for you if you do not set one. After changing ``.env``, apply it with
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

No user account is created for you, so create one before your first login.
The `django` service runs the application, so run `createsuperuser` there and
answer its prompts:

.. code-block:: console

    docker compose exec django python manage.py createsuperuser

You can then sign in at http://localhost with the credentials you just chose.

Scheduled notifications, scheduled reports and the emails they send run in the
``django-q`` service. ``docker compose ps`` shows it, with the other services, as
``healthy``, and ``docker compose logs django-q`` shows what it has run. Each
service keeps at most 50 MB of logs.

.. _docker_development:

Developing with Docker
~~~~~~~~~~~~~~~~~~~~~~

The commands above run the QATrack+ code built into the image. To work on
QATrack+ itself, run your checkout instead, so code changes show up without
rebuilding. QATrack+ then writes into your checkout (its log files, for
example), so it runs as your own user. Add your user and group ids to ``.env``
once, then start with the development overlay:

.. code-block:: console

    echo "QATRACK_UID=$(id -u)" >> .env
    echo "QATRACK_GID=$(id -g)" >> .env
    docker compose -f compose.yaml -f compose.dev.yaml up -d --build

Use the same ``-f compose.yaml -f compose.dev.yaml`` on every ``docker compose``
command for that stack. If your checkout has a ``logs`` folder created by an
earlier QATrack+ container, which ran as root, give it to your user once with
``sudo chown -R $(id -u):$(id -g) ../../logs``.


Setting up copying backups from local machine to remote server on Windows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create the following bat file:

.. code-block:: batch

    NET USE V: "\\pdc\OneDrive$\QATrack+"

    xcopy D:\QATrack+\qatrackplus\deploy\docker\user-data\backup-management\backups V:\backups /E /G /H /D /Y

Then using Windows Task scheduler to set that bat file to run daily.

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

.. _docker_https:

Serving QATrack+ over HTTPS
~~~~~~~~~~~~~~~~~~~~~~~~~~~

nginx serves QATrack+ over HTTPS with your certificate. You need a certificate
for the host name people use, and its private key, in PEM format: from your
hospital's IT department, a certificate authority, or an origin certificate from
a proxy such as Cloudflare.

1. Put them in ``deploy/docker/user-data/ssl`` as ``cert.pem`` and ``key.pem``.
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

Changing from port 80 to a different port
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first number of the `ports` item within `compose.yaml` can be changed
to use a port that is different to port 80. For example, if `80:80` was changed
to `8080:80` then you would need to type http://localhost:8080 within your
browser to see QATrack+. After editing `compose.yaml` you need to rerun
`docker compose up`.

Making the backup management store its files on a network share
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Within the docker image all backup data is placed at
`/usr/src/qatrackplus/deploy/docker/user-data/backup-management`.  If during
the initial boot of the docker image a network drive is mounted to that
directory theoretically all backups should be managed on that network drive
instead. To achieve this, at the start of `init.sh` write the following line:


.. code-block:: console

    mount -t cifs -o username=your_user_name -o password=your_password //host_name/share_name /usr/src/qatrackplus/deploy/docker/user-data/backup-management

See `cifs man page
<https://www.systutorials.com/docs/linux/man/8-mount.cifs/>`__ for more help if
needed.

This has not been tested yet, please inform Simon Biggs (me@simonbiggs.net) if
you have issues / if you get it working.

Shutdown the server
~~~~~~~~~~~~~~~~~~~

To shutdown the server run:

.. code-block:: console

    docker compose stop

You can also single press `Ctrl + C` within the server terminal that you ran
`docker compose up` to gracefully shutdown the server.

Update server
~~~~~~~~~~~~~

To update the server from github run:

.. code-block:: console

    docker compose stop
    git pull

Once any files have changed in the qatrackplus directory you need to run the following:

.. code-block:: console

    docker compose build
    docker compose up

Backup management
~~~~~~~~~~~~~~~~~

Everytime `docker compose up` is run a timestamped backup zip file of the
database, uploaded files, and your site specific css is created. These backups
are stored within
`qatrackplus/deploy/docker/user-data/backup-management/backups`.  To restore a
backup zip file copy it to the restore directory found at
`qatrackplus/deploy/docker/user-data/backup-management/restore`.  The
restoration will occur next time `docker compose up` is called. After
successful restoration the zip file within the restore directory is deleted.

This restore method will also successfully restore backup files created on a
different machine. However it will only successfully restore a like for like
QATrack+ version. This cannot be used when upgrading between versions.

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
