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
import textwrap

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

# `messages.warning(request, "...")` is user facing. `logger.warning("...")` is
# not: a log line is read by an administrator in the server's log, and
# translating it would make it unsearchable and locale-dependent. The names above
# are matched on the method alone, so without this the scanner demands that every
# logging call in the project be translated.
LOGGING_RECEIVERS = {'logger', 'log', 'logging', 'LOGGER', '_logger'}

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


def _receiver(func):
    """What a method is called on: 'logger' in `logger.warning(...)`.

    Handles `self.logger.warning(...)` too, by taking the last attribute name.
    """
    value = getattr(func, 'value', None)
    if isinstance(value, ast.Name):
        return value.id
    if isinstance(value, ast.Attribute):
        return value.attr
    return ''


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
        # as_posix(), not str(): the baseline is a checked-in file read on
        # every platform, and str() would write it with backslashes on
        # Windows. Every entry would then miss, the remaining debt would read
        # as new findings, and the suite would be red on Windows only.
        key = relative.as_posix()
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
                        found.add((key, keyword.arg, text))

            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
            if name in USER_FACING_CALLS and _receiver(node.func) not in LOGGING_RECEIVERS:
                for argument in node.args:
                    if not _is_translated(argument):
                        text = _literal_string(argument)
                        if text:
                            found.add((key, name, text))

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


def test_baseline_paths_are_posix():
    """The baseline is one file, read on every platform.

    ``find_untranslated`` keys on ``Path.as_posix()``, so an entry written
    with backslashes can never match - which is invisible on Linux and turns
    the whole remaining debt into "new findings" on Windows. Regenerating the
    baseline on a Windows checkout is the way that happens.
    """
    backslashed = sorted(path for path, _, _ in _load_baseline() if '\\' in path)
    assert not backslashed, (
        "%d baseline path(s) use backslashes. Rewrite them with forward "
        "slashes in %s:\n\n%s"
        % (len(backslashed), BASELINE_PATH.name, '\n'.join('  %s' % p for p in backslashed))
    )


def test_logging_calls_are_not_user_facing():
    """`logger.warning(...)` must not be demanded for translation.

    The names in ``USER_FACING_CALLS`` - warning, error, info, debug - exist for
    ``django.contrib.messages``, and were matched on the method name alone. That
    also matches every logging call in the project, so the scanner asked for log
    lines to be translated. A log line is read by an administrator in the
    server's log; translating it makes it locale-dependent and unsearchable.

    Asserted against parsed source rather than the tree, so it states the rule
    instead of depending on which calls happen to exist today.
    """
    source = textwrap.dedent(
        '''
        from django.contrib import messages
        logger = logging.getLogger(__name__)

        def f(request):
            logger.warning("a log line")
            logger.error("another %s", x)
            logging.info("a third")
            self.logger.debug("a fourth")
            messages.warning(request, "a message to a person")
        '''
    )
    tree = ast.parse(source)
    flagged = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
        if name in USER_FACING_CALLS and _receiver(node.func) not in LOGGING_RECEIVERS:
            for argument in node.args:
                text = _literal_string(argument)
                if text:
                    flagged.add(text)

    assert flagged == {"a message to a person"}, flagged
