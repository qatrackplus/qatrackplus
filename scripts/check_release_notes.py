"""Refuse a pull request that writes notes into release_notes.md directly.

Notes go in ``changes/<user>_<purpose>.md`` (see ``changes/README.md``). Only a release
adds bullets or headings to ``release_notes.md``, and a release is recognisable because
it deletes the ``changes/`` files it merged and leaves none behind.

Usage: ``python scripts/check_release_notes.py <base-ref>``
"""

import re
import subprocess
import sys

NOTES = 'release_notes.md'
# A Markdown bullet (* - +) or ATX heading, indented by up to three spaces.
NOTE_LINE = re.compile(r'^ {0,3}(?:[*+-] |#{1,6}(?: |$))')


def added_note_lines(diff):
    """Bullets and headings a unified diff of release_notes.md adds."""
    return [
        line[1:]
        for line in diff.splitlines()
        if line.startswith('+') and not line.startswith('+++') and NOTE_LINE.match(line[1:])
    ]


def deleted_change_files(name_status):
    """``changes/`` notes a ``git diff --name-status`` deletes, the README aside."""
    deleted = []
    for line in name_status.splitlines():
        status, _, path = line.partition('\t')
        if status == 'D' and path.startswith('changes/') and path != 'changes/README.md':
            deleted.append(path)
    return deleted


def remaining_change_files(tree_listing):
    """``changes/`` notes still present after the pull request, the README aside."""
    return [p for p in tree_listing.splitlines() if p.startswith('changes/') and p != 'changes/README.md']


def problem(diff, name_status, tree_listing=''):
    """The message to fail with, or None.

    A release deletes the notes it merged and leaves none, so deleting one unrelated
    file is not enough to pass.
    """
    added = added_note_lines(diff)
    if not added:
        return None
    if deleted_change_files(name_status) and not remaining_change_files(tree_listing):
        return None
    return (
        '%s gains %d note line(s), but this is not a release: put them in '
        'changes/<user>_<purpose>.md instead (see changes/README.md).\n  %s'
        % (NOTES, len(added), '\n  '.join(added[:5]))
    )


class GitError(Exception):
    pass


def git(*args):
    result = subprocess.run(['git', *args], capture_output=True, text=True)
    if result.returncode:
        raise GitError('git %s failed: %s' % (' '.join(args), result.stderr.strip()))
    return result.stdout


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    span = '%s...HEAD' % argv[0]
    try:
        message = problem(
            git('diff', '-U0', span, '--', NOTES),
            git('diff', '--name-status', span, '--', 'changes/'),
            git('ls-tree', '-r', '--name-only', 'HEAD', '--', 'changes/'),
        )
    except GitError as error:
        print(error, file=sys.stderr)
        return 2
    if message:
        print(message, file=sys.stderr)
        return 1
    print('%s: no notes added outside a release' % NOTES)
    return 0


if __name__ == '__main__':
    sys.exit(main())
