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
left out quietly: the two translation-status tests covered an msgfmt-parsing
implementation that no longer exists.
"""
import os
import pathlib
import re
import shlex
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


def test_translation_status_does_not_parse_msgfmt_again():
    """Reconstructed differently from @nsmela's table, and this says why.

    His two tests - that the counts are the same in any locale, and that a
    catalogue msgfmt cannot read makes it fail - covered a Python body that
    parsed msgfmt's `--statistics` prose. That body is gone: the work is done by
    `manage.py check_translations`, which computes coverage in Python from the
    .po files, so there is no msgfmt output to parse, no locale to depend on and
    no exit code to ignore. The faults cannot recur in the same form, so what is
    left to assert is that the implementation has not come back.

    Asserted against `check-messages` rather than the `i18n-status` alias it
    used to carry: that alias was removed on 2026-11-05, and this is the task
    that remains.
    """
    task = TASKS['check-messages']
    assert 'check_translations' in task.get('cmd', ''), task
    assert 'shell' not in task, "check-messages has a body again - see the docstring"
    assert 'msgfmt' not in str(task), "msgfmt is back in the task; see the docstring"


def test_the_autobuild_ports_are_each_what_their_runner_documents():
    """The two runners serve on different ports, and that is now deliberate.

    The Makefile serves on 8009 and the docs say 8008 four times, so the
    successor task is the one that is right. The Makefile is frozen until it
    goes in the 4.1 cycle, so the disagreement cannot be fixed by editing it -
    it is made visible instead: `docs-serve` keeps 8008, and the mirror
    keeps whatever `make docs-autobuild` actually does, which is 8009.

    An earlier commit on this branch took the port out of the Makefile
    altogether. That was part of reducing the Makefile to aliases, which Cody
    reversed on 2026-11-05.
    """
    assert TASKS['docs-serve']['args'][0]['default'] == '8008'
    makefile = (REPO_ROOT / 'Makefile').read_text(encoding='utf-8')
    assert '--port 8009' in makefile, "the Makefile's own autobuild port has moved"
    assert '--port 8009' in TASKS['make-docs-autobuild']['cmd'], (
        "the mirror no longer reproduces the Makefile's port")


# --------------------------------------------------------------------------
# The Makefile is frozen, and poe carries both ways of working
# --------------------------------------------------------------------------

def test_the_makefile_does_not_depend_on_poe():
    """A Makefile recipe that calls poe drags the dev group into production.

    An earlier commit on this branch made every target an alias for
    `$(POE) <task>`. crane measured what that costs on Ubuntu 24.04: `make
    supervisor.conf` on a site synced `--no-dev` took the environment from 112
    packages to 200, because `uv run poe` syncs the default groups first, and
    the removal tasks leave all 88 behind. `--no-dev` on the outer command does
    not help either - poe's uv executor wraps each task in its own `uv run`.

    Cody reversed the alias decision on 2026-11-05. This test is what keeps poe
    out of the Makefile's recipes until the file is removed in the 4.1 cycle.

    NAMING poe is fine; CALLING it is not. Since make is retired, a target that
    was broken now prints the poe task to use instead of running (Cody,
    2026-11-05), and `make help` says the same at the top. An `@echo` that
    mentions poe starts no process and syncs no dependency group, so the test
    looks at what the recipe *executes*.
    """
    offenders = []
    for line in (REPO_ROOT / 'Makefile').read_text(encoding='utf-8').splitlines():
        if 'poe' not in line.lower():
            continue
        stripped = line.strip().lstrip('@-+')
        # A comment explains; an echo prints; neither runs anything.
        if stripped.startswith('#') or stripped.startswith(('echo ', 'echo"')):
            continue
        offenders.append(line)
    assert not offenders, offenders


def test_a_retired_target_says_so_and_fails_rather_than_pretending():
    """The one behavioural claim worth making about the Makefile.

    Nothing in the suite runs `make` - every other Makefile test reads the file
    as text - so a retired target is exactly the kind of thing a well-meaning
    edit could quietly un-retire, restoring a known trap.

    `schema` is retired because it was broken twice over: it named the diagram
    from a version hardcoded in the Makefile, and it exited 0 even when the
    render failed, so it could report success while leaving the committed
    838 KB diagram corrupted. Measured on Ubuntu 24.04, whose Graphviz 2.42
    fails `-g` with "trouble in init_rank".

    Three things are asserted, because any one of them alone could be true of a
    target that still silently does the wrong thing: it does not render, it
    names the replacement, and it fails rather than reporting success.
    """
    recipe = recipe_for('schema')
    assert 'graph_models' not in recipe, (
        'the retired schema target renders the diagram again: %r' % recipe
    )
    assert 'poe schema' in recipe, (
        'the retired schema target does not name the task that replaces it'
    )
    assert 'exit 1' in recipe, (
        'the retired schema target exits 0, so a release script that calls it '
        'cannot tell the diagram was never regenerated'
    )


def recipe_for(target):
    """A target's recipe lines, without the comments above it."""
    text = (REPO_ROOT / 'Makefile').read_text(encoding='utf-8')
    body = text.split('\n%s:\n' % target, 1)[1]
    lines = []
    for line in body.splitlines():
        if line and not line.startswith(('\t', ' ')):
            break
        lines.append(line)
    return '\n'.join(lines)


