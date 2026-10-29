.. _linux_install_40:

New Installation of QATrack+ 4.0 on Ubuntu Linux
=================================================

.. note::

    This guide assumes you have at least a basic level of familiarity with
    Linux and the command line.


This guide is going to walk you through installing everything required to run
QATrack+ on an Ubuntu 24.04 LTS (Noble Numbat) server with Python 3.12, Nginx
as the web server and PostgreSQL 16 (recommended) or MySQL 8.0 — which remains
supported for existing installations — as the database.  The
instructions have also been tested on Ubuntu 22.04 and installation
instructions should be similar on other Ubuntu systems. Similar steps will also
likely work on other Linux distributions but those distributions are not
officially supported or tested.

If you are upgrading an existing QATrack+ installation, please see
one of the following pages:

* :ref:`Upgrading an existing v3.x.y installation to 4.0.0
  <linux_upgrading_40>`. 

The steps we will be undertaking are:

.. contents::
    :local:

If you hit an error along the way, stop and figure out why the error is
occurring before proceeding with the next step!  You can seek help on the on the
:mailinglist:`mailing list <>`.

Prerequisites
-------------

.. warning::

    These install steps should be done using a regular user account. They will not
    work if you are currently logged in as 'root'.

.. dropdown:: Starting from a fresh cloud server, where root is all you have
    :color: warning

    A new server from a cloud provider commonly gives you **root and nothing
    else**, so there is no regular account to use yet. Create one before you begin:

    .. code-block:: bash

        adduser qatrack
        usermod -aG sudo qatrack

    ``adduser`` asks you to choose a password for the new account and to type it
    twice, and then offers a handful of optional details -- full name, phone
    number and so on -- which you can skip by pressing ``Enter`` at each one.
    Keep the password: ``sudo`` asks for it.

    If you reach the server by SSH key rather than by password, copy your key over
    to the new account as well, or you will not be able to log in as it:

    .. code-block:: bash

        install -d -m 700 -o qatrack -g qatrack /home/qatrack/.ssh
        install -m 600 -o qatrack -g qatrack /root/.ssh/authorized_keys \
            /home/qatrack/.ssh/authorized_keys

    Then log out and back in as ``qatrack`` before continuing. The rest of this
    guide assumes you are that user and that ``sudo`` works.

Make sure your existing packages are up to date. On a server you reach over SSH,
start a ``tmux`` session before you begin, so that the upgrade keeps running — and
stays answerable — if your connection drops. (``tmux`` is already installed on most
cloud images; ``sudo apt install tmux`` if yours does not have it.)

.. code-block:: bash

    tmux
    sudo apt update
    sudo apt upgrade

