Hand back the files 4.0.0 and 4.0.1 left owned by root (optional)
-----------------------------------------------------------------

.. This file is a fragment, pulled into both Docker upgrade guides with
   `.. include::`. It is excluded from the build in conf.py, because an included file
   that is also read as a document has every label in it reported as a duplicate.
   It starts with its title, not this comment, so that the label the first guide puts
   before the include lands on the title.

QATrack+ 4.0.0 and 4.0.1 ran as ``root`` inside their containers, with your
QATrack+ folder itself mounted into them. Everything they wrote there belongs to
``root`` on the server: the ``logs`` folder, and a ``__pycache__`` folder beside
most of the Python code. A test site had several hundred such files.

From 4.0.2, QATrack+ runs from the code built into its image rather than from
this folder, so these files do not affect your running site, and you can leave
them. They only matter if you later work in this folder as yourself. Your
account cannot change them, or remove them from the ``root``-owned folders they
are in, so anything that runs from this folder as you, such as the
:ref:`development overlay <docker_development>`, cannot update them either.

Once 4.0.2 or later is running, see how many there are:

.. code-block:: bash

    cd ~/web/qatrackplus
    find . \( -path ./deploy/docker/backups -o -path ./deploy/docker/user-data \) -prune -o -user root -print | wc -l

If that prints ``0``, there is nothing to do. Otherwise, give them to your own
account:

.. code-block:: bash

    sudo find . \( -path ./deploy/docker/backups -o -path ./deploy/docker/user-data \) -prune -o -user root -exec chown -h "$(id -u):$(id -g)" {} +

**Both commands leave two folders alone, on purpose.** ``deploy/docker/backups``
holds your nightly backups, which are kept readable by ``root`` only (see
:ref:`docker_backups`), and ``deploy/docker/user-data`` is where the private key
of your HTTPS certificate is kept. A plain ``sudo chown -R`` over the whole
QATrack+ folder would hand both to your account, so use the command above
instead.

Do this after the upgrade rather than before it: until 4.0.2 is running, the old
containers keep writing new files as ``root``.