def mirror_for(target):
    """The task name mirroring a Makefile target; poe forbids a dot in one."""
    return 'make-' + target.replace('.', '-')


def makefile_targets():
    """Every target the Makefile defines, in file order."""
    for line in (REPO_ROOT / 'Makefile').read_text(encoding='utf-8').splitlines():
        if not line or line[0].isspace() or line.startswith('#') or ':' not in line:
            continue
        name = line.split(':', 1)[0].strip()
        if name.startswith(('.', '_')) or '=' in name or ' ' in name:
            continue
        yield name


def test_every_makefile_target_has_a_mirror():
    """Both ways of working are meant to work, which is a claim about coverage.

    `poe <task>` is the cross-platform successor and `poe make-<target>` is the
    Makefile's own behaviour. The second only means anything if there is one
    for every target, so this counts them rather than trusting the file.

    `help` is exempt: it prints a hand-written list of Makefile targets, and
    `poe` with no arguments already lists every task.
    """
    missing = [t for t in makefile_targets()
               if t != 'help' and mirror_for(t) not in TASKS]
    assert not missing, missing


def test_every_mirror_names_a_target_that_exists():
    """A mirror of a target nobody has is a mirror nobody can check."""
    targets = set(makefile_targets())
    orphans = [name for name in TASKS
               if name.startswith('make-')
               and not any(mirror_for(t) == name for t in targets)]
    assert not orphans, orphans


def test_the_makefile_has_a_target_for_every_habit_it_used_to_serve():
    """A rewrite is the easy place to drop a target somebody's script calls."""
    makefile = (REPO_ROOT / 'Makefile').read_text(encoding='utf-8')
    for target in ('test', 'test_simple', 'test-sqlite', 'test-memory',
                   'test-postgres', 'test-mysql', 'test-mssql',
                   'test-integration', 'cover', 'cover-mo', 'cover-module',
                   'cover-qatrack', 'docs', 'docs-autobuild', 'dumpdata',
                   'nginx.conf', 'supervisor.conf', 'schema', 'run', 'help'):
        assert ('\n%s:' % target) in makefile, "no %s target" % target


def test_every_mirror_that_delegates_points_at_a_task_that_exists():
    """A `ref` to a task that does not exist fails at run time, not at edit time."""
    missing = []
    for name, task in TASKS.items():
        if not name.startswith('make-') or not isinstance(task, dict):
            continue
        ref = task.get('ref')
        if ref and ref.split()[0] not in TASKS:
            missing.append((name, ref))
    assert not missing, missing


# --------------------------------------------------------------------------
# The reminder `poe ci` ends with
# --------------------------------------------------------------------------

def test_every_task_the_ci_reminder_names_exists():
    """The reminder is four `print()` calls, so nothing checks what it says.

    It went on telling people to run `poe test-gui-*` for a day after those
    three tasks became one `poe test-gui`. A reminder is only worth printing if
    the commands in it can be pasted.
    """
    body = TASKS['_ci-reminder']['shell']
    named = re.findall(r'\bpoe ([a-z][a-z0-9-]*)', body)
    assert named, "the regex found no task names - the reminder changed shape"
    missing = [name for name in named if name not in TASKS]
    assert not missing, missing


