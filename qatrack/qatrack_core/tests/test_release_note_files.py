"""Release-note files in ``changes/``: the names a release can merge.

The rules are in ``changes/README.md``.
"""

import re
from pathlib import Path

import pytest

NOTES_DIR = Path(__file__).resolve().parents[3] / 'changes'
NAME = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?_[a-z0-9]+(?:-[a-z0-9]+)*\.md$')


def note_files():
    return sorted(p for p in NOTES_DIR.iterdir() if p.is_file() and p.name != 'README.md')


def test_the_folder_and_its_readme_exist():
    assert (NOTES_DIR / 'README.md').is_file()


def test_each_file_is_named_for_its_author_and_purpose():
    misnamed = [p.name for p in note_files() if not NAME.match(p.name)]
    assert not misnamed, (
        'name these <user>_<purpose>.md, with a lowercase, hyphenated purpose (see changes/README.md): %s' % misnamed
    )


def content_problems(name, text):
    """What is wrong with one note file's text: no bullet, or a heading (indented up to three spaces)."""
    lines = text.splitlines()
    problems = []
    if not any(line.startswith('* ') for line in lines):
        problems.append("%s has no '* ' bullet" % name)
    if any(re.match(r' {0,3}#', line) for line in lines):
        problems.append('%s has a heading; the release decides which version it goes under' % name)
    return problems


def test_each_file_holds_bullets_and_no_heading():
    problems = []
    for path in note_files():
        problems += content_problems(path.name, path.read_text(encoding='utf-8'))
    assert not problems, problems


@pytest.mark.parametrize(
    'text, ok',
    [
        ('* **QA**: Corrected a display.\n', True),
        ('* **QA**: Corrected a display.\n  A second paragraph.\n', True),
        ('* **QA**: Corrected a display.\n## 9.0\n', False),
        ('* **QA**: Corrected a display.\n   ## 9.0\n', False),
        ('No bullet at all.\n', False),
    ],
)
def test_the_content_rule(text, ok):
    assert (content_problems('x.md', text) == []) is ok


@pytest.mark.parametrize(
    'name, ok',
    [
        ('nsmela_docker-port.md', True),
        ('crcrewso_tz-rules-2026f.md', True),
        ('some-user_x.md', True),
        ('nsmela_docker_port.md', False),
        ('nsmela_Docker-Port.md', False),
        ('nsmela_docker-port.txt', False),
        ('docker-port.md', False),
        ('-nsmela_docker-port.md', False),
        ('README.md', False),
    ],
)
def test_the_name_rule(name, ok):
    assert bool(NAME.match(name)) is ok
