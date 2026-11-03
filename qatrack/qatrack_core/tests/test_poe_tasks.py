"""The poe tasks, tested without poe.

These tests read the task definitions with tomllib and run the
Python-interpreter bodies directly with the current interpreter, in a
temporary directory, with stand-ins for the commands they shell out to. That
is enough to prove what each body does to the files it touches, which is where
the bugs were.

**Provenance.** @nsmela offered this file on #868 on 13 Oct, with a table of
what each test should check. The comment carrying it is truncated on GitHub at
5,457 characters - it ends mid-way through `test_python_task_body_compiles`,
and the second file he offered, `test_selenium_setup_cleanup.py`, is not in it
at all. Neither file exists on any branch or anywhere in the repository; a code
search for the test names returns nothing. So the helpers below are his, taken
from the part that did post, and the tests are reconstructed from his table
rather than copied. **If he still has the originals, they should replace this
file** - he measured 12 of 22 failing before the fixes, and a reconstruction
cannot claim to be the same 22.

Where a test could not be reconstructed it is said so in place, rather than
left out quietly: the two `i18n-status` tests covered an msgfmt-parsing
implementation that no longer exists.
"""
import os
import pathlib
import subprocess
import sys
import tomllib

import pytest
from django.conf import settings

REPO_ROOT = pathlib.Path(settings.PROJECT_ROOT).parent


def load_tasks():
    """Every task, from every file pyproject.toml includes."""
    with open(REPO_ROOT / 'pyproject.toml', 'rb') as f:
        includes = tomllib.load(f)['tool']['poe']['include']
    tasks = {}
    for include in includes:
        with open(REPO_ROOT / include, 'rb') as f:
            tasks.update(tomllib.load(f).get('tasks', {}))
    return tasks


TASKS = load_tasks()


def python_bodies():
    for name, task in TASKS.items():
        if isinstance(task, dict) and task.get('interpreter') == 'python' and 'shell' in task:
            yield pytest.param(task['shell'], id=name)


def run_body(name, cwd, env=None):
    """Run one task's Python body the way poe would: as a script, from the repo root."""
    return subprocess.run(
        [sys.executable, '-c', TASKS[name]['shell']],
        cwd=cwd, env={**os.environ, **(env or {})},
        capture_output=True, text=True, timeout=120,
    )


# --------------------------------------------------------------------------
# Every body at least compiles
# --------------------------------------------------------------------------

@pytest.mark.parametrize('body', list(python_bodies()))
def test_python_task_body_compiles(body):
    """The bodies live in TOML basic strings, so the parser unescapes them.

    A lone `\\n` written for Python becomes a real newline before Python ever
    sees it, and the body fails with `SyntaxError: unterminated string
    literal` having run nothing - which is how the original `test-integration`
    shipped. A triple-quoted docstring closes the TOML string outright. This
    test is the guard against both, and against whatever third form the trap
    takes next.
    """
    compile(body, '<poe task body>', 'exec')


# --------------------------------------------------------------------------
# The Makefile analogs must delegate, not carry their own copy
# --------------------------------------------------------------------------

def test_mirror_delegates_to_a_guarded_task():
    """Every `make-test-*` analog is a `ref`, so it cannot drift.

    `make-test-integration` used to hold its own shell copy of the
    provisioning sequence, without the database guard or the TEST name, and
    the five engine analogs shared a `_test-engine` shell task with no
    stale-backup refusal. Running either after an interrupted run destroyed
    the developer's database or settings. A `ref` has nothing to drift from.
    """
    mirrors = {name: task for name, task in TASKS.items() if name.startswith('make-test-')}
    assert mirrors, "no make-test-* tasks found - has the compat layer been renamed?"

    for name, task in sorted(mirrors.items()):
        ref = task.get('ref')
        assert ref, "%s is not a ref: %s" % (name, sorted(task))
        target = ref.split()[0]
        assert target in ('test-engine', 'test-integration'), (name, ref)
        assert 'shell' not in task, "%s carries its own body as well as a ref" % name


def test_the_shell_copy_is_gone():
    """`_test-engine` must not come back while the analogs are refs."""
    assert '_test-engine' not in TASKS


# --------------------------------------------------------------------------
# test-engine: the developer's settings file
# --------------------------------------------------------------------------

@pytest.fixture
def engine_tree(tmp_path):
    """A tree with just enough in it for `test-engine sqlite` to run."""
    (tmp_path / 'qatrack').mkdir()
    (tmp_path / 'qatrack' / 'local_test_settings.sqlite.py').write_text(
        '# the engine template this run should swap in\n', encoding='utf-8')
    # `bin_dir` is vestigial - see test_test_engine_restores_the_original_after
    # _a_run for why faking pytest on PATH does not work: the body invokes it as
    # `python -m pytest`, not as an executable.
    return tmp_path, None


