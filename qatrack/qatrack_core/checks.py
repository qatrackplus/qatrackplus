import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register()
def check_media_folder_permissions(app_configs, **kwargs):
    errors = []
    media_root = getattr(settings, 'MEDIA_ROOT', None)
    
    # Check if MEDIA_ROOT is configured and if the directory exists
    # This check is very likely unnecessary, since Django appears to recreate the folder on manage.py check, but it is here for completeness.

    if not media_root:
        errors.append(Error("The Media folder is not configured"))
        return errors
        
    media_root_path = Path(media_root)

    if not media_root_path.exists():
        errors.append(Error(f"The Media folder '{media_root}' does not exist"))
        return errors
    # End of redundant check    
    
    uploads_dirs = [
        media_root_path,
        media_root_path / 'uploads',
        media_root_path / 'uploads' / 'tmp',
    ]
    

    for directory in uploads_dirs:
        if directory.exists():
            if not directory.is_dir() or not os.access(directory, os.W_OK):
                errors.append(
                    Error(
                        f"The Django server process does not have write permissions to '{directory}'.",
                        hint=f"Check folder permissions. You may need to run `sudo chown -R www-data:www-data {media_root}` and `sudo chmod -R 775 {media_root}` (replace www-data with your web server user).",
                        id='qatrack.E001',
                    )
                )
            else:
                try:
                    fd, temp_path = tempfile.mkstemp(dir=str(directory))
                    os.close(fd)
                    Path(temp_path).unlink()
                except Exception as e:
                    errors.append(
                        Error(
                            f"The Django server process could not create a file in '{directory}': {e}",
                            hint="Check folder permissions and disk space.",
                            id='qatrack.E002',
                        )
                    )
        else:
            parent = directory.parent
            if parent.exists() and not os.access(parent, os.W_OK):
                errors.append(
                    Error(
                        f"The Django server process does not have write permissions to '{parent}' to create '{directory}'.",
                        hint=f"Check folder permissions. You may need to run `sudo chown -R www-data:www-data {media_root}`.",
                        id='qatrack.E001',
                    )
                )
    return errors


@register()
def check_translation_catalogues(app_configs, **kwargs):
    """Warn when a committed .mo no longer matches the .po beside it.

    A Warning rather than an Error on purpose. System checks run before
    `migrate` unless --skip-checks is passed, and a site part-way through
    editing its own translations should not be locked out of its migrations
    for it.
    """
    from qatrack.qatrack_core.translation_catalogues import catalogue_problems

    try:
        problems = catalogue_problems()
    except Exception:  # noqa: BLE001
        # Deliberately broad. This runs during system checks, which run before
        # `migrate`, and the docstring above promises it will not lock a site out
        # of its migrations. `OSError` alone was not enough: a malformed .po can
        # raise from the parser, and `locale_root` can raise AttributeError if
        # PROJECT_ROOT is unset. A diagnostic that cannot report is worth less
        # than a `migrate` that cannot run.
        return []

    return [
        Warning(
            problem,
            hint=(
                "The .po is what translators edit; the .mo is what Django reads. "
                "Recompile so the two agree."
            ),
            id='qatrack.W010',
        )
        for problem in problems
    ]


def procedure_uses_pyplot(source):
    """The names a calculation procedure uses to reach `matplotlib.pyplot`.

    Returned sorted, empty when it does not touch pyplot.

    Parsed rather than searched. A procedure is Python, and `grep` for "pyplot"
    finds it in a comment, in a docstring and in a string literal, none of which
    draw anything. A site with a warning it cannot act on learns to ignore
    warnings.

    Two routes, because both work here:

    * importing it - `import matplotlib.pyplot as plt`, or
      `from matplotlib import pyplot`;
    * reaching it through the module the calculation context already provides -
      `matplotlib.pyplot.plot(...)`, with no import at all, because
      DEFAULT_CALCULATION_CONTEXT hands procedures `matplotlib` whole.

    A syntax error is not this function's problem: it returns nothing and lets
    whatever reports broken procedures report it.
    """
    import ast

    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []

    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'matplotlib.pyplot' or alias.name == 'pylab':
                    found.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == 'matplotlib':
                for alias in node.names:
                    if alias.name == 'pyplot':
                        found.add(alias.asname or 'pyplot')
            elif node.module == 'matplotlib.pyplot':
                found.add('matplotlib.pyplot')
        elif isinstance(node, ast.Attribute) and node.attr == 'pyplot':
            if isinstance(node.value, ast.Name) and node.value.id == 'matplotlib':
                found.add('matplotlib.pyplot')

    return sorted(found)


