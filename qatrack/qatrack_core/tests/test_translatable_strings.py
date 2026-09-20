"""Catch user-facing strings that were never marked for translation.

QATrack+ ships in English, French, French Canadian and Spanish, and has
roughly two thousand marked strings in Python and fifteen hundred in
templates. A string that misses its `_()` does not fail anywhere - it simply
stays English for every other locale, and nobody finds out until a French site
reads it.

This does not try to fix the ones already here. It records them, and fails on
the next one, so the number can only go down.
"""

import ast
import pathlib

QATRACK = pathlib.Path(__file__).resolve().parents[2]
REPO_ROOT = QATRACK.parent

TRANSLATORS = {
    '_', '_l', 'gettext', 'gettext_lazy', 'ugettext', 'ugettext_lazy',
    'pgettext', 'pgettext_lazy', 'ngettext', 'ngettext_lazy', 'npgettext',
}

# Keyword arguments whose value is rendered to a user.
USER_FACING_KWARGS = {
    'verbose_name', 'verbose_name_plural', 'help_text', 'label', 'empty_label',
}

# Calls whose positional string argument is rendered to a user.
USER_FACING_CALLS = {
    'ValidationError',
    # django.contrib.messages
    'success', 'error', 'info', 'warning', 'debug', 'add_message',
}

# Strings that are deliberately not translated. Add to this only with a reason.
#
# 'ID' is the verbose_name Django generates for an automatic primary key.
# There are 57 of them, and every locale this project ships already renders it
# unchanged - `msgid "ID"` has `msgstr "ID"` in fr, fr_CA and es. Including
# them would bury three dozen real findings under identity translations.
IGNORED_VALUES = {'ID'}


def _is_translated(node):
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in TRANSLATORS
    if isinstance(func, ast.Attribute):
        return func.attr in TRANSLATORS
    return False


def _literal_string(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = node.value.strip()
        if text and text not in IGNORED_VALUES:
            return text
    return None


def find_untranslated():
    """Every user-facing literal that is not wrapped in a translation call.

    Keyed by (path, kind, text) rather than by line, so that moving code around
    does not look like a new finding.
    """
    found = set()

    for path in sorted(QATRACK.rglob('*.py')):
        relative = path.relative_to(REPO_ROOT)
        parts = relative.parts
        # Migrations carry a frozen copy of old field definitions; tests are
        # not user facing.
        if 'migrations' in parts or 'tests' in parts:
            continue

        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            for keyword in node.keywords:
                if keyword.arg in USER_FACING_KWARGS and not _is_translated(keyword.value):
                    text = _literal_string(keyword.value)
                    if text:
                        found.add((str(relative), keyword.arg, text))

            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
            if name in USER_FACING_CALLS:
                for argument in node.args:
                    if not _is_translated(argument):
                        text = _literal_string(argument)
                        if text:
                            found.add((str(relative), name, text))

    return found


BASELINE_PATH = pathlib.Path(__file__).with_name('untranslated_baseline.json')


def _load_baseline():
    import json
    return {tuple(row) for row in json.loads(BASELINE_PATH.read_text(encoding='utf-8'))}


def test_no_new_untranslated_user_facing_strings():
    """A ratchet, not a cleanup.

    The strings already recorded in untranslated_baseline.json are a debt to
    pay down when someone is in the area. What this stops is the debt growing:
    a new verbose_name, help_text, label, ValidationError or flash message that
    nobody can translate.

    To fix a finding, wrap it:

        from django.utils.translation import gettext_lazy as _l
        help_text=_l("Current status of this issue")

    and delete its line from the baseline. The baseline should only ever
    shrink.
    """
    baseline = _load_baseline()
    current = find_untranslated()

    new = sorted(current - baseline)
    assert not new, (
        "%d user-facing string(s) are not marked for translation:\n\n%s\n\n"
        "Wrap them with gettext_lazy (imported as _l in this codebase). If a "
        "string genuinely should not be translated - a code, a unit symbol - "
        "add it to IGNORED_VALUES with a note saying why."
        % (len(new), '\n'.join('  %s\n    %s=%r' % (p, k, t) for p, k, t in new))
    )


def test_baseline_has_no_stale_entries():
    """A fixed string must be removed from the baseline, or it protects nothing.

    Without this, the file accumulates entries for code that no longer exists
    and stops describing anything real.
    """
    baseline = _load_baseline()
    current = find_untranslated()

    stale = sorted(baseline - current)
    assert not stale, (
        "%d baseline entr(ies) no longer match anything - the string was "
        "translated, moved or deleted. Remove them from %s:\n\n%s"
        % (len(stale), BASELINE_PATH.name,
           '\n'.join('  %s\n    %s=%r' % (p, k, t) for p, k, t in stale))
    )
