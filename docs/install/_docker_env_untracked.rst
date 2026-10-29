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
left, remove the stash - by its reference, not as a bare ``drop``:

.. code-block:: bash

    git stash drop 'stash@{0}'

**Only run that if** ``git stash pop`` **reported a conflict.** A pop that succeeded
has already removed the stash, and a bare ``git stash drop`` would then delete
whatever stash is now on top - which may be work of yours from weeks ago. If
``git stash list`` no longer shows ``qatrack-4.0.2-upgrade``, there is nothing to
drop and you can skip this.

Your other changes stay in place.

Your ``.env`` is now ignored by git, and later pulls leave it alone. Compare it
with ``deploy/docker/.env.example``, which lists every setting you can now make
there: in particular set ``ALLOWED_HOSTS`` to the names people use to reach
QATrack+. Keep ``qatrack.env.backup`` somewhere safe, or delete it: it holds your
database password.

If your server is a Windows machine, see :ref:`the note on line endings
<docker_line_endings>` in the installation guide as well.

Check you are on the release branch
-----------------------------------

Installations made before 4.0.2 were told to ``git clone`` without naming a branch, which
leaves the checkout on ``master`` rather than on a release. ``git pull`` then follows
``master``, so the site can pick up work that has not been released. The install guide now
checks out ``releases/4.0``; move an existing installation onto it once:

.. code-block:: bash

    cd ~/web/qatrackplus
    git branch --show-current

If that prints anything other than ``releases/4.0``, switch to it. Do this **with the same
care as the** ``.env`` **steps above** - it is the same hazard, because switching branches also
replaces tracked files you may have edited:

.. code-block:: bash

    git checkout releases/4.0

``git branch --show-current`` printing ``releases/4.0`` afterwards is the whole check. A
site already on the branch needs none of this.

.. note::

    ``manage.py`` and the admin report the version from ``qatrack/settings.py``, which is
    set by hand. A checkout of ``master`` therefore reports a release number too, so the
    branch name is the only thing that tells you which code you are running.