.. dropdown:: New to ``tmux``? Everything you need for this guide

    ``tmux`` runs your shell **on the server** rather than inside your SSH client, so
    nothing running in it depends on your connection staying up. If your laptop sleeps,
    your network drops, or SSH itself stops answering — which is exactly what the next
    step does — the commands keep running, and you can pick the session back up when
    you get back in.

    .. list-table::
        :header-rows: 1
        :widths: 22 78

        * - Command
          - What it does
        * - ``tmux``
          - Starts a session and puts you in a shell inside it.
        * - ``tmux attach``
          - Puts you back into the session you left. This is the one you run after
            logging in again.
        * - ``tmux ls``
          - Lists the sessions on this server, if you are not sure one is still there.
        * - ``exit``
          - Ends the session, once you are finished with it.

    To leave a session running on purpose, press ``Ctrl-b`` and then ``d``, for
    "detach". ``Ctrl-b`` is how you talk to ``tmux`` itself rather than to the shell
    inside it, and the only other one worth learning is ``Ctrl-b`` then ``[``, which
    lets you scroll back through output with the arrow keys — press ``q`` to stop
    scrolling and return to the shell.

    If your server has ``screen`` instead, it does the same job: ``screen`` to start,
    ``screen -r`` to get back in, and ``Ctrl-a`` where ``tmux`` uses ``Ctrl-b``.

    Nothing else in this guide requires a session like this, but the longer steps —
    installing dependencies, running the test suite — are worth the same protection.

.. warning::

    **The upgrade offers to replace** ``/etc/ssh/sshd_config``\ **, and SSH stops
    accepting new connections before it asks.** Cloud images ship their own
    ``sshd_config``, so ``openssh-server`` finds a locally modified file and asks
    what to do about it — as a full-screen dialog, not a one-line prompt.

    Answer it in the session you are already in. **"keep the local version
    currently installed" is already the selected option, so pressing Enter is the
    right answer** — and on a fresh server it is the honest one too, since the
    image's ``sshd_config`` is the only locally modified file there is. SSH starts
    answering again about five seconds later and the upgrade finishes normally.

    What you cannot do is open a second session to go and look at the question.
    ``openssh-server`` is unpacked — which stops ``sshd`` — more than a minute
    before the dialog appears, and the dialog then waits as long as you do, so
    ``ssh`` reports ``connection refused`` while your provider still reports the
    server as running. Measured on Linode Ubuntu 24.04 images, 2026-10-28, on
    1 GB and 2 GB servers alike.

    **Getting back in.** If your connection drops while the question is waiting,
    port 22 will not come back on its own. Log in through your provider's
    out-of-band console — Linode calls it Lish, most providers offer a web or
    serial console, and a local virtual machine has the hypervisor's own window —
    and pick the session back up:

    .. code-block:: bash

        tmux attach

    You are in front of the same dialog, on the same half-finished upgrade. Answer
    it and the upgrade carries on from where it stopped.

    **If you were not running under tmux,** the upgrade died with your shell,
    and the server is left with ``openssh-server`` half-configured and the twenty
    or so packages behind it unconfigured. **You may not need the console for
    this one.** Reboot the server - the control panel's own reboot button is
    enough - and SSH answers again, because the configuration file still in place
    is the one that was working before the upgrade started. Then finish the job
    over SSH:

    .. code-block:: bash

        sudo dpkg --force-confold --configure -a

    ``--force-confold`` answers the dialog the same way pressing Enter would, by
    keeping the configuration file already installed, so it runs without stopping
    to ask. Check the result with ``dpkg --audit``, which prints nothing at all
    when every package is configured. Measured on a Linode Ubuntu 24.04 server,
    2026-10-29: reboot, then one command, 36 packages configured, SSH never lost
    again.

    If a reboot does not bring SSH back, the console is the way in, and
    ``sudo dpkg --configure -a`` there will stop and ask the question for you to
    answer.

    **Adding -y to the upgrade command does not help.** It answers ``apt``'s own
    *"Do you want to continue?"*, not this one, which comes from ``dpkg``: measured,
    ``sudo apt -y upgrade`` stops on the same dialog in the same place.

    For an unattended install, answer the question before it is asked:

    .. code-block:: bash

        sudo DEBIAN_FRONTEND=noninteractive apt-get -y \
            -o Dpkg::Options::="--force-confold" upgrade

    That upgrade runs start to finish without stopping — but note that it still
    takes ``sshd`` down for about a minute while ``openssh-server`` is replaced
    (measured: 60 s), so a connection opened during that minute is still refused.
    The difference is that nothing is waiting for an answer, so the port comes back
    on its own.


You will need to have the `make` command and a few other packages available for
this deployment. Install them as follows:

.. code-block:: bash

    sudo apt install make build-essential python3-dev python3-tk curl

You will also need the Chrome browser installed for generating PDF reports:

.. code-block:: bash

    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt install ./google-chrome-stable_current_amd64.deb


Installing and configuring Git and checking out the QATrack+ Source Code
------------------------------------------------------------------------

QATrack+ uses the git version controls system.  Ensure you have git installed
with the following command:

.. code-block:: bash

   sudo apt install git

and then configure git (substituting your name and email address!)

.. code-block:: bash

   git config --global user.name ccody
   git config --global user.email ccody@example.com

Check out the QATrack+ source code from GitHub
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now that we have git installed we can proceed to grab the latest version of
QATrack+.  To checkout the code enter the following commands:

.. code-block:: bash

    mkdir -p ~/web
    cd ~/web
    git clone https://github.com/qatrackplus/qatrackplus.git
    cd qatrackplus
    git checkout releases/4.0

.. dropdown:: Side note: Alternate Tag
    :color: warning

    The ``releases/4.0`` branch is the 4.0 series including its patch releases, so
    upgrading later is ``git fetch`` and ``git pull`` — you never name a version.

    Pinning an exact version with a tag is possible but **not recommended**: a tag is
    immutable, so ``git pull`` will not bring you patches and each upgrade becomes a
    fresh checkout. If you must, the available tags are listed on the
    `releases page <https://github.com/qatrackplus/qatrackplus/releases>`__.


Installing a Database System
----------------------------

It is *highly* recommended that you choose PostgreSQL for your database,
however it is possible to use MySQL/MariaDB if you need to.

Installing PostgreSQL
~~~~~~~~~~~~~~~~~~~~~

If you do not have an existing database server, you will need to install
PostgreSQL locally. Run the following commands:

.. code-block:: bash

    sudo apt-get install postgresql libpq-dev postgresql-client postgresql-client-common

After that completes, we can create a new database and Postgres user (db
name/user/pwd = qatrackplus/qatrack/qatrackpass) as follows:

.. warning::

    ``qatrackpass`` **is an example in a published document, not a default to
    keep.** The script below sets it, and so does the ``local_settings.py``
    template further down, so a site that follows this guide literally ends up
    with the password printed in our documentation. Change it on both the main
    and the read-only role, and in ``local_settings.py``, before the server is
    reachable by anyone else:

    .. code-block:: bash

        sudo -u postgres psql -c "ALTER ROLE qatrack WITH PASSWORD 'your-own-password'"
        sudo -u postgres psql -c "ALTER ROLE qatrack_reports WITH PASSWORD 'another-one'"

    The roles are only reachable from this server as it is configured here, which
    is why this is a warning rather than a blocker - but a password anybody can
    look up is one credential away from mattering.

.. code-block:: bash

    cd ~/web/qatrackplus
    sudo -u postgres psql < deploy/postgres/create_db_and_role.sql

And then create a readonly user for the SQL query tool:

.. code-block:: bash

    sudo -u postgres psql < deploy/postgres/create_ro_role.sql


Now edit ``pg_hba.conf``. The path contains the major version of PostgreSQL you
just installed, which depends on your distribution rather than on QATrack+ —
**Ubuntu 24.04 installs PostgreSQL 16**, so the path there is
``/etc/postgresql/16/main/pg_hba.conf``. Check which you have rather than
assuming:

.. code-block:: bash

    ls /etc/postgresql/
    # then, substituting the version it printed:
    sudo nano /etc/postgresql/16/main/pg_hba.conf

.. note::

    This guide uses ``nano`` because it works the way a text editor works in
    Windows: the arrow keys move the cursor, what you type appears where the cursor
    is, and the commands are listed along the bottom of the screen — ``Ctrl-o`` then
    ``Enter`` writes the file, ``Ctrl-x`` leaves it. Ubuntu installs it by default,
    so it is already there. If you have an editor you prefer, use that instead;
    nothing in this guide depends on the choice.

Find the ``local all all`` line. It is near the end of a 130-odd line file, not
at the very bottom, and there are more lines after it -- in ``nano``, ``Ctrl-w``
searches, so ``Ctrl-w`` then ``local   all`` lands on it. Change its method from
``peer`` to ``scram-sha-256``:

.. code-block:: bash

    # TYPE  DATABASE        USER            ADDRESS                 METHOD

    # "local" is for Unix domain socket connections only
    local   all             all                                     scram-sha-256
    # IPv4 local connections:
    host    all             all             127.0.0.1/32            scram-sha-256
    # IPv6 local connections:
    host    all             all             ::1/128                 scram-sha-256

Only the first of those three lines changes; the two ``host`` lines already say
``scram-sha-256`` on a stock Ubuntu 24.04 install, and the ``local all postgres``
and ``replication`` lines above and below are left alone.

.. note::

    This guide's ``local_settings.py`` connects to PostgreSQL on
    ``127.0.0.1``, which is a ``host`` line and not the ``local`` one, so
    QATrack+ itself works whether or not you make this change. It is the
    ``psql -U qatrack`` kind of command, run on the server over the Unix
    socket, that needs it -- including the ones later in this guide. Older
    releases of this page said ``md5`` here, which still works; PostgreSQL has
    preferred ``scram-sha-256`` since version 14.

and restart the pg server:

.. code-block:: bash

    sudo service postgresql restart


.. dropdown:: For MySQL: Install & Configure Database
    :color: warning

    **Installing MySQL (only required if you prefer to use MySQL over Postgres)**

    .. code-block:: bash

        sudo apt-get install mysql-server libmysqlclient-dev

    .. note::

        You should use the InnoDB storage engine for MySQL.  If you are using MySQL
        >= 5.5.5 then it uses InnoDB by default, otherwise if you are using MySQL <
        5.5.5 you need to set the default storage engine to InnoDB:
        https://dev.mysql.com/doc/refman/5.5/en/storage-engine-setting.html


    Now we can create and configure a user (db name/user/pwd =
    qatrackplus/qatrack/qatrackpass) and database for QATrack+:

    .. code-block:: bash

        # if you set a password during mysql install
        sudo mysql -u root -p < deploy/mysql/create_db_and_role.sql

        # if you didn't
        sudo mysql < deploy/mysql/create_db_and_role.sql


    And then create a readonly user for the SQL query tool:


    .. code-block:: bash

        # if you  set a password during mysql install
        sudo mysql -u root -p < deploy/mysql/create_ro_role.sql

        # if you didn't
        sudo mysql < deploy/mysql/create_ro_role.sql


Setting up our Python environment (including virtualenv)
--------------------------------------------------------


Check your Python version
~~~~~~~~~~~~~~~~~~~~~~~~~

QATrack+ 4.0 runs on Python 3.12. Check your version of
python3 with the command:

.. code-block:: bash

   python3 -V

Which should show the result `Python 3.12.10` or similar.  In order to keep
QATrack+'s Python environment isolated from the system Python, we will run
QATrack+ inside a Python `Virtual Environment` managed by `uv`.

First, install `uv`:

.. code-block:: bash

    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.local/bin/env

Creating our virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    cd ~/web/qatrackplus
    uv venv --python 3.12 --prompt qatrackplus .venv


Anytime you open a new terminal/shell to work with your QATrack+ installation
you will want to activate your virtual environment.  Do so now like this:

.. code-block:: bash

    source .venv/bin/activate

Your command prompt should now be prefixed with `(qatrackplus)`.

We will now install all the libraries required for QATrack+ with PostgresSQL
(be patient, this can take a few minutes!):

.. code-block:: bash

    cd ~/web/qatrackplus
    uv sync --extra postgres --no-dev

``--no-dev`` keeps the test and documentation tooling out of a deployment.
Without it ``uv`` installs the ``dev`` dependency group as well - around 220
packages including pytest, selenium, sphinx and **django-debug-toolbar** - none
of which a server needs in order to run QATrack+. Leave it off only if you
intend to run the test suite on this machine; see :ref:`linux_upgrade_from_4_0_1`.

The next section does run the test suite, and ``make test_simple`` re-syncs with
the ``dev`` group to do it, so following this guide in order leaves the dev
tooling installed. That is harmless -- nothing serves from it -- but if you want
the deployment trimmed afterwards, run ``uv sync --extra postgres --no-dev``
again once you are done testing.

.. dropdown:: For MySQL: Install Requirements
    :color: warning

    or for MySQL:

    .. code-block:: bash

        cd ~/web/qatrackplus
        uv sync --extra mysql --no-dev


Making sure everything is working up to this point
--------------------------------------------------

At this point you can run the QATrack+ test suite to ensure your environment is set up correctly:

.. code-block:: bash

    cd ~/web/qatrackplus
    cp deploy/sqlite/local_settings.py qatrack/local_settings.py
    make test_simple

This takes a couple of minutes and should end with a line like this:

.. code-block:: bash

    1354 passed, 3 skipped, 34 deselected, 219 warnings in 152.63s (0:02:32)

Measured on a 1 vCPU / 1 GB server running Ubuntu 24.04 against 4.0.1. **Do not
treat the exact numbers as a target** - they move with every release, and the
count differs by platform and by which optional dependencies you installed. What
matters is that nothing *failed*.

The three skips are expected on a standard install: they are the Active Directory
tests, which need the optional ``python-ldap`` package.


Configuration of QATrack+
-------------------------

Next we need to tell QATrack+ how to connect to our database and (optionally)
set some configuration options for your installation.

Create your `local_settings.py` file by copying the example from `deploy/{postgres|mysql}/local_settings.py`:

.. code-block:: bash

    # postgres
    cp deploy/postgres/local_settings.py qatrack/local_settings.py
    chmod 600 qatrack/local_settings.py

.. dropdown:: For MySQL: Copy Settings File
    :color: warning

    .. code-block:: bash

        # mysql
        cp deploy/mysql/local_settings.py qatrack/local_settings.py


then open the file:

.. code-block:: bash

    nano qatrack/local_settings.py

There are many available settings and
they are documented within the example file and more completely on :ref:`the
settings page <qatrack-config>`. Directions for :ref:`setting up email
<config_email>`  are also included on that page.

However, the two most important settings are `DATABASES` and `ALLOWED_HOSTS`:
which should be set like the following (switch the `ENGINE` to mysql if
required).

.. tip::

    You can quickly find your server's IP address by running ``hostname -I`` in your terminal.

.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'qatrackplus',
            'USER': 'qatrack',
            'PASSWORD': 'qatrackpass',
            'HOST': '127.0.0.1',
            'PORT': '',
        },
        'readonly': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'qatrackplus',
            'USER': 'qatrack_reports',
            'PASSWORD': 'qatrackpass',
            'HOST': '127.0.0.1',
            'PORT': '',
        }
    }


    # Change XX.XXX.XXX.XX to your servers IP address and/or host name e.g. ALLOWED_HOSTS = ['54.123.45.1', 'yourhostname']
    ALLOWED_HOSTS = ['XX.XXX.XXX.XX']

    # CSRF_TRUSTED_ORIGINS is required for Django 4.0+. It must include the scheme (http/https).
    CSRF_TRUSTED_ORIGINS = ['http://XX.XXX.XXX.XX', 'https://XX.XXX.XXX.XX']