@register(Tags.database)
def check_calculation_procedures_use_pyplot(app_configs=None, databases=None, **kwargs):
    """Warn when a calculation procedure draws with pyplot.

    `matplotlib.pyplot` keeps its figures in module-level state, so two
    procedures plotting at once in one process share it. QATrack+ makes that
    worse rather than better: `clean_mpl` in `qa/views/perform.py` calls
    `plt.clf()` and `plt.close('all')` after a view that may have plotted, and
    both act on **every** figure in the process rather than this request's. The
    function's own docstring says pyplot is not threadsafe, and the
    `except KeyError` wrapped round it is commented as failing "when multiple
    uploads are being analyzed at same time" - which is this, already observed.

    **Whether it can happen depends on how the site serves requests, which this
    check cannot see.** A system check runs under `manage.py`, in its own
    process; nothing tells it what is serving. The shipped Linux and Docker
    deployments configure gunicorn with sync workers, one request per process,
    and are safe by that configuration rather than by anything in the code. The
    shipped Windows deployment runs CherryPy's thread pool and is not.

    So this reports the half it can establish - that the procedures are written
    the vulnerable way - and the hint tells the reader which deployment turns it
    into a fault. A Warning, never an Error: the site may be on a configuration
    where it cannot happen, and in any case nothing is repaired by refusing to
    let them migrate.

    The failure is not a crash. It is a plot saved against the wrong test, or an
    empty one, in a record a physicist will read as evidence.

    Registered under Tags.database like `qatrack.W011`, so it runs on `migrate`
    and on `check --database <alias>` and costs nothing on every other command.
    On a first `migrate` the tables do not exist yet, so nothing is reported
    until the next run.
    """
    if not databases:
        return []

    from django.apps import apps
    from django.db import connections
    from django.db.utils import DatabaseError

    try:
        Test = apps.get_model('qa', 'Test')
    except LookupError:  # pragma: no cover - qa is always installed
        return []

    offenders = []
    seen = set()

    for alias in databases:
        connection = connections[alias]

        # Unreachable or un-migrated is not this check's business, exactly as
        # for W011: other checks report a broken connection, and a fresh
        # install's first `migrate` must not be derailed by a diagnostic.
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except (DatabaseError, OSError):
            continue

        if Test._meta.db_table not in tables:
            continue

        try:
            procedures = (
                Test.objects.using(alias)
                .exclude(calculation_procedure=None)
                .exclude(calculation_procedure='')
                .values_list('pk', 'name', 'calculation_procedure')
            )
            procedures = list(procedures)
        except DatabaseError:
            continue

        for pk, name, source in procedures:
            if pk in seen:
                continue
            names = procedure_uses_pyplot(source or '')
            if names:
                seen.add(pk)
                offenders.append((name, names))

    if not offenders:
        return []

    offenders.sort()
    shown = offenders[:10]
    listed = ', '.join('"%s" (%s)' % (name, ', '.join(names)) for name, names in shown)
    if len(offenders) > len(shown):
        listed += ', and %d more' % (len(offenders) - len(shown))

    return [
        Warning(
            "%d calculation procedure(s) draw with matplotlib.pyplot: %s. pyplot "
            "holds its figures in module-level state, so two procedures plotting "
            "at the same time in one process can take each other's figures - and "
            "QATrack+ clears every figure in the process after a plot, not just "
            "the one it made. The result is a plot saved against the wrong test, "
            "or an empty one." % (len(offenders), listed),
            hint=(
                "Rewrite them to use UTILS.get_figure(), which returns a figure "
                "with its own canvas and cannot be taken by another "
                "calculation:\n\n"
                "    fig = UTILS.get_figure()\n"
                "    ax = fig.add_subplot(111)\n"
                "    ax.plot(xs, ys)\n"
                "    UTILS.write_file('plot.png', fig)\n\n"
                "Whether this can bite you depends on how you serve QATrack+, "
                "which a system check cannot see. The shipped Windows deployment "
                "serves requests on a CherryPy thread pool and shares one "
                "process, so it is exposed. The shipped Linux and Docker "
                "deployments run gunicorn with sync workers, one request per "
                "process, and are not - but that is their current configuration "
                "rather than a guarantee, and adding threads or workers with "
                "threads would change it. This is a warning, not an error: "
                "nothing here stops you migrating."
            ),
            id='qatrack.W012',
        )
    ]
