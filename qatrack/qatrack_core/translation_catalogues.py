"""Compare each translation source (.po) with the catalogue compiled from it (.mo).

Django reads the .mo at runtime and never looks at the .po, so the two
drifting apart is silent: the file a translator edits stops being the file
users see. This repository tracks both, which is what allowed
qatrack/locale/es/LC_MESSAGES/django.mo to spend a year carrying 150
translations that its .po had never contained - including strings from
another site's catalogue, and 150 with an unsubstituted `__Format_0__`
placeholder that Spanish users saw verbatim.

`compilemessages` is documented as an install step for Linux and Windows but
is not run by the Docker entrypoint, so containerised deployments get exactly
what is committed here. Until that is settled one way or the other, the
committed .mo has to be trusted, which means it has to be checked.

The comparison is deliberately pure Python: it reads the .mo with the
standard library rather than shelling out to msgfmt, because the platform
that most needs the check - the Docker image - has no gettext installed.
"""
import ast
import gettext
import re
import struct
from pathlib import Path

from django.conf import settings

#: A .po entry is only compiled into the .mo when it has a translation and is
#: not marked fuzzy. Obsolete entries (`#~`) are ignored by msgfmt entirely.
_QUOTED = re.compile(r'"(.*)"\s*$')


def _unescape(raw):
    """Decode a .po string literal's escapes.

    `ast.literal_eval` rather than `eval`: stripping `__builtins__` does not make
    `eval` data-only - concatenation and repetition still execute, so a malformed
    or hostile catalogue entry could hang a management command. This runs during
    system checks, which run before `migrate`, so that is not a hypothetical
    place to be evaluating text from a file.
    """

    try:
        return ast.literal_eval('"%s"' % raw)
    except (SyntaxError, ValueError):
        return raw


def po_entries(path):
    """Every non-obsolete entry in a .po, as (msgid, msgstr, fuzzy, plural).

    One parser, because deriving "how many entries are there" from a second,
    simpler one got it wrong: a msgid wrapped across lines opens with `msgid ""`,
    so counting lines that start with `msgid` and carry text skips exactly the
    long strings, and the totals came out under the number translated.
    """

    entries = []
    msgid, msgstr, msgctxt, mode, fuzzy, pending_fuzzy, plural = [], [], [], None, False, False, False

    def flush():
        key = "".join(msgid)
        if not key:
            return
        context = "".join(msgctxt)
        if context:
            # How gettext keys a context-qualified entry, and therefore how it
            # appears in the .mo: context, US (0x04), msgid. Without this a
            # `msgctxt` entry would be compared as its bare msgid and report as
            # both missing from the .mo and extra in it.
            key = "%s\x04%s" % (context, key)
        entries.append((key, "".join(msgstr), fuzzy, plural))

    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("#~"):
            mode = None                      # obsolete entry, not compiled
        elif line.startswith("#,"):
            pending_fuzzy = "fuzzy" in line
        elif line.startswith("#"):
            continue
        elif line.startswith("msgctxt"):
            flush()
            msgid, msgstr, msgctxt = [], [], [_unescape(_QUOTED.search(line).group(1))]
            mode, fuzzy, pending_fuzzy, plural = "msgctxt", pending_fuzzy, False, False
        elif line.startswith("msgid_plural"):
            mode, plural = "plural", True    # shares the msgid already collected
        elif line.startswith("msgid"):
            if not msgctxt:
                flush()
            msgid, msgstr = [_unescape(_QUOTED.search(line).group(1))], []
            mode, fuzzy, pending_fuzzy, plural = "msgid", (pending_fuzzy or fuzzy), False, False
        elif line.startswith("msgstr"):
            mode = "msgstr"
            m = _QUOTED.search(line)
            if m:
                msgstr.append(_unescape(m.group(1)))
        elif line.startswith('"'):
            text = _unescape(_QUOTED.search(line).group(1))
            if mode == "msgid":
                msgid.append(text)
            elif mode == "msgctxt":
                msgctxt.append(text)
            elif mode == "msgstr":
                msgstr.append(text)
        elif not line:
            flush()
            msgid, msgstr, msgctxt, mode, fuzzy, plural = [], [], [], None, False, False
    flush()
    return entries


