"""`qatrack.W012` - calculation procedures that draw with pyplot.

The check's own docstring says why it exists. These tests cover the two things
worth pinning: that the parser recognises every way a procedure can reach
pyplot, and that it does not fire on text that merely mentions it.
"""

from unittest import mock

from django.core.checks import Warning
from django.db.utils import DatabaseError
from django.test import TestCase

from qatrack.qa import models
from qatrack.qa.tests import utils
from qatrack.qatrack_core.checks import (
    check_calculation_procedures_use_pyplot,
    procedure_uses_pyplot,
)


class TestProcedureUsesPyplot:
    """The parser, without a database."""

    def test_an_import_with_an_alias(self):
        assert procedure_uses_pyplot("import matplotlib.pyplot as plt\nplt.plot([1])") == ['plt']

    def test_an_import_without_an_alias(self):
        assert procedure_uses_pyplot("import matplotlib.pyplot\n") == ['matplotlib.pyplot']

    def test_from_matplotlib_import_pyplot(self):
        assert procedure_uses_pyplot("from matplotlib import pyplot\n") == ['pyplot']

    def test_from_matplotlib_import_pyplot_as(self):
        assert procedure_uses_pyplot("from matplotlib import pyplot as p\n") == ['p']

    def test_from_pyplot_import_a_name(self):
        assert procedure_uses_pyplot("from matplotlib.pyplot import plot\n") == ['matplotlib.pyplot']

    def test_reached_through_the_context_without_importing(self):
        """The context hands procedures `matplotlib`, so no import is needed.

        This is the route a grep for "import" would miss entirely.
        """
        assert procedure_uses_pyplot("fig = matplotlib.pyplot.figure()\n") == ['matplotlib.pyplot']

    def test_pylab(self):
        assert procedure_uses_pyplot("import pylab\npylab.plot([1])") == ['pylab']

    def test_the_safe_pattern_is_not_reported(self):
        source = (
            "fig = UTILS.get_figure()\n"
            "ax = fig.add_subplot(111)\n"
            "ax.plot([1, 2], [3, 4])\n"
            "UTILS.write_file('p.png', fig)\n"
        )
        assert procedure_uses_pyplot(source) == []

    def test_a_comment_mentioning_pyplot_is_not_reported(self):
        """Why this is parsed and not searched."""
        assert procedure_uses_pyplot("# do not use matplotlib.pyplot here\nresult = 1\n") == []

    def test_a_string_mentioning_pyplot_is_not_reported(self):
        assert procedure_uses_pyplot("result = 'matplotlib.pyplot'\n") == []

    def test_a_docstring_mentioning_pyplot_is_not_reported(self):
        assert procedure_uses_pyplot('"""Avoid matplotlib.pyplot."""\nresult = 1\n') == []

    def test_other_numpy_and_matplotlib_use_is_not_reported(self):
        source = "import numpy as np\nresult = float(np.mean([1, 2]))\n"
        assert procedure_uses_pyplot(source) == []

    def test_a_broken_procedure_is_not_this_functions_problem(self):
        """Whatever reports unparseable procedures reports them, not this."""
        assert procedure_uses_pyplot("def (\n") == []

    def test_no_procedure_at_all(self):
        assert procedure_uses_pyplot('') == []


class TestPyplotCheck(TestCase):
    """The check, against the database."""

    def make_test(self, procedure, name=None):
        test = utils.create_test(name=name, test_type=models.COMPOSITE)
        test.calculation_procedure = procedure
        test.save()
        return test

    def test_nothing_is_reported_when_no_procedure_uses_pyplot(self):
        self.make_test("result = 1\n")
        assert check_calculation_procedures_use_pyplot(None, databases=['default']) == []

    def test_a_procedure_using_pyplot_is_reported(self):
        self.make_test("import matplotlib.pyplot as plt\nplt.plot([1])\nresult = 1\n", name="Flatness plot")
        problems = check_calculation_procedures_use_pyplot(None, databases=['default'])
        assert len(problems) == 1
        assert isinstance(problems[0], Warning)
        assert problems[0].id == 'qatrack.W012'
        assert 'Flatness plot' in problems[0].msg

    def test_the_hint_gives_the_replacement_and_names_the_exposed_deployment(self):
        self.make_test("import matplotlib.pyplot as plt\nresult = 1\n")
        hint = check_calculation_procedures_use_pyplot(None, databases=['default'])[0].hint
        assert 'UTILS.get_figure()' in hint
        # The check cannot see what is serving, so the hint has to say which
        # deployment turns this into a fault and which does not.
        assert 'Windows' in hint
        assert 'sync workers' in hint

    def test_many_offenders_are_summarised_rather_than_listed(self):
        for i in range(12):
            self.make_test("import matplotlib.pyplot as plt\nresult = 1\n", name="Plot %02d" % i)
        problems = check_calculation_procedures_use_pyplot(None, databases=['default'])
        assert len(problems) == 1
        assert '12 calculation procedure(s)' in problems[0].msg
        assert 'and 2 more' in problems[0].msg

    def test_nothing_runs_without_a_database_argument(self):
        """Tags.database means `manage.py check` alone must not pay for this."""
        self.make_test("import matplotlib.pyplot as plt\nresult = 1\n")
        assert check_calculation_procedures_use_pyplot(None) == []
        assert check_calculation_procedures_use_pyplot(None, databases=[]) == []

    def test_an_unreachable_database_is_not_this_checks_problem(self):
        from django.db import connection

        self.make_test("import matplotlib.pyplot as plt\nresult = 1\n")
        with mock.patch.object(
            connection.introspection, 'table_names', side_effect=DatabaseError('nope')
        ):
            assert check_calculation_procedures_use_pyplot(None, databases=['default']) == []

    def test_tables_that_do_not_exist_yet_are_skipped(self):
        """A fresh install's first `migrate` must not produce noise."""
        from django.db import connection

        self.make_test("import matplotlib.pyplot as plt\nresult = 1\n")
        with mock.patch.object(connection.introspection, 'table_names', return_value=[]):
            assert check_calculation_procedures_use_pyplot(None, databases=['default']) == []

    def test_the_check_is_registered_under_the_database_tag(self):
        from django.core.checks import registry

        registered = [
            c for c in registry.registry.get_checks(include_deployment_checks=False)
            if c is check_calculation_procedures_use_pyplot
        ]
        assert registered, "the check is not registered"
        assert registry.registry.tags_available() and 'database' in registry.registry.tags_available()
