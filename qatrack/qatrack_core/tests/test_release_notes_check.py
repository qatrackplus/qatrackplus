"""``scripts/check_release_notes.py``, fed diffs rather than a repository."""

import pytest

from scripts import check_release_notes
from scripts.check_release_notes import problem

BULLET = '+++ b/release_notes.md\n@@ -6,0 +7 @@\n+* **Docker**: something changed.\n'
HEADING = '@@ -4,0 +5 @@\n+## 4.1.0\n'
WARNING_LINE = "@@ -4,0 +5 @@\n+**Don't edit this file in a pull request.** Add a file to changes/.\n"
REMOVED_BULLET = '@@ -7 +6,0 @@\n-* **Docker**: something changed.\n'


def test_a_pull_request_adding_a_bullet_is_refused():
    message = problem(BULLET, '')
    assert message and 'changes/<user>_<purpose>.md' in message and 'something changed' in message


def test_a_pull_request_adding_a_heading_is_refused():
    assert problem(HEADING, '')


def test_a_release_that_deletes_the_notes_it_merged_passes():
    assert problem(BULLET + HEADING, 'D\tchanges/nsmela_docker-port.md\n', 'changes/README.md\n') is None


def test_deleting_one_note_while_others_remain_is_not_a_release():
    deleted = 'D\tchanges/nsmela_docker-port.md\n'
    remaining = 'changes/README.md\nchanges/crcrewso_other-change.md\n'
    assert problem(BULLET, deleted, remaining)


@pytest.mark.parametrize(
    'line',
    ['+- **Docker**: dash bullet.', '++ **Docker**: plus bullet.', '+   * **Docker**: indented.', '+   ## 9.0', '+#'],
)
def test_every_markdown_bullet_and_heading_counts(line):
    assert problem('@@ -6,0 +7 @@\n%s\n' % line, '')


@pytest.mark.parametrize(
    'line', ['+    * four spaces is code, not a bullet', '+#hashtag, not a heading', '+  A paragraph.']
)
def test_code_and_prose_do_not_count(line):
    assert problem('@@ -6,0 +7 @@\n%s\n' % line, '') is None


def test_a_bad_base_ref_fails_with_a_message_not_a_traceback(capsys):
    assert check_release_notes.main(['no-such-ref-anywhere']) == 2
    assert 'git diff' in capsys.readouterr().err


def test_deleting_only_the_readme_is_not_a_release():
    assert problem(BULLET, 'D\tchanges/README.md\n')


def test_adding_a_note_file_is_not_a_release():
    assert problem(BULLET, 'A\tchanges/nsmela_docker-port.md\n')


def test_prose_and_removals_are_allowed():
    assert problem(WARNING_LINE + REMOVED_BULLET, '') is None


def test_no_change_at_all_passes():
    assert problem('', '') is None