def test_test_engine_refuses_to_overwrite_a_stale_backup(engine_tree):
    """A killed run leaves the real settings in the .bak; copying over it loses them.

    try/finally restores on any Python-level exit, Ctrl-C included, but cannot
    run when the process is killed outright - SIGHUP from a closed terminal, a
    dropped SSH session. @nsmela reproduced the loss end to end on #868.
    """
    tree, bin_dir = engine_tree
    live = tree / 'qatrack' / 'local_test_settings.py'
    backup = tree / 'qatrack' / 'local_test_settings.py.bak'
    live.write_text('# what a later run swapped in\n', encoding='utf-8')
    backup.write_text('# THE DEVELOPER OWN SETTINGS\n', encoding='utf-8')

    result = run_body('test-engine', tree, {'engine': 'sqlite'})

    assert result.returncode != 0, result.stdout
    assert 'already exists' in result.stdout, result.stdout
    assert backup.read_text() == '# THE DEVELOPER OWN SETTINGS\n', "the backup was overwritten"
    assert live.read_text() == '# what a later run swapped in\n', "the live file was touched"


def test_test_engine_restores_the_original_after_a_run(engine_tree):
    """The normal case, so the refusal above cannot be satisfied by refusing always.

    The body runs `python -m pytest`, which in a bare temporary tree collects
    nothing and exits 5. That is not what is under test and the assertions do
    not look at it - what matters is that the file the developer had is the
    file they have afterwards, whatever pytest said. A traceback would mean
    the body itself broke, so that is checked instead.
    """
    tree, bin_dir = engine_tree
    live = tree / 'qatrack' / 'local_test_settings.py'
    live.write_text('# mine\n', encoding='utf-8')

    result = run_body('test-engine', tree, {'engine': 'sqlite'})

    assert 'Traceback' not in result.stderr, result.stderr
    assert live.read_text() == '# mine\n'
    assert not (tree / 'qatrack' / 'local_test_settings.py.bak').exists()


def test_test_engine_leaves_no_settings_file_when_there_was_none(engine_tree):
    """And does not invent one: a developer with no local_test_settings.py had none."""
    tree, bin_dir = engine_tree

    result = run_body('test-engine', tree, {'engine': 'sqlite'})

    assert 'Traceback' not in result.stderr, result.stderr
    assert not (tree / 'qatrack' / 'local_test_settings.py').exists()


def test_test_engine_says_which_template_is_missing(engine_tree):
    tree, bin_dir = engine_tree

    result = run_body('test-engine', tree, {'engine': 'mysql'})

    assert result.returncode != 0
    assert 'local_test_settings.mysql.py' in result.stdout, result.stdout


# --------------------------------------------------------------------------
# dev-init: a failure must not block the next attempt
# --------------------------------------------------------------------------

def test_dev_init_undoes_what_it_created_when_a_step_fails(tmp_path):
    """Otherwise the rerun refuses, which is the problem dev-init exists to fix.

    The settings files are copied before `migrate` runs. With nothing to undo
    them, a failed migrate left all three in place, and the next `dev-init`
    answered 'This already looks like a set up dev environment' and exited 1.
    """
    (tmp_path / 'qatrack').mkdir()
    (tmp_path / 'deploy' / 'dev').mkdir(parents=True)
    for name in ('local_settings.dev.py', 'local_test_settings.sqlite.py',
                 'local_test_settings.memory.py'):
        (tmp_path / 'deploy' / 'dev' / name).write_text('# template\n', encoding='utf-8')
    # A manage.py that fails, standing in for a migrate that cannot run.
    (tmp_path / 'manage.py').write_text('import sys\nsys.exit(3)\n', encoding='utf-8')

    first = run_body('dev-init', tmp_path)
    assert first.returncode == 3, (first.returncode, first.stdout, first.stderr)

    left = sorted(p.name for p in (tmp_path / 'qatrack').iterdir())
    assert left == [], "dev-init left %s behind, so the rerun will refuse" % left

    # And the rerun gets as far as calling manage.py again, rather than
    # refusing up front - which is the whole point.
    second = run_body('dev-init', tmp_path)
    assert second.returncode == 3, second.stdout
    assert 'already looks like a set up dev environment' not in second.stdout, second.stdout


def test_dev_init_still_refuses_an_environment_it_did_not_create(tmp_path):
    """The negative control: the undo must not weaken the up-front refusal."""
    (tmp_path / 'qatrack').mkdir()
    (tmp_path / 'deploy' / 'dev').mkdir(parents=True)
    for name in ('local_settings.dev.py', 'local_test_settings.sqlite.py',
                 'local_test_settings.memory.py'):
        (tmp_path / 'deploy' / 'dev' / name).write_text('# template\n', encoding='utf-8')
    (tmp_path / 'qatrack' / 'local_settings.py').write_text('# mine, already here\n', encoding='utf-8')

    result = run_body('dev-init', tmp_path)

    assert result.returncode == 1
    assert 'already looks like a set up dev environment' in result.stdout, result.stdout
    assert (tmp_path / 'qatrack' / 'local_settings.py').read_text() == '# mine, already here\n'


