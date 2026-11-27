"""A wraparound value has to reach the numeric branch that formats it.

`qa/js/qa.js` sets a test's displayed value in a chain of `else if`s on the test
type. Wraparound was missing from the numeric arm, so a wraparound value was
left unformatted on the perform page while simple and composite values were
formatted. randlet fixed it on the unreleased 3.2.0 branch in a single line
(`25831150`, 2022-01-30) and the fix never reached a release; this is that line,
brought forward.

It is pinned here rather than left to a reviewer's eye because the arm is one
line of JavaScript inside a 1800-line module, there is no JavaScript test runner
in this project, and the failure is silent - the page renders, the number is
simply the wrong shape. `reports/tests/test_schedule_dialog_css.py` and
`test_dateformats.py::TestNoJavascriptHardCodesADateFormat` assert against
static assets from Python in the same way.

Deliberately NOT asserted: that `QAUtils.CONSTANT` is in the same arm. It is
not, and that is correct - constants have their own branch further down, which
sets the value from `data("formatted")`. randlet's fix did not touch constants
either, and this commit reproduces that fix as it was written.
"""

import os
import re

from django.conf import settings

QA_JS = os.path.join(
    settings.PROJECT_ROOT, 'qa', 'static', 'qa', 'js', 'qa.js'
)

# The arm itself: an `else if` over test types whose body formats the value.
NUMERIC_ARM = re.compile(
    r'\}else if \(tt === QAUtils\.SIMPLE[^)]*\)\{', re.MULTILINE
)


def qa_js():
    with open(QA_JS, encoding='utf8') as f:
        return f.read()


class TestTheNumericArmExists:
    """Without this, the assertion below could pass by matching nothing."""

    def test_the_arm_is_there_to_be_checked(self):
        source = qa_js()
        found = NUMERIC_ARM.findall(source)
        assert len(found) == 1, (
            'expected exactly one `else if (tt === QAUtils.SIMPLE ...)` arm in '
            'qa.js, found %d - the test below is checking the wrong thing' % len(found)
        )


class TestWraparoundIsFormattedLikeTheOtherNumbers:

    def test_the_numeric_arm_names_wraparound(self):
        arm = NUMERIC_ARM.search(qa_js()).group(0)
        assert 'QAUtils.WRAPAROUND' in arm, (
            'the numeric arm is %r, which leaves a wraparound value unformatted '
            'on the perform page' % arm
        )
