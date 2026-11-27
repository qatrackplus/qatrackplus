"""Which spelling of a command the documentation hands the reader.

Three invariants, each of which has already gone wrong once:

1. **A retired target must not still be the instruction.** `make schema` was
   retired in this release - the target prints why and exits 1 - while
   `docs/developer/schema.rst` still gave it as *the* way to regenerate the
   diagram, with `poe schema` mentioned afterwards as an alternative. Nothing
   in the suite runs `make`, so nothing noticed.

2. **A command quoted as "what the task runs underneath" must be that
   command.** The guide dual-lists three tools deliberately, so that a reader
   can look the flags up in pytest's, Sphinx's or pre-commit's own
   documentation. That is duplication kept on purpose, and duplication kept on
   purpose is duplication that can drift.

3. **`compilemessages` must not be published without its ignore patterns.**
   Unlike `makemessages`, it has no default ignore patterns (Django's
   `compilemessages.py` declares `--ignore` with `default=[]`), and it collects
   every directory named `locale` below the working directory - `.venv`
   included. `docs/install/` is deliberately out of scope here: a deployed site
   installs with `--no-dev` and so has no poe at all, and whether those pages
   need the ignores is a separate open question about deployments, not about
   which spelling to teach.
"""

import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
DOCS = REPO_ROOT / 'docs'

# Pages written for somebody with a development checkout, which is what makes
# a poe task available to them at all.
I18N_TUTORIALS = (
    DOCS / 'tutorials' / 'internationalization' / 'add_language.rst',
    DOCS / 'tutorials' / 'internationalization' / 'configure_language.rst',
)


def pages():
    """Every documentation page, excluding the build output."""
    return [p for p in DOCS.rglob('*.rst') if '_build' not in p.parts]


def makefile_recipes():
    """Each target's recipe, keyed by target name."""
    recipes = {}
    current = None
    for line in (REPO_ROOT / 'Makefile').read_text(encoding='utf-8').splitlines():
        if line and not line[0].isspace() and ':' in line and not line.startswith('#'):
            name = line.split(':', 1)[0].strip()
            current = None if name.startswith(('.', '_')) or '=' in name or ' ' in name else name
            if current:
                recipes[current] = []
        elif current is not None and line.startswith('\t'):
            recipes[current].append(line)
    return {name: '\n'.join(body) for name, body in recipes.items()}


def retired_targets():
    """Targets that now refuse rather than doing the job.

    Read from the Makefile rather than listed here, so retiring the next one
    brings its documentation under this test without anybody remembering to
    add it.
    """
    return sorted(
        name
        for name, recipe in makefile_recipes().items()
        if 'RETIRED' in recipe and 'exit 1' in recipe
    )


def test_there_is_at_least_one_retired_target_to_check():
    """Otherwise the test below passes by having nothing to look for."""
    assert retired_targets(), (
        'no Makefile target is marked RETIRED with a non-zero exit, so '
        'test_no_page_recommends_a_retired_make_target proves nothing'
    )


@pytest.mark.parametrize('target', retired_targets())
def test_no_page_recommends_a_retired_make_target(target):
    pattern = re.compile(r'(^|[\s`(])make\s+%s(\s|$|`)' % re.escape(target))
    offenders = []
    for page in pages():
        lines = page.read_text(encoding='utf-8').splitlines()
        for index, line in enumerate(lines):
            if not pattern.search(line):
                continue
            # Saying it is retired is the opposite of recommending it, and the
            # word is as likely to be in the sentence beside the command as in
            # the same line - the generated target table puts the name on one
            # row and "RETIRED and broken" on the next.
            nearby = '\n'.join(lines[max(0, index - 3):index + 4]).lower()
            if 'retired' in nearby:
                continue
            offenders.append('%s:%d: %s' % (page.relative_to(REPO_ROOT), index + 1, line.strip()))
    assert not offenders, (
        '`make %s` is retired - it prints why and exits 1 - but these lines still '
        'give it as the command to run:\n  %s' % (target, '\n  '.join(offenders))
    )


def task_command(task):
    """The shell command a one-line `cmd` poe task runs."""
    import tomllib

    for toml in sorted((REPO_ROOT / 'poe_tasks').glob('*.toml')):
        tasks = tomllib.loads(toml.read_text(encoding='utf-8')).get('tasks', {})
        if task in tasks and isinstance(tasks[task], dict) and 'cmd' in tasks[task]:
            return ' '.join(tasks[task]['cmd'].split())
    raise AssertionError('no poe task named %r with a `cmd`' % task)


