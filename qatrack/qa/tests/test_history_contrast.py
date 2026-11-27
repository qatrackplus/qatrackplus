"""History labels must be readable on every pass/fail background.

Bootstrap's `.label` sets `color: #fff`, and every history label sits on one of
the five pass/fail backgrounds at the top of `qa.css`. White fails WCAG AA on
all five. `qa.css` overrides the colour for `.qa-history .label`, and these
tests compute the ratios from the stylesheet so that adding a sixth background,
or loosening the override, fails here rather than shipping.

**What went wrong, since it is three different things.** The override used to be
`th.qa-history .label`, covering only the header's date labels. `td.qa-history`
appears in `testlistinstance_detail.html`, `testlistinstance_review.html` and
`qavalue_form.html`, and in those cells numeric history values and the `N/A`
label have always rendered white on colour. String and date values were the one
case that had been patched - with `text-black` on the inner span in
`history.html` - and this branch removed that class while fixing an unclosed
`<span>` beside it. The other two predate that change and are fixed by the same
selector.

Parsed with tinycss2, which arrives with WeasyPrint - the same approach as
`qatrack/reports/tests/test_schedule_dialog_css.py`.
"""

import os

import tinycss2
from django.conf import settings

from qatrack.qa.models import PASS_FAIL_CHOICES

QA_CSS = os.path.join(settings.PROJECT_ROOT, "qa", "static", "qa", "css", "qa.css")
HISTORY_TEMPLATE = os.path.join(settings.PROJECT_ROOT, "qa", "templates", "qa", "history.html")

# Normal-size text. A history label is 11px (`.history-value`), so the 3:1
# large-text allowance does not apply.
AA_NORMAL_TEXT = 4.5

# history.html writes `{{hist.pass_fail}}` into the class list alongside
# `label`, so the set comes from the model and not from this file. Taking it
# from PASS_FAIL_CHOICES means a sixth state added to the model is measured here
# the moment it exists - which is the whole reason these tests read the
# stylesheet rather than asserting a list of ratios.
PASS_FAIL_CLASSES = [value for value, _display in PASS_FAIL_CHOICES]


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def declarations_for(selector, css):
    """Every declaration block whose selector matches `selector` exactly."""
    found = []
    for rule in tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True):
        if rule.type != "qualified-rule":
            continue
        prelude = tinycss2.serialize(rule.prelude).strip()
        if prelude == selector:
            body = {}
            for decl in tinycss2.parse_blocks_contents(rule.content, skip_whitespace=True):
                if decl.type == "declaration":
                    body[decl.lower_name] = tinycss2.serialize(decl.value).strip()
            found.append(body)
    return found


def colour_of(selector, prop, css):
    blocks = declarations_for(selector, css)
    assert blocks, "no rule for %s" % selector
    values = [b[prop] for b in blocks if prop in b]
    assert values, "%s sets no %s" % (selector, prop)
    return values[-1]


def relative_luminance(colour):
    """WCAG 2.x relative luminance of a #rgb or #rrggbb colour."""
    h = colour.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    assert len(h) == 6, colour
    channels = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def pass_fail_backgrounds():
    css = read(QA_CSS)
    return {name: colour_of(".%s" % name, "background-color", css) for name in PASS_FAIL_CLASSES}


class TestTheContrastMaths:
    """The helpers above, against figures that are not ours to get wrong."""

    def test_white_on_black_is_twenty_one_to_one(self):
        assert round(contrast("#ffffff", "#000000"), 2) == 21.0

    def test_a_colour_against_itself_is_one_to_one(self):
        assert round(contrast("#00c0ef", "#00c0ef"), 2) == 1.0

    def test_three_digit_and_six_digit_forms_agree(self):
        assert contrast("#fff", "#000") == contrast("#ffffff", "#000000")


class TestHistoryLabelContrast:

    def test_the_override_is_not_scoped_to_the_header(self):
        """`th.qa-history .label` left every value cell white on colour.

        Asserted as an absence too: restoring the `th` form would reintroduce
        exactly the gap, and the broader rule could sit below it unnoticed.
        """
        css = read(QA_CSS)

        assert declarations_for(".qa-history .label", css), (
            "no `.qa-history .label` rule - the value cells in "
            "testlistinstance_detail.html, testlistinstance_review.html and "
            "qavalue_form.html have no colour of their own"
        )
        assert not declarations_for("th.qa-history .label", css), (
            "the header-only form is back; it covers neither `td.qa-history` "
            "nor the three templates that use it"
        )

    def test_every_pass_fail_background_meets_aa_with_the_override(self):
        css = read(QA_CSS)
        foreground = colour_of(".qa-history .label", "color", css)

        failures = []
        for name, background in sorted(pass_fail_backgrounds().items()):
            ratio = contrast(foreground, background)
            if ratio < AA_NORMAL_TEXT:
                failures.append("%s (%s): %.2f:1" % (name, background, ratio))

        assert not failures, (
            "%s on these backgrounds is below AA's %s:1 - %s"
            % (foreground, AA_NORMAL_TEXT, "; ".join(failures))
        )

    def test_white_would_fail_on_every_one_of_them(self):
        """The control: without the override there is a real problem, not a theory.

        If this ever passes, Bootstrap's `.label` colour or the pass/fail
        palette has changed enough that the override may no longer be needed -
        which is worth knowing rather than assuming.
        """
        would_pass = {
            name: round(contrast("#ffffff", background), 2)
            for name, background in pass_fail_backgrounds().items()
            if contrast("#ffffff", background) >= AA_NORMAL_TEXT
        }
        assert not would_pass, (
            "white now meets AA on %s, so the premise of the override has changed" % would_pass
        )

    def test_the_template_does_not_rely_on_text_black(self):
        """The utility class this replaces, and why it is not the fix.

        `.text-black` is AdminLTE's, declared `color:#111 !important`. It worked,
        but only where somebody remembered to type it - which was one of the
        three label sites in history.html. A stylesheet rule covers all of them,
        and does not need `!important` because two classes already beat
        Bootstrap's one.
        """
        assert "text-black" not in read(HISTORY_TEMPLATE)

    def test_every_pass_fail_state_in_the_model_has_a_background(self):
        """A state with no background rule renders on the page's own colour.

        Which may well be readable - but it is not measured by the test above,
        because that test can only check backgrounds it can find. This is what
        makes the set complete: add a sixth state to PASS_FAIL_CHOICES without
        a colour in qa.css and this fails, rather than the AA check quietly
        covering five of six.
        """
        css = read(QA_CSS)
        missing = [
            name for name in PASS_FAIL_CLASSES
            if not declarations_for(".%s" % name, css)
        ]
        assert not missing, (
            "these pass/fail states have no background-color rule in qa.css, so "
            "their contrast is not measured: %s" % missing
        )
