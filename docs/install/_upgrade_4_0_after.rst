.. This file is a fragment, pulled into each platform's upgrade guide with
   `.. include::`. It is excluded from the build in conf.py, because an included file
   that is also read as a document has every label in it reported as a duplicate.
   
   It holds what is true of the release regardless of how QATrack+ is deployed, so that
   the per-platform guides differ only where the commands differ - and so that next
   patch's notes are written once rather than three times.

After upgrading
---------------

**Check your group permissions**, once, if any group was created in v3.x. Under
*Authentication and Authorization* → *Groups*, confirm that wherever a group has
*Can change X* it also has *Can view X*.

.. dropdown:: Why those groups are missing it

    Django added a separate ``view`` permission per model in version 2.1, so groups set
    up before that have ``change`` without it. The admin hides this, because Django
    treats ``change`` as implying ``view`` — but some admin widgets check for ``view``
    alone, and a group lacking it sees a field render blank with no error.

**Confirm your backups** — if you act on one thing in this release, make it the MySQL
check at the top of this page.
