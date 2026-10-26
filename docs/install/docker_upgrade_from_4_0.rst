.. _docker_upgrade_from_4_0:

Upgrading a Docker 4.0.0 installation to 4.0.1
================================================

4.0.1 is a patch release containing **no database migrations**. On Docker the
upgrade is a code update, a dependency sync and a restart:

1. ``git fetch`` and ``git pull``
2. ``docker compose build``
3. ``docker compose up -d``
4. ``manage.py check`` and ``manage.py migrate`` inside the container

You never name a version. The installation guide checks out the ``releases/4.0``
*branch* rather than a version tag, so the branch carries each patch as it is released
and a ``git pull`` is all that moves you between them.

**These steps apply to any 4.0.x patch**, not only this one. What changes between
patches is in the next section.

.. note::

    The service and scheduled task names stopped carrying version numbers in 4.0.0
    precisely so that patch upgrades would not require renaming anything. If you
    upgraded to 4.0.0 from v3.x, your service is called *QATrack+ Web Service* and your
    scheduled task *QATrack+ Django Q Cluster*.

.. include:: _upgrade_4_0_before.rst

.. _docker_upgrade_check_compose:

Before you pull: check your Docker Compose version
--------------------------------------------------

From 4.0.2, QATrack+ needs **Docker Compose 2.17 or newer** and **Docker Engine
23.0 or newer** (see :ref:`docker_minimum_versions` for why). Check both *before*
``git pull``:

.. code-block:: bash

    docker compose version
    docker version --format '{{.Server.Version}}'

With an older Compose, once you have pulled, every command that builds or creates
containers stops: ``up``, ``build``, ``run`` (so ``restore-media`` too), ``create``
and ``pull``, as well as ``config``. The error looks like this:

.. code-block:: text

    services.django.build Additional property additional_contexts is not allowed

Your current containers aren't affected: they keep running, and ``ps``, ``logs``,
``exec``, ``stop``, ``start`` and ``restart`` still work. But you can't build or
start 4.0.2 until Docker is updated, and if you run ``docker compose down`` in the
meantime, ``up`` can't create the containers again, so your site stays down until
then.

If either version is too old, update Docker first (on Ubuntu, through Docker's ``apt``
repository, which updates the Engine and the ``docker-compose-plugin`` package
together), then carry on with the upgrade. If you have already pulled and see that
error, updating Docker is the fix too: nothing else needs undoing.

.. _docker_upgrade_env_untracked:

Upgrading from 4.0.0 or 4.0.1: keep your ``.env``
-------------------------------------------------

From 4.0.2, ``deploy/docker/.env`` is no longer part of the QATrack+ repository,
because it holds your database password. Your copy has your own settings in it, so
on this one upgrade ``git pull`` stops with *Your local changes to the following
files would be overwritten*. Before the first pull to 4.0.2 or later, set your
``.env`` aside and put it back afterwards:

.. code-block:: bash

    cd ~/web/qatrackplus
    cp deploy/docker/.env ../qatrack.env.backup
    git checkout -- deploy/docker/.env
    git stash push -m qatrack-4.0.2-upgrade
    git pull
    git stash list | grep -q qatrack-4.0.2-upgrade && git stash pop
    cp ../qatrack.env.backup deploy/docker/.env

``git stash`` and ``git stash pop`` keep any other changes you have made to
QATrack+'s files, such as a different port in ``deploy/docker/compose.yaml`` or
edits to ``nginx.conf``. 4.0.2 changes ``compose.yaml`` and the nginx files for
the first time since 4.0.0, so without these steps ``git pull`` stops on any of
them you have changed. If ``git stash`` replies *No local changes to save*, that's fine:
the ``grep`` line then skips ``git stash pop``, so an older stash you may have is
left alone. If it asks
*Please tell me who you are*, tell git once, then run ``git stash`` again:

.. code-block:: bash

    git config user.name "QATrack+ administrator"
    git config user.email "you@example.com"

If you edited ``deploy/docker/nginx/conf.d/default.conf``, for example to set up
HTTPS, ``git stash pop`` reports a conflict on it and keeps your stash. 4.0.2 no
longer uses that file: nginx is now configured from ``.env`` (see
:ref:`docker_https`). Save your old copy to compare with, then finish the step:

.. code-block:: bash

    git show 'stash@{0}:deploy/docker/nginx/conf.d/default.conf' > ../old-nginx-default.conf
    git rm -q deploy/docker/nginx/conf.d/default.conf
    git reset -q
    git status

Before you go on, check what ``git status`` lists. If any other file shows a
conflict, most likely ``deploy/docker/compose.yaml``, open it and resolve the
section between the ``<<<<<<<`` and ``>>>>>>>`` markers by hand, keeping your
change and 4.0.2's. ``git stash show -p 'stash@{0}'`` shows every change you had
stashed. Only once all of them are back in place, and no conflict markers are
left, remove the stash:

.. code-block:: bash

    git stash drop

Your other changes stay in place.

Your ``.env`` is now ignored by git, and later pulls leave it alone. Compare it
with ``deploy/docker/.env.example``, which lists every setting you can now make
there: in particular set ``ALLOWED_HOSTS`` to the names people use to reach
QATrack+. If you have set your site's name or domain in the admin's *Websites*
page, leave ``SITE_NAME`` and ``SITE_DOMAIN`` commented out: set in ``.env``, they
replace those on every start. Keep ``qatrack.env.backup`` somewhere safe, or
delete it: it holds your database password.

If your server is a Windows machine, see :ref:`the note on line endings
<docker_line_endings>` in the installation guide as well.

.. _docker_upgrade_keep_secret_key:

Keep your users signed in (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

From 4.0.2, QATrack+ keeps its secret key in a Docker volume, or takes it from
``SECRET_KEY`` in ``.env``. 4.0.0 and 4.0.1 kept it in your QATrack+ folder, at
``deploy/docker/user-data/secret_key.txt``. If you start 4.0.2 without carrying it
over, QATrack+ makes a new key: every user is signed out once, and password-reset
links sent before the upgrade stop working.

To keep the key, copy it into ``.env`` before you start 4.0.2 for the first time:

.. code-block:: bash

    cd ~/web/qatrackplus
    echo "SECRET_KEY=$(cat deploy/docker/user-data/secret_key.txt)" >> deploy/docker/.env

If that file does not exist, there is no key to carry over; skip this step. The
key signs your users' sessions: keep ``.env`` as private as your database
password.

.. _docker_upgrade_stale_follow_ups:

Clear follow-up emails that were never sent (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Docker installations before 4.0.2 did not run QATrack+'s background tasks, so
the follow-up emails of *QC Completed* notices set to *Follow up* were queued but
never sent. 4.0.2 runs background tasks, and the first time it starts it sends
every follow-up still waiting, all at once, however old. Only sites that set up
follow-up notices are affected.

While your current QATrack+ is still running, and before ``docker compose up -d``
starts 4.0.2, see how many are waiting:

.. code-block:: bash

    cd ~/web/qatrackplus/deploy/docker
    docker compose exec -T django python manage.py shell -c "from django.utils import timezone; from django_q.models import Schedule; print(Schedule.objects.filter(name__startswith='follow-up-for-tli-', schedule_type=Schedule.ONCE, next_run__lt=timezone.now()).exclude(repeats=0).count(), 'overdue follow-up emails')"

To remove them instead of sending them:

.. code-block:: bash

    docker compose exec -T django python manage.py shell -c "from django.utils import timezone; from django_q.models import Schedule; print(Schedule.objects.filter(name__startswith='follow-up-for-tli-', schedule_type=Schedule.ONCE, next_run__lt=timezone.now()).exclude(repeats=0).delete()[0], 'overdue follow-up emails removed')"

Follow-ups that are not due yet are kept, and are sent on time.

Running the upgrade
-------------------

From your ``deploy/docker`` directory:

.. code-block:: bash

    cd ~/web/qatrackplus
    git fetch origin
    git pull
    cd deploy/docker
    docker compose build
    docker compose up -d

Then check the installation and run the migration step inside the container:

.. code-block:: bash

    docker compose exec django python manage.py check
    docker compose exec django python manage.py migrate

Before restarting, re-read *What needs your attention in this release* above: the
backup script's environment variables changed in this release.

.. note::

    ``manage.py check`` reports configuration problems, not data problems — it will not
    tell you whether your backups contain a database or whether your groups have the
    permissions they need. Both are covered below.

.. include:: _upgrade_4_0_after.rst
