"""The committed .mo files must match the .po files they were compiled from.

This guards the repository rather than a deployment. `qatrack.W010` warns a
deployer who edits a .po without recompiling; these tests fail CI when a
*contributor* commits the two out of step, which is how
qatrack/locale/es/LC_MESSAGES/django.mo came to carry 150 translations its
source had never held - among them strings from an unrelated site's catalogue
and 150 with an unsubstituted `__Format_0__` placeholder, shown verbatim to
Spanish users for a year.
"""
import re
from pathlib import Path

from django.test import SimpleTestCase

from qatrack.qatrack_core.translation_catalogues import (
    _unescape,
    catalogue_problems,
    configured_language_coverage,
    locale_root,
    mo_translations,
    po_entries,
    po_translations,
)

#: The signature of the machine-translation pass that produced the Spanish
#: catalogue: each format specifier was masked before translation and never
#: put back. The pipeline was inconsistent about case and spacing.
MASKED_SPECIFIER = re.compile(r"__\s*format(?:_\d+)?\s*__", re.IGNORECASE)


class TestCatalogueIsCompiledFromItsSource(SimpleTestCase):

    def test_every_po_has_a_matching_mo(self):
        problems = catalogue_problems()
        assert problems == [], "\n".join(problems)

    def test_there_is_a_catalogue_to_check(self):
        """A vacuous pass is worse than a failure here."""
        pairs = sorted(locale_root().glob("*/LC_MESSAGES/*.po"))
        # >= 1, not >= 6: six is how many locales this repository happens to
        # ship, and encoding that here makes removing one a test failure. The
        # point is that the scan found something to check.
        assert len(pairs) >= 1, [str(p) for p in pairs]


class TestNoMaskedFormatSpecifiers(SimpleTestCase):
    """No translation may ship a placeholder token in place of a specifier.

    `msgfmt --check-format` catches most of these, and `compilemessages` runs
    it - but only where the entry carries a python-format flag. Three strings
    on the home page used Django's own `{{ VAR }}` syntax inside a `{% trans %}`
    literal, carried no flag, and so shipped `__format_0__}` straight to the
    interface without msgfmt objecting.
    """

    def test_no_po_translation_contains_a_masked_specifier(self):
        offenders = []
        for po in sorted(locale_root().glob("*/LC_MESSAGES/*.po")):
            text = po.read_text(encoding="utf-8")
            for block in text.split("\n\n"):
                if block.lstrip().startswith("#~") or "#~ msgid" in block:
                    continue                      # obsolete; never compiled
                flags = " ".join(l for l in block.split("\n") if l.startswith("#,"))
                if "fuzzy" in flags:
                    continue                      # excluded from the .mo
                msgstr = "\n".join(l for l in block.split("\n") if not l.startswith(("#", "msgid")))
                if MASKED_SPECIFIER.search(msgstr):
                    offenders.append("%s/%s: %s" % (po.parent.parent.name, po.name, msgstr.strip()[:90]))
        assert offenders == [], "\n".join(offenders)

    def test_no_compiled_translation_contains_a_masked_specifier(self):
        offenders = []
        for mo in sorted(locale_root().glob("*/LC_MESSAGES/*.mo")):
            import gettext
            with open(mo, "rb") as handle:
                catalogue = gettext.GNUTranslations(handle)
            for value in catalogue._catalog.values():
                for text in ([value] if isinstance(value, str) else list(value)):
                    if text and MASKED_SPECIFIER.search(text):
                        offenders.append("%s/%s: %r" % (mo.parent.parent.name, mo.name, text[:80]))
        assert offenders == [], "\n".join(offenders)