Once you have got those settings done, we can now test our database connection:

.. code-block:: bash

    python manage.py showmigrations accounts

which should show output like:

.. code-block:: bash

    accounts
     [ ] 0001_initial
     [ ] 0002_activedirectorygroupmap_defaultgroup
     [ ] 0003_auto_20210207_1027
     [ ] 0004_Auto_BigAuto_TimeZone_Django42
     [ ] 0005_v4_0_final


If you were able to connect to your database, we can now create the tables in
our database and install the default data:

.. code-block:: bash

    python manage.py migrate
    python manage.py loaddata fixtures/defaults/*/*


After that completes, we can grant privileges to our readonly database user as
follows:

.. code-block:: bash

    # PostgreSQL
    sudo -u postgres psql < deploy/postgres/grant_ro_rights.sql

.. dropdown:: For MySQL: Grant Read-Only Privileges
    :color: warning

    .. code-block:: bash

        # or MySQL if you set a password during install
        sudo mysql -u root -p -N -B -e "$(cat deploy/mysql/generate_ro_privileges.sql)" > grant_ro_privileges.sql
        sudo mysql -u root -p --database qatrackplus < grant_ro_privileges.sql

        # or MySQL if you did not set a password during install
        sudo mysql -N -B -e "$(cat deploy/mysql/generate_ro_privileges.sql)" > grant_ro_privileges.sql
        sudo mysql --database qatrackplus < grant_ro_privileges.sql


You also need to create a super user so you can login and begin configuring
your Test Lists:


.. code-block:: bash

    python manage.py createsuperuser

and finally we need to collect all our static media files in one location for
Nginx to serve:

.. code-block:: bash

    python manage.py collectstatic

If you want to enable internationalization, then you need to compile the
messages catalogs for the languages you need. ``compilemessages`` is a wrapper
around GNU gettext's ``msgfmt``, which is not part of Python, so install it
first:

.. code-block:: bash

    sudo apt install gettext

Without it the command stops with ``CommandError: Can't find msgfmt. Make sure
you have GNU gettext tools 0.15 or newer installed.`` and no catalogue is
compiled - QATrack+ then serves every string in English, with nothing else to
say it is wrong.

.. code-block:: bash

    python manage.py compilemessages -l fr
    python manage.py compilemessages -l fr_CA
    python manage.py compilemessages -l es


Setting up Django Q
------------------- 

As of version 3.1.0, some features in QATrack+ rely on a separate long running
process which looks after periodic and background tasks like sending out
scheduled notices and reports.  We are going to use 
`Supervisor <http://supervisord.org>`_ to look after running this process
on startup and ensuring it gets restarted if it fails for some reason.

Install supervisor:

.. code-block:: bash

    sudo apt install supervisor


In order for Django Q to run properly and for Nginx to serve uploaded files, we need to create the logging and media directories and ensure the web server and QATrack+ background tasks can share permissions:

.. code-block:: bash

    sudo usermod -a -G www-data $USER
    exec sg www-data newgrp `id -gn` # this refreshes users group memberships without needing to log off/on
    mkdir -p logs qatrack/media
    touch logs/{migrate,debug,django-q2,auth}.log
    sudo chown -R www-data:www-data logs qatrack/media
    sudo chmod ug+rwxs logs qatrack/media

.. note::

    ``exec sg`` replaces your shell, which also clears the ``(qatrackplus)``
    prefix from your prompt. The virtual environment is still in use -- ``which
    python`` still answers ``.venv/bin/python`` -- so carry on. It works when you
    are typing at a terminal
    and **cannot work inside a script**: everything after it in the same file is
    never reached. If you are automating this install, drop that line and either log
    out and back in, or run the remaining commands with ``sg www-data -c '...'``. The
    line is only a convenience to avoid logging out - nothing later depends on it
    having run in the same shell.


and then set up the Django Q configuration:

.. code-block:: bash

    make supervisor.conf


Lastly, confirm django-q2 is now running:

.. code-block:: bash

    sudo supervisorctl status

which should result in output like:

.. code-block:: bash

    django-q2                        RUNNING   pid 15860, uptime 0:00:05
    gunicorn                         RUNNING   pid 1332294, uptime 0:00:10


If supervisor does not show `RUNNING` you can check the error log which 
is located at /var/log/supervisor-django-q2.err.log

You can also check on the status of your task cluster at any time like this:

.. code-block:: bash

    cd ~/web/qatrackplus/
    source .venv/bin/activate
    python manage.py qmonitor


Installing Nginx web server
---------------------------

The next step to take is to install and configure the Nginx web server.
Nginx can be installed with the following command:

.. code-block:: bash

    sudo apt-get install nginx

Now we can remove the default Nginx config file and copy over the QATrack+ config
file:

.. danger::

    If you already have other sites running using the default config file you
    will want to edit it to include the directives relevant to QATrack+ rather
    than deleting it.  Seek help if you're unsure!

.. code-block:: bash

    sudo rm -f /etc/nginx/sites-enabled/default
    make nginx.conf

and finally restart Nginx:

.. code-block:: bash

    sudo service nginx restart


You should now be able to log into your server at http://yourserver/!


Serving over HTTPS
------------------

The configuration written by ``make nginx.conf`` serves plain HTTP. For anything
reachable beyond a trusted network you want TLS, and `Let's Encrypt
<https://letsencrypt.org>`__ issues free certificates that browsers trust.

.. important::

    **First give nginx a real server name.** ``make nginx.conf`` writes
    ``server_name _;`` - a catch-all - and certbot's nginx plugin cannot match a
    catch-all to a certificate, so it will not know which block to edit. Replace it
    with the host name people will use:

    .. code-block:: bash

        sudo sed -i 's/server_name  *_;/server_name qatrack.example.com;/' \
            /etc/nginx/sites-available/qatrack.conf
        sudo nginx -t && sudo systemctl reload nginx

Then obtain and install the certificate. The DNS name must already resolve to this
server, and port 80 must be reachable from the internet:

.. code-block:: bash

    sudo apt install certbot python3-certbot-nginx
    sudo certbot --nginx -d qatrack.example.com --agree-tos -m you@your-hospital.example --redirect

**Use a real mailbox for the** ``-m`` **address.** Let's Encrypt refuses addresses at
``example.com`` and ``example.org``, and certbot answers *"There seem to be
problems with that address"* and then stops to ask for another one - so the
address in this command is a placeholder you must replace, not one you can run.
That mailbox is where expiry warnings go if renewal ever stops working, which is
the one piece of post-installation mail worth receiving. If your department
genuinely has no address for it, ``--register-unsafely-without-email`` registers
without one and you give up those warnings.

``--redirect`` adds the HTTP-to-HTTPS redirect. certbot installs a renewal timer at
the same time; confirm it with ``systemctl is-active certbot.timer`` and check the
certificate with ``sudo certbot certificates``.

.. note::

    Until you run ``certbot``, the configuration written by ``make nginx.conf``
    serves QATrack+ on port 80 and redirects nothing. It is ``certbot --redirect``
    that adds the redirect to HTTPS, and it sends *everything* that way, including
    ``/.well-known/acme-challenge/``. Let's Encrypt follows that redirect and does
    not validate the certificate while doing so, so renewal still works - but if
    you replace the configuration with one that blocks the path outright, renewal
    will start failing silently.

**Tell QATrack+ about the new name.** Up to here the site has been reached by
the server's IP address, which is what ``ALLOWED_HOSTS`` in
``local_settings.py`` was set to. Django answers a request for any other name
with **400 Bad Request**, so the HTTPS site you have just set up refuses its own
hostname until you add it:

.. code-block:: python

    ALLOWED_HOSTS = ['qatrack.example.com', '10.0.0.5']
    CSRF_TRUSTED_ORIGINS = ['https://qatrack.example.com']

.. code-block:: bash

    sudo supervisorctl restart gunicorn

``CSRF_TRUSTED_ORIGINS`` is what lets a form submitted over HTTPS be accepted; a
site that answers pages but rejects every login is usually missing it.

**Where the reason appears**, if a page comes back 400 and nginx's own logs say
nothing: ``~/web/qatrackplus/logs/gunicorn.log``, which carries
*"Invalid HTTP_HOST header: '...'. You may need to add '...' to ALLOWED_HOSTS"*.
That file holds the application's own errors for everything in this guide, and is
the first place to look when the site is up but a page is not.

Tested on Ubuntu 24.04 with nginx 1.24.0 and certbot 2.9.0.

.. include:: _site_record.rst


Next Steps
----------

* Check the :ref:`the settings page <qatrack-config>` for any available
  customizations you want to add to your QATrack+ installation (don't forget to
  restart your Nginx and Supervisor services after changing any settings!)

* Automate the :ref:`backup of your QATrack+ installation <qatrack_backup>`.

* Read the :ref:`Administration Guide <admin_guide>`, :ref:`User Guide
  <users_guide>`, and :ref:`Tutorials <tutorials>`.


Last Word
---------

There are a lot of steps getting everything set up so don't be discouraged if
everything doesn't go completely smoothly! If you run into trouble, please get
in touch on the :mailinglist:`mailing list <>`.
