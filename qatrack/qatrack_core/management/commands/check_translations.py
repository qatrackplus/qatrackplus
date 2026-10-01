"""Report the state of the translation catalogues.

Deliberately a command rather than a system check. Coverage is *informational* -
a partially translated language is a normal, reasonable state, and the
untranslated strings fall back to English rather than breaking - so reporting it
through `manage.py check` would print "System check identified N issues" on every
run and every pre-commit, for a condition that can only be cleared by finishing a
translation. Catalogue *staleness* stays a system check (`qatrack.W010`), because
that one is silent when healthy and is a real defect when it is not.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from qatrack.qatrack_core.translation_catalogues import (
    catalogue_problems,
    configured_language_coverage,
    locale_root,
    po_entries,
)


class Command(BaseCommand):
    help = "Report untranslated strings per configured language, and any .mo that is out of date."

    def add_arguments(self, parser):
        parser.add_argument(
            "--missing",
            metavar="LANG",
            help="List the untranslated and fuzzy msgids for one language code, e.g. es.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=40,
            help="How many msgids to list with --missing (default 40; 0 for all).",
        )

    def handle(self, *args, **options):
        from django.utils.translation import to_locale

        source = getattr(settings, "LANGUAGE_CODE", "en")

        if options["missing"]:
            return self._list_missing(options["missing"], options["limit"], to_locale)

        self.stdout.write("Languages offered by LANGUAGES (source language: %s)\n" % source)
        rows = configured_language_coverage()
        problems = 0

        for code, name, translated, total, has_catalogue in rows:
            if code == source:
                self.stdout.write("  %-7s %-22s the language the strings are written in" % (code, name))
                continue

            if not has_catalogue:
                problems += 1
                self.stdout.write(self.style.WARNING(
                    "  %-7s %-22s NO CATALOGUE - every string is served in %s" % (code, name, source)
                ))
                continue

            missing = total - translated
            pct = 100.0 * translated / total if total else 0.0
            line = "  %-7s %-22s %5d / %-5d translated (%.0f%%)" % (code, name, translated, total, pct)
            if missing:
                line += "  -  %d fall back to %s" % (missing, source)
            self.stdout.write(line if not missing else self.style.NOTICE(line))

        self.stdout.write("\nCompiled catalogues (.mo) against their sources (.po)")
        stale = catalogue_problems()
        if stale:
            problems += len(stale)
            for problem in stale:
                self.stdout.write(self.style.ERROR("  " + problem))
        else:
            self.stdout.write("  every .po has a .mo compiled from that exact source")

        if problems:
            self.stdout.write("")
            raise SystemExit(1)

    def _list_missing(self, code, limit, to_locale):
        po = locale_root() / to_locale(code) / "LC_MESSAGES" / "django.po"
        if not po.exists():
            raise SystemExit("no catalogue for %s at %s" % (code, po))

        missing = [
            (msgid, "fuzzy" if fuzzy else "untranslated")
            for msgid, msgstr, fuzzy, _ in po_entries(po)
            if not msgstr or fuzzy
        ]
        self.stdout.write("%s: %d strings do not reach users\n" % (code, len(missing)))
        shown = missing if limit == 0 else missing[:limit]
        for msgid, why in shown:
            flat = msgid.replace("\n", " ")
            self.stdout.write("  [%-12s] %s" % (why, flat[:96]))
        if len(shown) < len(missing):
            self.stdout.write("  ... and %d more (--limit 0 for all)" % (len(missing) - len(shown)))
