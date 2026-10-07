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
    alone, and refuse the request that fills the field in.

.. dropdown:: What this will not fix

    If a Test List's memberships show a test's ID and macro name but **no test
    name**, group permissions are not the cause and granting them will change
    nothing. That is a separate fault, reported as :issues:`#897 <897>` and present in
    every 4.0 release up to and including this one: the admin answers the request
    that fetches the name with a 404 before any permission is considered, so it fails
    for every user including a superuser. A fix is in hand for a later release.

    The permission check above is still worth doing - it is a real cause of a blank
    field in other places, and it costs one look at your groups - but do not expect
    it to restore a missing test name.

**Confirm your backups** — if you act on one thing in this release, make it the
backup check at the top of this page. It applies to MySQL and to PostgreSQL, for
different reasons.