# The three tools the developer guide names in both spellings, and the task
# each one is. The guide quotes the underlying command; this is what it has to
# agree with.
DUAL_LISTED = [
    ('test', 'pytest'),
    ('lint', 'pre-commit run --all-files'),
    ('docs', 'sphinx-build -W --keep-going -a --fresh-env -b html docs docs/_build/html'),
]


@pytest.mark.parametrize('task,expected', DUAL_LISTED)
def test_each_dual_listed_task_is_still_the_command_the_guide_quotes(task, expected):
    assert task_command(task) == expected, (
        '`poe %s` no longer runs what the developer guide says it runs' % task
    )


@pytest.mark.parametrize('task,expected', DUAL_LISTED)
def test_the_guide_quotes_that_command_and_the_task_beside_it(task, expected):
    guide = (DOCS / 'developer' / 'guide.rst').read_text(encoding='utf-8')
    assert expected in ' '.join(guide.split()), (
        'the developer guide no longer shows what `poe %s` runs, so a reader '
        'cannot look its flags up in the tool\'s own documentation' % task
    )
    assert 'poe %s' % task in guide, (
        'the developer guide names %r without the `poe %s` task beside it' % (expected, task)
    )


@pytest.mark.parametrize('page', I18N_TUTORIALS, ids=lambda p: p.name)
def test_compilemessages_is_never_offered_without_its_ignores(page):
    offenders = []
    for number, line in enumerate(page.read_text(encoding='utf-8').splitlines(), start=1):
        if 'manage.py compilemessages' not in line:
            continue
        if '--ignore=.venv' in line or line.rstrip().endswith('\\'):
            continue
        offenders.append('%s:%d: %s' % (page.relative_to(REPO_ROOT), number, line.strip()))
    assert not offenders, (
        'compilemessages has no default ignore patterns and collects every '
        '`locale` directory below the working directory, `.venv` included - use '
        '`poe compile-messages`, or pass --ignore=.venv --ignore=node_modules:\n  %s'
        % '\n  '.join(offenders)
    )


@pytest.mark.parametrize('page', I18N_TUTORIALS, ids=lambda p: p.name)
def test_each_i18n_tutorial_offers_the_task(page):
    """Guards the test above against passing because the command is simply gone."""
    assert 'poe compile-messages' in page.read_text(encoding='utf-8'), (
        '%s no longer tells the reader how to compile the catalogues' % page.name
    )


def dev_init_body():
    """`dev-init`'s Python body, as the task file carries it."""
    import tomllib

    tasks = tomllib.loads((REPO_ROOT / 'poe_tasks' / 'dev.toml').read_text(encoding='utf-8'))['tasks']
    return tasks['dev-init']['shell']


# Pages that now describe what `poe dev-init` does instead of listing the
# commands it replaced. Describing a task is duplication of the task, and this
# is the kind that goes quietly out of date.
PAGES_DESCRIBING_DEV_INIT = (
    DOCS / 'developer' / 'guide.rst',
    REPO_ROOT / 'CONTRIBUTING.md',
)


@pytest.mark.parametrize('page', PAGES_DESCRIBING_DEV_INIT, ids=lambda p: p.name)
def test_the_superuser_dev_init_documents_is_the_one_it_creates(page):
    """The credentials are printed in two places and created in one."""
    body = dev_init_body()
    match = re.search(r"'DJANGO_SUPERUSER_USERNAME':\s*'([^']+)'", body)
    assert match, 'dev-init no longer sets DJANGO_SUPERUSER_USERNAME'
    username = match.group(1)
    text = page.read_text(encoding='utf-8')
    assert 'dev-init' in text, '%s no longer mentions the task' % page.name
    assert username in text, (
        '%s does not name the superuser `poe dev-init` creates (%r), so somebody '
        'following it cannot log in' % (page.name, username)
    )


def test_the_templates_the_guide_says_dev_init_copies_are_the_ones_it_copies():
    body = dev_init_body()
    copied = re.findall(r"\('deploy/dev/([^']+)',\s*'([^']+)'\)", body)
    assert copied, 'dev-init no longer copies templates from a list of pairs'
    guide = (DOCS / 'developer' / 'guide.rst').read_text(encoding='utf-8')
    missing = [source for source, _ in copied if source not in guide]
    assert not missing, (
        'the developer guide describes `poe dev-init` without naming every '
        'template it copies - missing: %s' % ', '.join(missing)
    )
    assert len(copied) == 3, (
        'dev-init now copies %d templates; the guide says "three files"' % len(copied)
    )


def test_dev_init_still_refuses_rather_than_overwriting():
    """Both pages promise this, and it is the reason to prefer the task."""
    body = dev_init_body()
    assert 'already looks like a set up dev environment' in body, (
        'dev-init no longer refuses an existing environment, which both the '
        'developer guide and CONTRIBUTING.md tell the reader it does'
    )
