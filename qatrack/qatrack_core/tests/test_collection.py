"""Guard against test files that pytest silently never collects.

A module whose name does not match ``python_files`` is not an error and not a
skip - pytest simply never looks at it, and the tests inside it stop running
without anyone noticing. That has happened twice in this codebase:
``qatrack/units/tests.py`` and ``qatrack/faults/tests/tests.py``, the latter
holding 76 tests across 16 classes that had never run at all.

Both were found by accident. This test looks for the same thing on purpose, so
the next one fails immediately and loudly instead.
"""

import ast
import fnmatch
import pathlib

QATRACK = pathlib.Path(__file__).resolve().parents[2]
REPO_ROOT = QATRACK.parent


def _looks_like_a_test_case(node):
    """True for a class that pytest/unittest would run tests from."""
    base_names = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            base_names.add(base.id)
        elif isinstance(base, ast.Attribute):
            base_names.add(base.attr)

    plausible = node.name.startswith('Test') or any(b.endswith('TestCase') for b in base_names)
    if not plausible:
        return False

    # A base class with no test methods of its own is not a missed test - the
    # Selenium harness classes are exactly this.
    return any(
        isinstance(item, ast.FunctionDef) and item.name.startswith('test_')
        for item in node.body
    )


def _defines_tests(path):
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return False

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            return True
        if isinstance(node, ast.ClassDef) and _looks_like_a_test_case(node):
            return True
    return False


def test_no_test_module_is_silently_uncollected(pytestconfig):
    """Every module that defines tests must match ``python_files``."""

    patterns = list(pytestconfig.getini('python_files'))
    assert patterns, "python_files is empty - collection would match nothing"

    missed = []
    for path in sorted(QATRACK.rglob('*.py')):
        # Only consider files that live where tests live. Application modules
        # are full of functions like test_list_* - this codebase's domain is
        # literally test lists - and none of those are pytest tests.
        relative = path.relative_to(REPO_ROOT)
        if 'tests' not in relative.parts and path.name != 'tests.py':
            continue

        if not _defines_tests(path):
            continue

        if not any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns):
            missed.append(str(relative))

    assert not missed, (
        "These modules define tests that pytest will never collect, because "
        "their filenames match none of python_files=%r:\n\n%s\n\n"
        "Rename them to match (test_<something>.py is the usual choice), or "
        "widen python_files in pyproject.toml if the name is deliberate."
        % (patterns, '\n'.join('  - ' + m for m in missed))
    )