class TestComparisonLogic(SimpleTestCase):
    """The comparison itself, so a silent false pass is not possible."""

    def test_fuzzy_entries_are_not_expected_in_the_mo(self):
        import tempfile
        from pathlib import Path

        po = Path(tempfile.mkdtemp()) / "django.po"
        po.write_text(
            'msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
            'msgid "solid"\nmsgstr "sólido"\n\n'
            '#, fuzzy\nmsgid "shaky"\nmsgstr "inestable"\n\n'
            '#~ msgid "gone"\n#~ msgstr "ido"\n',
            encoding="utf-8",
        )
        assert po_translations(po) == {"solid": "sólido"}

    def test_untranslated_entries_are_not_expected_in_the_mo(self):
        import tempfile
        from pathlib import Path

        po = Path(tempfile.mkdtemp()) / "django.po"
        po.write_text('msgid "done"\nmsgstr "hecho"\n\nmsgid "todo"\nmsgstr ""\n', encoding="utf-8")
        assert po_translations(po) == {"done": "hecho"}

    def test_mo_msgids_reads_a_real_catalogue(self):
        fr = locale_root() / "fr" / "LC_MESSAGES" / "django.mo"
        assert len(mo_translations(fr)) > 1000


class TestNoUninterpolatedVariablesInTransTags(SimpleTestCase):
    """`{% trans %}` does not interpolate - `{% blocktrans %}` does.

    Three tooltips on the home page read
    `{% trans "There are currently {{ SE_NEEDING_REVIEW_COUNT }} ..." %}`. Django
    treats the whole thing as one literal msgid, so the page rendered the raw
    variable name to the user - in **every** language, English included, and the
    msgid could never match a real count either.

    Asserted across the templates rather than on those three, so the next one is
    caught when it is written.
    """

    #: The `qatrack` package, not the repository root. parents[3] was the
    #: repository, so the scan walked docs/, build/ and any vendored HTML
    #: outside .venv - slow, and liable to fail on third-party markup that
    #: legitimately contains a brace inside a trans tag.
    TEMPLATE_ROOT = Path(__file__).resolve().parents[2]

    def test_no_trans_tag_contains_a_template_variable(self):
        offenders = []
        scanned = 0
        for template in sorted(self.TEMPLATE_ROOT.rglob("*.html")):
            if ".venv" in template.parts or "node_modules" in template.parts:
                continue
            try:
                text = template.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            scanned += 1
            for match in re.finditer(r"\{%\s*trans\s+(\"[^\"]*\"|'[^']*')", text):
                if "{{" in match.group(1):
                    rel = template.relative_to(self.TEMPLATE_ROOT)
                    offenders.append("%s: %s" % (rel, match.group(0)[:70]))

        # Guards the narrowing direction only: if TEMPLATE_ROOT is pointed
        # somewhere with few or no templates the test would otherwise pass
        # vacuously. It cannot catch the root being too *wide* - that scans more,
        # not less - which is why the root is pinned to the package above rather
        # than relied on here.
        assert scanned > 100, "only %d template(s) scanned - is TEMPLATE_ROOT right?" % scanned

        assert offenders == [], (
            "%d {%% trans %%} tag(s) contain a template variable, which is never "
            "interpolated. Use {%% blocktrans %%}:\n\n%s"
            % (len(offenders), "\n".join("  " + o for o in offenders))
        )