# --------------------------------------------------------------------------
# The catalogue tasks
# --------------------------------------------------------------------------

def test_check_messages_can_fail():
    """`python manage.py check` cannot: qatrack.W010 is a Warning, and check exits 0.

    Measured on #868 with one translation added to fr/django.po and not
    compiled: `manage.py check` printed W010 and exited 0, while
    `manage.py check_translations` reported the catalogue and exited 1. A task
    that reports a problem and then reports success is worse than no task.

    This asserts the wiring; that check_translations itself exits non-zero is
    covered in qatrack/qatrack_core/tests/test_translation_catalogues.py.
    """
    cmd = TASKS['check-messages']['cmd']
    assert 'check_translations' in cmd, cmd
    assert cmd.split()[-1] != 'check', "back on `manage.py check`, which exits 0 for a Warning"


def test_i18n_status_delegates_rather_than_parsing_msgfmt():
    """Reconstructed differently from @nsmela's table, and this says why.

    His two tests for this task - that the counts are the same in any locale,
    and that a catalogue msgfmt cannot read makes it fail - covered a Python
    body that parsed msgfmt's `--statistics` prose. That body is gone: the task
    is now a `ref` to `check-messages`, which computes coverage in Python from
    the .po files, so there is no msgfmt output to parse, no locale to depend
    on and no exit code to ignore. The faults cannot recur in the same form,
    so what is left to assert is that the implementation has not come back.
    """
    task = TASKS['i18n-status']
    assert task.get('ref') == 'check-messages', task
    assert 'shell' not in task, "i18n-status has a body again - see the docstring"


def test_the_autobuild_port_is_the_documented_one():
    """poe said 8008 and the Makefile said 8009; the docs say 8008 four times.

    The Makefile now names no port at all, which is the real fix: there is one
    place for it to be wrong instead of two.
    """
    default = TASKS['docs-autobuild']['args'][0]['default']
    assert default == '8008', default
    makefile = (REPO_ROOT / 'Makefile').read_text(encoding='utf-8')
    assert '--port' not in makefile, "the Makefile has a port of its own again"


# --------------------------------------------------------------------------
# The Makefile holds aliases and nothing else
# --------------------------------------------------------------------------

def makefile_recipe_lines():
    """Every recipe line - the tab-indented ones - with its target."""
    target = None
    for line in (REPO_ROOT / 'Makefile').read_text(encoding='utf-8').splitlines():
        if line and not line[0].isspace() and ':' in line and not line.startswith('#'):
            target = line.split(':', 1)[0].strip()
        elif line.startswith('\t') and target:
            yield target, line.strip()


def test_every_makefile_target_only_calls_poe():
    """Two runners with two implementations drift, and this one did.

    `make-test-integration` stopped matching `make test-integration`,
    `docs-autobuild` served on a different port under each, and the two
    engine-swap implementations disagreed about refusing a backup left by an
    interrupted run - which is how one of them came to destroy a developer's
    settings. Every recipe line now either prints help or calls poe, so there
    is one implementation to be wrong.
    """
    offenders = [
        (target, line) for target, line in makefile_recipe_lines()
        if target not in ('help', '.PHONY')
        and not line.startswith('$(POE)')
        and not line.startswith('@echo')
    ]
    assert not offenders, offenders


def test_the_makefile_has_a_target_for_every_habit_it_used_to_serve():
    """A rewrite is the easy place to drop a target somebody's script calls."""
    makefile = (REPO_ROOT / 'Makefile').read_text(encoding='utf-8')
    for target in ('test', 'test_simple', 'test-sqlite', 'test-memory',
                   'test-postgres', 'test-mysql', 'test-mssql',
                   'test-integration', 'cover', 'cover-mo', 'cover-module',
                   'cover-qatrack', 'docs', 'docs-autobuild', 'dumpdata',
                   'nginx.conf', 'supervisor.conf', 'schema', 'run', 'help'):
        assert ('\n%s:' % target) in makefile, "no %s target" % target


def test_every_poe_task_a_makefile_target_names_exists():
    """An alias to a task that does not exist fails at run time, not at edit time."""
    missing = []
    for target, line in makefile_recipe_lines():
        if not line.startswith('$(POE)'):
            continue
        task = line.split()[1]
        if task not in TASKS:
            missing.append((target, task))
    assert not missing, missing
