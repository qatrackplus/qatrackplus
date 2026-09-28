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
import gettext
import re
from pathlib import Path

from django.conf import settings

#: A .po entry is only compiled into the .mo when it has a translation and is
#: not marked fuzzy. Obsolete entries (`#~`) are ignored by msgfmt entirely.
_QUOTED = re.compile(r'"(.*)"\s*$')


def _unescape(raw):
    try:
        return eval('"%s"' % raw, {"__builtins__": {}}, {})  # noqa: S307
    except SyntaxError:
        return raw


def po_translated_msgids(path):
    """The msgids a .po file expects to appear in its compiled .mo."""
    ids = set()
    msgid, msgstr, mode, fuzzy, pending_fuzzy = [], [], None, False, False

    def flush():
        key = "".join(msgid)
        if key and "".join(msgstr) and not fuzzy:
            ids.add(key)

    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("#~"):
            mode = None                      # obsolete entry, not compiled
        elif line.startswith("#,"):
            pending_fuzzy = "fuzzy" in line
        elif line.startswith("#"):
            continue
        elif line.startswith("msgid_plural"):
            mode = "plural"                  # shares the msgid already collected
        elif line.startswith("msgid"):
            flush()
            msgid, msgstr = [_unescape(_QUOTED.search(line).group(1))], []
            mode, fuzzy, pending_fuzzy = "msgid", pending_fuzzy, False
        elif line.startswith("msgstr"):
            mode = "msgstr"
            m = _QUOTED.search(line)
            if m:
                msgstr.append(_unescape(m.group(1)))
        elif line.startswith('"'):
            text = _unescape(_QUOTED.search(line).group(1))
            if mode == "msgid":
                msgid.append(text)
            elif mode == "msgstr":
                msgstr.append(text)
        elif not line:
            flush()
            msgid, msgstr, mode, fuzzy = [], [], None, False
    flush()
    return ids


def mo_msgids(path):
    """The msgids actually present in a compiled catalogue."""
    with open(path, "rb") as handle:
        catalogue = gettext.GNUTranslations(handle)
    ids = set()
    for key in catalogue._catalog:
        key = key[0] if isinstance(key, tuple) else key
        if key:
            ids.add(key)
    return ids


def locale_root():
    paths = getattr(settings, "LOCALE_PATHS", None) or []
    return Path(paths[0]) if paths else Path(settings.PROJECT_ROOT) / "locale"


def catalogue_problems(root=None):
    """Return one message per catalogue whose .mo does not match its .po.

    An empty list means every tracked .po has a .mo compiled from that exact
    source.
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
            compiled = mo_msgids(mo)
        except Exception as exc:                       # noqa: BLE001 - reported, not raised
            problems.append("%s: its .mo could not be read (%s)." % (name, exc))
            continue

        expected = po_translated_msgids(po)
        missing = expected - compiled
        extra = compiled - expected

        if missing or extra:
            detail = []
            if missing:
                detail.append("%d translation(s) in the .po are absent from the .mo" % len(missing))
            if extra:
                detail.append("%d in the .mo are not in the .po" % len(extra))
            problems.append(
                "%s is out of step with its source: %s. Run "
                "`python manage.py compilemessages`." % (name, "; ".join(detail))
            )

    return problems