class TestAStaleTranslationIsCaught(SimpleTestCase):
    """
    The case comparing msgid *sets* could never see: a translator improves a
    `msgstr` and leaves the `msgid` alone, which is the normal workflow. Both
    files still list the same strings, and Django serves the old wording.
    """

    def _pair(self, po_text, mo_pairs):
        import struct
        import tempfile
        from pathlib import Path

        root = Path(tempfile.mkdtemp()) / "xx" / "LC_MESSAGES"
        root.mkdir(parents=True)
        (root / "django.po").write_text(po_text, encoding="utf-8")

        # A minimal .mo, so the test does not need msgfmt on PATH.
        items = sorted((k.encode(), v.encode()) for k, v in mo_pairs)
        offsets, ids, strs = [], b"", b""
        for k, v in items:
            offsets.append((len(ids), len(k), len(strs), len(v)))
            ids += k + b"\0"
            strs += v + b"\0"
        n = len(items)
        keystart = 7 * 4 + 16 * n
        valstart = keystart + len(ids)
        koffsets, voffsets = [], []
        for o1, l1, o2, l2 in offsets:
            koffsets += [l1, o1 + keystart]
            voffsets += [l2, o2 + valstart]
        output = struct.pack("Iiiiiii", 0x950412de, 0, n, 7 * 4, 7 * 4 + n * 8, 0, 0)
        output += struct.pack("i" * len(koffsets), *koffsets)
        output += struct.pack("i" * len(voffsets), *voffsets)
        output += ids + strs
        (root / "django.mo").write_bytes(output)
        return root.parent.parent

    def test_a_changed_msgstr_is_reported(self):
        root = self._pair(
            'msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
            'msgid "colour"\nmsgstr "couleur vive"\n',
            [("", "Content-Type: text/plain; charset=UTF-8\n"), ("colour", "couleur")],
        )
        problems = catalogue_problems(root)
        assert problems, "a .mo compiled from an older .po went unreported"
        assert "differ in wording" in problems[0], problems[0]

    def test_matching_translations_are_quiet(self):
        root = self._pair(
            'msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
            'msgid "colour"\nmsgstr "couleur"\n',
            [("", "Content-Type: text/plain; charset=UTF-8\n"), ("colour", "couleur")],
        )
        assert catalogue_problems(root) == []


class TestConfiguredLanguageCoverage(SimpleTestCase):

    def test_it_reports_every_configured_language(self):
        from django.conf import settings

        codes = {row[0] for row in configured_language_coverage()}
        assert codes == {code for code, _ in settings.LANGUAGES}

    def test_fuzzy_counts_as_untranslated(self):
        """
        Because msgfmt does not compile fuzzy entries. A catalogue that counted
        them would report itself complete while serving English.
        """

        import tempfile
        from pathlib import Path

        po = Path(tempfile.mkdtemp()) / "django.po"
        po.write_text(
            'msgid "a"\nmsgstr "A"\n\n'
            '#, fuzzy\nmsgid "b"\nmsgstr "B"\n\n'
            'msgid "c"\nmsgstr ""\n',
            encoding="utf-8",
        )
        entries = po_entries(po)
        assert len(entries) == 3
        shipping = sum(1 for _, msgstr, fuzzy, _ in entries if msgstr and not fuzzy)
        assert shipping == 1

    def test_the_spanish_figure_matches_the_compiled_catalogue(self):
        """The count is only meaningful if it equals what the .mo really holds."""

        rows = {row[0]: row for row in configured_language_coverage()}
        if "es" not in rows:
            self.skipTest("Spanish is not configured")
        _, _, translated, total, _ = rows["es"]
        compiled = mo_translations(locale_root() / "es" / "LC_MESSAGES" / "django.mo")
        # the .mo carries a header entry with an empty msgid
        assert abs(len(compiled) - translated) <= 1, (len(compiled), translated)
        assert translated < total, "Spanish is expected to be partial"


class TestCatalogueTextIsDataNotCode(SimpleTestCase):
    """
    This parser runs during system checks, which run before `migrate`, over a
    file translators edit. It used to decode escapes with `eval` and an emptied
    `__builtins__`, which is not the same as data-only: concatenation and
    repetition still execute, so an entry could allocate arbitrarily much and
    hang the command without calling anything.
    """

    def test_ordinary_escapes_still_decode(self):
        assert _unescape(r"a\nb") == "a\nb"
        assert _unescape(r"quote \" here") == 'quote " here'
        assert _unescape("plain") == "plain"

    def test_an_expression_is_not_evaluated(self):
        # Under the old eval this built a 100-million-character string; under
        # literal_eval it is not valid and comes back untouched.
        payload = '" + "a" * 100000000 + "'
        out = _unescape(payload)
        assert out == payload, "catalogue text was evaluated as an expression"
        assert len(out) < 200