def test_the_ci_reminder_does_not_let_poe_narrate_it():
    """`verbosity = -1` is the whole fix; without it poe prints the source.

    Every other task in `ci` earns its echo - you want to see the pre-commit
    line that failed. This one's source *is* its output, so the echo printed
    the reminder twice: once as six `print()` calls and once as four lines of
    English. Measured on poe 0.49.0, the setting suppresses the echo only: a
    failing task still aborts the sequence by name and still carries its exit
    code out.
    """
    assert TASKS['_ci-reminder'].get('verbosity') == -1


# --------------------------------------------------------------------------
# Nothing needs a POSIX shell unless it says which one and why
# --------------------------------------------------------------------------

# A `shell` task with no `interpreter` gets poe's default, which is a POSIX
# shell. poe's own error message for the Windows case says so outright -
# "Installing Git Bash or using WSL should fix this" (poethepoet/task/
# shell.py). So every such task is a task a Windows developer cannot run, and
# the whole reason these tasks exist is that `make` was one.
#
# `interpreter = "python"` is the portable form, because poe resolves it to the
# interpreter the virtualenv already has. Seventeen of the twenty-three shell
# tasks use it. These six do not, and each one has a reason that is about the
# command rather than about convenience:
SHELL_TASKS_THAT_NEED_A_REAL_SHELL = {
    # Ubuntu-only by declaration, not by accident: the templates under deploy/
    # hardcode a Linux path, the tasks run sudo and write into /etc, and the
    # help text of all four starts "WIP- Ubuntu only". A python interpreter
    # would not make any of that portable. See the header of deploy.toml.
    'nginx-conf': 'installs a Linux nginx site config as root',
    'nginx-conf-remove': 'removes a Linux nginx site config as root',
    'supervisor-conf': 'installs Linux supervisor configs as root',
    'supervisor-conf-remove': 'removes Linux supervisor configs as root',
    # `make docs` shells out to docs/Makefile, so the thing being mirrored
    # needs Make on the host. That is exactly why the `docs` task calls
    # sphinx-build directly, and anyone reaching for the Makefile route has
    # Make already.
    'make-docs': 'mirrors `make docs`, which needs Make either way',
    # Mirrors the Makefile's timestamp, which comes from `date`. The portable
    # route is the `dump-data` task, which builds the same name in Python.
    'make-dumpdata': 'mirrors `make dumpdata`, whose filename comes from `date`',
}


def shell_task_specs():
    """Every `shell` task, including ones written inline inside a `sequence`."""
    for name, spec in TASKS.items():
        if not isinstance(spec, dict):
            continue
        if 'shell' in spec:
            yield name, spec
        for index, step in enumerate(spec.get('sequence') or []):
            if isinstance(step, dict) and 'shell' in step:
                yield '%s[%d]' % (name, index), step


def test_every_shell_task_runs_python_or_says_why_not():
    """A shell task without `interpreter = "python"` needs bash to exist.

    Cody now runs an agent on Windows, so "it works on my machine" has two
    answers. This is the guard that keeps the default honest: reach for a
    POSIX shell only when the command itself is POSIX, and name the task here
    with the reason when you do.
    """
    found = list(shell_task_specs())
    assert found, "no shell tasks found - the walker stopped working"
    unexplained = [name for name, spec in found
                   if spec.get('interpreter') != 'python'
                   and name not in SHELL_TASKS_THAT_NEED_A_REAL_SHELL]
    assert not unexplained, (
        "these shell tasks need a POSIX shell and do not say why; either set "
        "interpreter = \"python\" or add them to "
        "SHELL_TASKS_THAT_NEED_A_REAL_SHELL with a reason: %s" % unexplained)


