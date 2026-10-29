"""Every Django system check must own its id.

Two unrelated checks sharing an id cannot be silenced independently: a deployer
who puts that id in ``SILENCED_SYSTEM_CHECKS`` to quieten one message silences
the other as well, without being told.

This is a real defect rather than a hypothetical one. ``qatrack.E002`` was used by
both the media-folder check (the server process could not create a file) and, on
the 4.1 settings branch, the unedited-placeholder check - so silencing a cosmetic
template warning would also have hidden an unwritable ``MEDIA_ROOT``. A second
collision on ``qatrack.W001`` existed at the same time between two branches that
had each invented it, and surfaced only when they were brought together.

The ids are read from the source rather than from Django's check registry on
purpose: a check's id appears only in the ``Error`` or ``Warning`` it returns, so
walking the registry cannot see an id until something makes that check fail. A
source-level read sees every id whether or not it fires.
"""

import ast
import pathlib

from django.test import SimpleTestCase

from qatrack.qatrack_core import checks


def _ids_by_check(source):
    """Map each check id to the set of function names that return it."""
    owners = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.keyword) or inner.arg != 'id':
                continue
            value = inner.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                owners.setdefault(value.value, set()).add(node.name)
    return owners


class TestCheckIdsAreUnique(SimpleTestCase):

    def setUp(self):
        self.source = pathlib.Path(checks.__file__).read_text(encoding='utf-8')

    def test_ids_were_found_at_all(self):
        """Guard the guard: a refactor that moves the ids elsewhere would
        otherwise make this file silently vacuous."""
        assert _ids_by_check(self.source), (
            'no check ids found in %s - if the checks have moved, move this test '
            'with them rather than deleting it' % checks.__file__
        )

    def test_no_id_is_used_by_two_different_checks(self):
        shared = {
            check_id: sorted(functions)
            for check_id, functions in _ids_by_check(self.source).items()
            if len(functions) > 1
        }
        assert not shared, (
            'these check ids are used by more than one check, so neither can be '
            'silenced on its own: %r' % shared
        )
