"""
#837: in dark mode the schedule rule was white on white.

django-recurrence 1.14's `recurrence.css` ends with a `prefers-color-scheme:
dark` rule setting `div.recurrence-widget a.recurrence-label` to white.
`reports.css` styles the same selector, so the two have equal specificity, and
`reports.html` loads `recurrence.css` second - the later file wins. The schedule
modal's own background does not follow the colour preference (QATrack+ ships no
`prefers-color-scheme` rules of its own), so the text vanished against it and
the Schedule box looked empty apart from its close button.

These tests pin the *mechanism* rather than a rendered colour, for two reasons:

- the fix works by specificity, not by order, and a test that asserted the
  `<link>` order would pass for a fix that does not actually work and fail for
  one that does;
- the real regression risk is a django-recurrence upgrade that renames the
  selector, at which point the override silently stops applying to anything.
  `test_recurrence_still_ships_the_dark_rule` is what catches that.

The fix is an opt-out from dark mode rather than a restyle, which is possible
only in this direction: `color-scheme: light` would not help, since
`prefers-color-scheme` reports the user's setting whatever the page declares.
recurrence.css's rule above is the only dark-mode rule the page has, so
overruling it *is* the opt-out.

They parse the stylesheets with tinycss2, which arrives with WeasyPrint.
"""

import os
import re

import recurrence
import tinycss2
from django.conf import settings

LABEL_SELECTOR_TAIL = "div.recurrence-widget a.recurrence-label"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def stylesheets_loaded_by_reports_page():
    """The project stylesheets `reports.html` links, resolved to files on disk.

    Vendored files under STATIC_ROOT are skipped: they are collectstatic output
    and not ours to police.
    """

    template = os.path.join(settings.PROJECT_ROOT, "reports", "templates", "reports", "reports.html")
    hrefs = re.findall(r'{%\s*static\s+"([^"]+\.css)"', read(template))

    found = []
    for href in hrefs:
        app = href.split("/", 1)[0]
        candidate = os.path.join(settings.PROJECT_ROOT, app, "static", href)
        if os.path.exists(candidate):
            found.append(candidate)
    return found


def repo_path(path):
    """Project-relative, with forward slashes on every platform.

    `os.path.relpath` gives backslashes on Windows, so comparing its output to a
    literal is a POSIX-only test - which is how the first revision of this file
    failed CI on Windows while passing on Linux.
    """

    return os.path.relpath(path, settings.PROJECT_ROOT).replace(os.sep, "/")

RECURRENCE_CSS = os.path.join(
    os.path.dirname(recurrence.__file__), "static", "recurrence", "css", "recurrence.css",
)
REPORTS_CSS = os.path.join(
    settings.PROJECT_ROOT, "reports", "static", "reports", "css", "reports.css",
)


def specificity(selector):
    """(ids, classes, elements) for the simple selectors used in these files."""
    ids = selector.count("#")
    classes = selector.count(".")
    elements = len([
        part for part in selector.replace(">", " ").split()
        if part and not part.startswith(("#", "."))
    ])
    return (ids, classes, elements)


def dark_mode_label_rules(path):
    """Every `a.recurrence-label` rule inside a prefers-color-scheme: dark block."""

    with open(path, encoding="utf-8") as f:
        sheet = tinycss2.parse_stylesheet(f.read(), skip_whitespace=True, skip_comments=True)

    found = []
    for rule in sheet:
        if rule.type != "at-rule" or rule.lower_at_keyword != "media":
            continue
        prelude = tinycss2.serialize(rule.prelude)
        if "prefers-color-scheme" not in prelude or "dark" not in prelude:
            continue
        for inner in tinycss2.parse_stylesheet(
            tinycss2.serialize(rule.content), skip_whitespace=True, skip_comments=True
        ):
            if inner.type != "qualified-rule":
                continue
            selector = " ".join(tinycss2.serialize(inner.prelude).split())
            if not selector.endswith(LABEL_SELECTOR_TAIL):
                continue
            body = " ".join(tinycss2.serialize(inner.content).split())
            found.append((selector, body))
    return found


