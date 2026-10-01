"""Make the database enforce the uniqueness the models declare.

Some backends silently stop enforcing a unique constraint. `mssql-django` drops a
unique index when an unrelated `AlterField` retypes a model's primary key and never
recreates it, and the 4.0 migrations do that to every model - so a SQL Server
installation accepts duplicates the ORM believes are impossible, with no
`IntegrityError` and nothing in a log. `qatrack.W011` reports which constraints are
affected; `manage.py check_unique_constraints` reports the rows that block repairing
them.

**This module names no database engine.** An earlier version guarded on
`connection.vendor == 'microsoft'`, which was a proxy for "this engine has the bug" -
a statement about today's `mssql-django` rather than about the database in front of
it. Instead, each constraint is repaired only if the database is *not currently
enforcing it*, which is the real condition. On an engine that enforces what it is
told, every constraint is skipped and this does nothing; measured on SQLite,
PostgreSQL 15 and MySQL 8, all three report nothing to repair. If another backend ever
develops the same fault, this fixes it without being changed.

**Django generates the SQL, not this module.** `schema_editor.add_constraint` with a
`UniqueConstraint` lets each backend emit its own syntax, including the `WHERE ... IS
NOT NULL` that a nullable column needs on SQL Server - where NULLs are treated as
equal, unlike every other engine here. It also degrades correctly: Django returns no
SQL at all where `supports_partial_indexes` is False (MySQL), rather than this module
emitting something invalid.

**It changes no migration state.** The models already declare this uniqueness and the
migration graph already records it - the database is what diverged. So the callers are
`RunPython` with no `state_operations`, and running them cannot make `makemigrations`
report a change.

**It skips rather than fails.** A site may already hold rows that violate a constraint
nothing was enforcing. Creating the index would fail, and failing here aborts the
upgrade for exactly the installations that most need it.
"""

import hashlib

from django.db.models import Count, Q, UniqueConstraint


def constraint_name(model, fields):
    """A deterministic name, short enough for any backend's identifier limit.

    Deterministic because it is what makes `repair_unique_constraints` idempotent and
    lets `remove_repaired_constraints` find only what this created - never an index the
    database had of its own.
    """
    table = model._meta.db_table
    digest = hashlib.sha1(("%s:%s" % (table, ",".join(fields))).encode()).hexdigest()[:8]
    return "qatrack_uniq_%s_%s" % (table[:40], digest)


def _build(model, fields, nullable):
    """The constraint to add: filtered when any of its columns may be NULL.

    The condition is what makes this match Django's semantics rather than SQL Server's.
    Django permits many NULLs in a nullable unique column - standard SQL treats them as
    distinct - so an unfiltered unique index would reject a second NULL row that the
    application considers perfectly valid.
    """
    condition = Q(**{"%s__isnull" % f: False for f in nullable}) if nullable else None
    return UniqueConstraint(
        fields=list(fields),
        name=constraint_name(model, fields),
        condition=condition,
    )


def _columns(model, fields):
    return frozenset(model._meta.get_field(f).column for f in fields)


def _is_enforced(connection, model, fields):
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(
            cursor, model._meta.db_table
        )
    wanted = _columns(model, fields)
    return any(
        d.get("unique") and d.get("columns") and frozenset(d["columns"]) == wanted
        for d in constraints.values()
    )


def _duplicate_count(connection, model, fields, nullable):
    """Groups of rows sharing a value, NULLs excluded.

    Excluded because the constraint built above excludes them too: a row with a NULL in
    a nullable column is not a duplicate, so counting those groups would report rows
    the repair does not care about.
    """
    qs = model._default_manager.using(connection.alias)
    for f in nullable:
        qs = qs.exclude(**{"%s__isnull" % f: True})
    return (
        qs.values(*fields)
        .annotate(_n=Count("pk"))
        .filter(_n__gt=1)
        .count()
    )


def repair_unique_constraints(apps, schema_editor, specs, log=None):
    """Add a unique constraint for each spec the database is not enforcing.

    `specs` is a sequence of (app_label, model_name, field_names, nullable_field_names).
    Returns counts so a caller - or a test - can assert on what happened rather than
    parsing output.
    """
    connection = schema_editor.connection
    result = {"created": [], "already_enforced": [], "blocked": [], "unsupported": []}

    def say(message):
        if log is not None:
            log(message)

    for app_label, model_name, fields, nullable in specs:
        model = apps.get_model(app_label, model_name)
        label = "%s.%s %s" % (app_label, model_name, list(fields))

        if _is_enforced(connection, model, fields):
            result["already_enforced"].append(label)
            continue

        if nullable and not connection.features.supports_partial_indexes:
            # Django would emit nothing here. Say so rather than letting it look repaired.
            result["unsupported"].append(label)
            say("  %s: not repaired - %s cannot express a partial unique index"
                % (label, connection.vendor))
            continue

        duplicates = _duplicate_count(connection, model, fields, nullable)
        if duplicates:
            result["blocked"].append((label, duplicates))
            say(
                "  %s: NOT repaired - %d duplicated value(s) already present. Run "
                "`manage.py check_unique_constraints` to list them, resolve them, then "
                "re-run this migration." % (label, duplicates)
            )
            continue

        schema_editor.add_constraint(model, _build(model, fields, nullable))
        result["created"].append(label)
        say("  %s: unique constraint restored%s"
            % (label, " (NULLs excluded)" if nullable else ""))

    return result


def remove_repaired_constraints(apps, schema_editor, specs):
    """Reverse of `repair_unique_constraints`: remove only what it added.

    Keyed on the generated name, so a constraint the database had of its own is left
    alone. A name that is not present is not an error - the forward pass skips
    constraints that were already enforced, so there is nothing to remove for those.
    """
    connection = schema_editor.connection
    for app_label, model_name, fields, nullable in specs:
        model = apps.get_model(app_label, model_name)
        name = constraint_name(model, fields)
        with connection.cursor() as cursor:
            existing = connection.introspection.get_constraints(
                cursor, model._meta.db_table
            )
        if name in existing:
            schema_editor.remove_constraint(model, _build(model, fields, nullable))
