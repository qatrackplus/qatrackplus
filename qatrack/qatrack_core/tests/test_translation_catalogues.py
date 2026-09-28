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
    catalogue_problems,
    locale_root,
    mo_msgids,
    po_translated_msgids,
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
        assert len(pairs) >= 6, [str(p) for p in pairs]


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
        assert po_translated_msgids(po) == {"solid"}

    def test_untranslated_entries_are_not_expected_in_the_mo(self):
        import tempfile
        from pathlib import Path

        po = Path(tempfile.mkdtemp()) / "django.po"
        po.write_text('msgid "done"\nmsgstr "hecho"\n\nmsgid "todo"\nmsgstr ""\n', encoding="utf-8")
        assert po_translated_msgids(po) == {"done"}

    def test_mo_msgids_reads_a_real_catalogue(self):
        fr = locale_root() / "fr" / "LC_MESSAGES" / "django.mo"
        assert len(mo_msgids(fr)) > 1000


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

    TEMPLATE_ROOT = Path(__file__).resolve().parents[3]

    def test_no_trans_tag_contains_a_template_variable(self):
        offenders = []
        for template in sorted(self.TEMPLATE_ROOT.rglob("*.html")):
            if ".venv" in template.parts or "node_modules" in template.parts:
                continue
            try:
                text = template.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for match in re.finditer(r"\{%\s*trans\s+(\"[^\"]*\"|'[^']*')", text):
                if "{{" in match.group(1):
                    rel = template.relative_to(self.TEMPLATE_ROOT)
                    offenders.append("%s: %s" % (rel, match.group(0)[:70]))

        assert offenders == [], (
            "%d {%% trans %%} tag(s) contain a template variable, which is never "
            "interpolated. Use {%% blocktrans %%}:\n\n%s"
            % (len(offenders), "\n".join("  " + o for o in offenders))
        )