def test_no_shell_exception_has_outlived_its_reason():
    """An exception list nobody prunes stops being a list of exceptions.

    A name here that has since been ported to python, renamed or deleted
    silences a guard for a task that no longer needs silencing.
    """
    specs = dict(shell_task_specs())
    stale = [name for name in SHELL_TASKS_THAT_NEED_A_REAL_SHELL
             if name not in specs
             or specs[name].get('interpreter') == 'python']
    assert not stale, (
        "drop these from SHELL_TASKS_THAT_NEED_A_REAL_SHELL - they are no "
        "longer shell tasks that need a shell: %s" % stale)


def test_no_cmd_task_relies_on_shell_syntax():
    """poe runs a `cmd` itself, with no shell, so an operator becomes an argument.

    Measured on poe 0.49.0: `cmd = 'python -c "..." && echo second'` runs
    python with `['-c', '&&', 'echo', 'second']` in argv and **exits 0**. The
    chained command never runs and nothing says so. `>` does not redirect
    either. The silence is what makes this worth a guard rather than a
    comment: a task written this way looks like it worked.

    Tokens are compared whole, so an operator inside a quoted argument - a
    help string, a python one-liner - is not flagged. Anything that really
    needs a pipe or a redirect belongs in a `shell` task with
    `interpreter = "python"`.
    """
    operators = {'&&', '||', '|', '>', '>>', '<', '<<', ';', '&', '`'}
    offenders = []
    for name, spec in TASKS.items():
        if not isinstance(spec, dict):
            continue
        commands = [spec['cmd']] if isinstance(spec.get('cmd'), str) else []
        for index, step in enumerate(spec.get('sequence') or []):
            if isinstance(step, dict) and isinstance(step.get('cmd'), str):
                commands.append(step['cmd'])
        for command in commands:
            try:
                tokens = shlex.split(command)
            except ValueError:
                continue  # unbalanced quotes are a different bug
            hits = [t for t in tokens
                    if t in operators or t.startswith('$(')]
            if hits:
                offenders.append((name, hits))
    assert not offenders, offenders


# The number Cody is reacting to, and the only one a reader of `poe` sees:
# public tasks that are not Makefile mirrors. 38 at 2026-11-08, after `cover`
# absorbed `cover-qatrack` and `cover-module` and `dev-clean` went private.
#
# Raising it is a review decision. That is the whole point of the number being
# here: adding a task is easy, and without this the surface grows by default
# and nobody has to argue for it. swift counted 41 on 2026-11-06 and said so -
# `projects/qatrackplus/evidence/2026-11-06-swift-poe-task-architecture-review.md` -
# and the guide's *Adding a new poe task* now says what earns a public name.
MAX_PUBLIC_TASKS = 35


def public_task_names():
    """Every task a `poe` listing shows that is not a Makefile mirror."""
    return sorted(
        name for name in load_tasks()
        if not name.startswith('_') and not name.startswith('make-')
    )


def test_the_public_task_surface_has_not_grown_quietly():
    names = public_task_names()
    assert len(names) <= MAX_PUBLIC_TASKS, (
        'there are now %d public non-mirror tasks, over the %d this test allows.\n\n'
        'If the new one earns its name by the rule in the developer guide - it composes '
        'more than one command, hides a trap, or encodes something a newcomer could not '
        'guess - raise MAX_PUBLIC_TASKS here and say so in the pull request. If it is a '
        'variant of an existing task, it probably wants to be an argument instead, and '
        'if it is a step inside a composite it wants a leading underscore.\n\n%s'
        % (len(names), MAX_PUBLIC_TASKS, ', '.join(names))
    )


def test_the_ceiling_is_not_far_above_the_count():
    """A ratchet that has drifted loose stops ratcheting.

    If several tasks are retired and the ceiling is left where it was, the next
    few additions are free and this test goes quiet for exactly as long as it
    takes for the surface to grow back. Tightening it is part of retiring a
    task.
    """
    names = public_task_names()
    slack = MAX_PUBLIC_TASKS - len(names)
    assert slack <= 2, (
        'MAX_PUBLIC_TASKS is %d and there are %d public tasks, so %d could be added '
        'without this test noticing. Lower the ceiling to %d.'
        % (MAX_PUBLIC_TASKS, len(names), slack, len(names))
    )


# --------------------------------------------------------------------------
# test-gui: one task, two named options
# --------------------------------------------------------------------------