def po_translations(path):
    """What a .po expects its .mo to contain, as {msgid: msgstr}.

    Only entries that will actually be compiled: a translation is present and the
    entry is not fuzzy. Plural entries map to `None`, because their .mo
    representation is indexed by plural form and comparing those to a single
    string would be wrong - for them only presence is checked.
    """

    return {
        msgid: (None if plural else msgstr)
        for msgid, msgstr, fuzzy, plural in po_entries(path)
        if msgstr and not fuzzy
    }


def mo_translations(path):
    """What a compiled catalogue actually contains, as {msgid: msgstr}.

    Plural entries are keyed `(msgid, index)` by gettext; they map to `None` here
    for the same reason as in `po_translations`.
    """

    with open(path, "rb") as handle:
        catalogue = gettext.GNUTranslations(handle)
    ids = {}
    for key, value in catalogue._catalog.items():
        if isinstance(key, tuple):
            key = key[0]
            value = None
        if key:
            ids.setdefault(key, value)
    return ids


def locale_root():
    paths = getattr(settings, "LOCALE_PATHS", None) or []
    return Path(paths[0]) if paths else Path(settings.PROJECT_ROOT) / "locale"


def catalogue_problems(root=None):
    """Return one message per catalogue whose .mo does not match its .po.

    An empty list means every tracked .po has a .mo compiled from that exact
    source, with the same translations - not merely the same msgids. Comparing
    only msgids would miss the commonest edit of all: a translator improving a
    `msgstr` and leaving the `msgid` alone. Both files would still list the same
    strings while Django served the old wording.
    """
    root = Path(root) if root else locale_root()
    problems = []

    for po in sorted(root.glob("*/LC_MESSAGES/*.po")):
        mo = po.with_suffix(".mo")
        name = "%s/%s" % (po.parent.parent.name, po.name)

        if not mo.exists():
            problems.append(
                "%s has no compiled .mo, so none of its translations apply." % name
            )
            continue

        try:
            compiled = mo_translations(mo)
        except (OSError, struct.error, UnicodeDecodeError, ValueError) as exc:
            # Narrow deliberately: these are what an unreadable or truncated .mo
            # raises (gettext unpacks it with `struct`). Catching everything here
            # would turn a bug in this module into a polite "could not be read"
            # and hide it. The broad catch belongs at the boundary, in
            # `checks.check_translation_catalogues`, whose job is to make sure a
            # diagnostic can never block `migrate`.
            problems.append("%s: its .mo could not be read (%s)." % (name, exc))
            continue

        expected = po_translations(po)
        missing = set(expected) - set(compiled)
        extra = set(compiled) - set(expected)
        stale = [
            key for key in set(expected) & set(compiled)
            if expected[key] is not None and compiled[key] is not None
            and expected[key] != compiled[key]
        ]

        if missing or extra or stale:
            detail = []
            if missing:
                detail.append("%d translation(s) in the .po are absent from the .mo" % len(missing))
            if extra:
                detail.append("%d in the .mo are not in the .po" % len(extra))
            if stale:
                detail.append(
                    "%d differ in wording, so the .mo was compiled from an older .po"
                    % len(stale)
                )
            problems.append(
                "%s is out of step with its source: %s. Run "
                "`python manage.py compilemessages`." % (name, "; ".join(detail))
            )

    return problems


def configured_language_coverage(root=None):
    """How much of each configured language actually reaches users.

    Reports against `settings.LANGUAGES` rather than against whatever catalogues
    happen to be on disk: a language offered in the picker with nothing behind it
    is the failure worth naming, and a catalogue for a language nobody can select
    is not.

    A string only reaches users when its entry has a translation *and* is not
    fuzzy. A .po can look complete while serving barely half of itself - fuzzy
    entries are matches gettext guessed and `msgfmt` deliberately excludes, so
    they count as missing here.

    Yields (code, name, translated, total, has_catalogue) per configured language.
    """

    from django.utils.translation import to_locale

    root = Path(root) if root else locale_root()
    rows = []

    for code, name in getattr(settings, "LANGUAGES", []):
        po = root / to_locale(code) / "LC_MESSAGES" / "django.po"
        if not po.exists():
            rows.append((code, str(name), 0, 0, False))
            continue

        entries = po_entries(po)
        translated = sum(1 for _, msgstr, fuzzy, _ in entries if msgstr and not fuzzy)
        rows.append((code, str(name), translated, len(entries), True))

    return rows