class TestScheduleDialogLabelIsReadableInDarkMode:

    def test_recurrence_still_ships_the_dark_rule(self):
        """The premise. If this fails the override below may be dead weight."""

        rules = dark_mode_label_rules(RECURRENCE_CSS)
        assert rules, (
            "django-recurrence no longer has a dark-mode rule for %s. #837's fix in "
            "reports.css may now be unnecessary - check before removing it, since the "
            "selector may simply have been renamed." % LABEL_SELECTOR_TAIL
        )
        assert any("white" in body for _, body in rules), rules

    def test_reports_css_overrides_it_by_specificity(self):
        ours = dark_mode_label_rules(REPORTS_CSS)
        assert ours, "reports.css has no dark-mode rule for the schedule label (#837)"

        theirs = dark_mode_label_rules(RECURRENCE_CSS)

        for our_selector, our_body in ours:
            assert "black" in our_body or "#000" in our_body, our_body
            for their_selector, _ in theirs:
                assert specificity(our_selector) > specificity(their_selector), (
                    "%r does not outrank %r, so recurrence.css wins in dark mode "
                    "whenever it is loaded second - which reports.html does" % (
                        our_selector, their_selector,
                    )
                )

    def test_the_override_cannot_reach_the_admin(self):
        """
        Opting out of dark mode is scoped to the pages that load reports.css.
        Django's admin has its own dark theme, which works and is meant to, and
        the admin uses the same recurrence widget for notice schedules - so the
        containment here is "which templates load this file", not the selector.
        """

        ours = dark_mode_label_rules(REPORTS_CSS)
        # Without this the check below is vacuous when the rule is missing
        # entirely, which is exactly the state the fix removes.
        assert ours, "reports.css has no dark-mode rule for the schedule label (#837)"

        loaders = []
        for root, dirs, files in os.walk(settings.PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in ("node_modules", "__pycache__")]
            for name in files:
                if not name.endswith(".html"):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8", errors="replace") as f:
                    if "reports/css/reports.css" in f.read():
                        loaders.append(repo_path(path))

        assert sorted(loaders) == ["reports/templates/reports/reports.html"], sorted(loaders)

    def test_no_other_stylesheet_this_page_loads_reacts_to_the_preference(self):
        """
        Why the modal stays light: nothing the reports page loads reacts to the
        preference, so a dark-mode user gets the light page with one white label
        on it.

        Scoped to the stylesheets `reports.html` actually links. An earlier
        version walked every .css in the project, which coupled this reports test
        to unrelated files - adding a legitimate dark-mode rule to an admin
        stylesheet would have failed it while changing nothing about the schedule
        dialog.
        """

        offenders = []
        for path in stylesheets_loaded_by_reports_page():
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            if "prefers-color-scheme" in text and os.path.realpath(path) != os.path.realpath(REPORTS_CSS):
                offenders.append(repo_path(path))

        assert sorted(offenders) == [], sorted(offenders)

    def test_the_widgets_own_rules_are_not_disturbed(self):
        """
        This file was edited by replacing a span of text, and the first attempt
        deleted the `.remove` rule below the insertion point - half-em padding
        and normal weight that applied in *both* colour schemes, so the widget's
        remove controls changed for users who never had the dark-mode bug. The
        dark-mode tests above could not see it, because they only look at
        dark-mode rules.

        Anything that edits near the recurrence block should keep failing this
        until the rules it did not mean to touch are back.
        """

        text = read(REPORTS_CSS)
        for selector in (
            "div.recurrence-widget a.recurrence-label",
            "div.recurrence-widget .remove",
            "div.recurrence-widget .remove:link",
            "div.recurrence-widget .remove:visited",
            "div.recurrence-widget .checkbox",
            "div.recurrence-widget .control",
            "div.recurrence-widget .radio",
        ):
            assert selector in text, (
                "%s is gone from reports.css; an edit removed a rule it did not "
                "mean to" % selector
            )