def gui_run(tmp_path, **argv):
    """Run `_test-gui-run`'s body with a pytest that reports its environment.

    poe hands a declared argument to a Python body as an environment variable,
    so this sets `mode` and `browser` the way the wrapper would. The stub
    stands in for `python -m pytest`, which is the only thing the body shells
    out to.
    """
    stub = tmp_path / 'pytest' / '__main__.py'
    stub.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / 'pytest' / '__init__.py').write_text('', encoding='utf-8')
    stub.write_text(
        'import os\n'
        "print('HEADLESS=%s' % os.environ.get('SELENIUM_HEADLESS', ''))\n"
        "print('SLOWMO=%s' % os.environ.get('SELENIUM_SLOW_MO', ''))\n"
        "print('BROWSER=%s' % os.environ.get('SELENIUM_BROWSER', ''))\n",
        encoding='utf-8',
    )
    done = run_body('_test-gui-run', tmp_path, env={'PYTHONPATH': str(tmp_path), **argv})
    assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
    return dict(
        line.split('=', 1) for line in done.stdout.splitlines() if '=' in line and line.isascii()
    ), done.stdout


def test_a_mode_sets_the_variables_it_names(tmp_path):
    seen, out = gui_run(tmp_path, mode='headless')
    assert seen.get('HEADLESS') == 'True', out
    assert seen.get('SLOWMO') == '', out

    seen, out = gui_run(tmp_path, mode='visible')
    assert seen.get('HEADLESS') == 'False', out
    assert seen.get('SLOWMO') == '', out

    seen, out = gui_run(tmp_path, mode='watch')
    assert seen.get('HEADLESS') == 'False', out
    assert seen.get('SLOWMO') == '0.4', (
        'watch no longer slows the run down, which is the only thing that '
        'distinguishes it from visible: %s' % out
    )


def test_omitting_an_option_overrides_nothing(tmp_path):
    """The reason `poe test-gui` with nothing given is still worth having.

    settings.py reads both variables from the environment and
    local_test_settings.py is imported afterwards, so leaving them unset is
    what lets a developer's own choice through. Setting a default here would
    silently take that away.
    """
    seen, out = gui_run(tmp_path)
    assert seen.get('HEADLESS') == '', out
    assert seen.get('SLOWMO') == '', out
    assert seen.get('BROWSER') == '', out
    assert 'mode from your settings' in out, out
    assert 'browser from your settings' in out, out

    # The body cannot see this half. poe applies a declared `default` before
    # the body runs, so a default added to either option would hand it a value
    # and the assertions above would still pass while the behaviour they exist
    # for had gone. Checked here because this is the test that would otherwise
    # be believed - found by mutating the TOML and watching it stay green.
    for arg in TASKS['test-gui'].get('args') or []:
        assert 'default' not in arg, (
            "%s has a default, so `poe test-gui` no longer leaves that half to the "
            "developer's own settings - which is the only reason the bare task is "
            'worth having' % arg['name']
        )


def test_the_browser_option_reaches_selenium(tmp_path):
    seen, out = gui_run(tmp_path, browser='chromium')
    assert seen.get('BROWSER') == 'chromium', out
    assert seen.get('HEADLESS') == '', 'naming a browser should not impose a mode: %s' % out


def test_both_options_are_named_so_their_order_cannot_matter(tmp_path):
    """Measured: two optional *positionals* reject the reversed order.

    `poe a chromium headless` fails with "argument mode: invalid choice:
    'chromium'" - true, and misleading, since the fault is the order. Named
    options cannot have that problem, and this asserts they are named rather
    than trusting the help line.
    """
    args = TASKS['test-gui'].get('args') or []
    by_name = {a['name']: a for a in args}
    assert set(by_name) == {'mode', 'browser'}, by_name
    for name, arg in by_name.items():
        assert arg.get('options'), (
            '%s is not a named option, so `poe test-gui <a> <b>` would depend on the '
            'order the two are typed in' % name
        )
        assert not arg.get('positional'), '%s is positional again' % name
        assert arg.get('choices'), (
            '%s lost its choices, which is what rejects a value the harness does not '
            'know and what drives tab completion' % name
        )
