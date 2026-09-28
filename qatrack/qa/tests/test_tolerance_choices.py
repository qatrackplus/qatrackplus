"""Which tolerances the admin offers for a given test type.

A string test - STRING or STRING_COMPOSITE as well as MULTIPLE_CHOICE - is judged
by `TestInstance.string_pass_fail()`, which compares the value against a multiple
choice tolerance's pass and tolerance lists. So a multiple choice tolerance is the
only kind that means anything for one.

v4 narrowed the admin form to offer multiple choice tolerances only when the test
type was exactly MULTIPLE_CHOICE, dropping v3.1's `or is_string_type()`. A site
upgrading from 3.1 found a string composite that returned 'PASS' /
'Incorrect Linac' / 'Incorrect Field' could no longer be given the tolerance it
had been using, and was offered absolute and percentage instead (#881).

The evaluation side never stopped supporting it, so this is about what the form
allows, not about how a result is judged.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from qatrack.qa import models
from qatrack.qa.admin import UnitTestInfoForm
from qatrack.qa.tests import utils


class TestUnitTestInfoToleranceChoices(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser("tol", "tol@e.com", "pw")
        self.absolute = utils.create_tolerance(tol_type=models.ABSOLUTE, created_by=self.user)
        self.percent = utils.create_tolerance(tol_type=models.PERCENT, created_by=self.user)
        self.mc = utils.create_tolerance(
            tol_type=models.MULTIPLE_CHOICE,
            mc_pass_choices="PASS",
            mc_tol_choices="Incorrect Linac,Incorrect Field",
            created_by=self.user,
        )

    def offered_for(self, test_type, **kwargs):
        """The tolerance types the admin form offers for a test of this type."""
        test = utils.create_test(name="t-%s" % test_type, test_type=test_type, **kwargs)
        utc = utils.create_unit_test_collection()
        uti = models.UnitTestInfo.objects.get_or_create(unit=utc.unit, test=test)[0]
        form = UnitTestInfoForm(instance=uti)
        return set(form.fields["tolerance"].queryset.values_list("type", flat=True))

    def test_string_composite_is_offered_multiple_choice(self):
        """#881: the reporter's case."""
        assert self.offered_for(models.STRING_COMPOSITE) == {models.MULTIPLE_CHOICE}

    def test_plain_string_is_offered_multiple_choice(self):
        assert self.offered_for(models.STRING) == {models.MULTIPLE_CHOICE}

    def test_multiple_choice_is_offered_multiple_choice(self):
        assert self.offered_for(
            models.MULTIPLE_CHOICE, choices="PASS,Incorrect Linac") == {models.MULTIPLE_CHOICE}

    def test_numerical_is_not_offered_multiple_choice(self):
        """The narrowing must still narrow - a guard against over-widening."""
        offered = self.offered_for(models.SIMPLE)
        assert models.MULTIPLE_CHOICE not in offered
        assert models.BOOLEAN not in offered
        assert models.ABSOLUTE in offered and models.PERCENT in offered

    def test_wraparound_is_offered_absolute_only(self):
        """A percentage of a wraparound value is not meaningful; v3.1 restricted it."""
        assert self.offered_for(models.WRAPAROUND) == {models.ABSOLUTE}

    def test_string_test_hides_the_numerical_reference_field(self):
        test = utils.create_test(name="t-hide", test_type=models.STRING_COMPOSITE)
        utc = utils.create_unit_test_collection()
        uti = models.UnitTestInfo.objects.get_or_create(unit=utc.unit, test=test)[0]
        form = UnitTestInfoForm(instance=uti)
        assert form.fields["reference_value"].widget.input_type == "hidden"


class TestStringPassFailUsesTheTolerance(TestCase):
    """The evaluation side, to show the form was the only thing in the way."""

    def test_a_string_composite_is_judged_by_its_multiple_choice_tolerance(self):
        user = User.objects.create_superuser("sp", "sp@e.com", "pw")
        tol = utils.create_tolerance(
            tol_type=models.MULTIPLE_CHOICE,
            mc_pass_choices="PASS",
            mc_tol_choices="Incorrect Linac,Incorrect Field",
            created_by=user,
        )
        test = utils.create_test(name="t-judge", test_type=models.STRING_COMPOSITE)
        utc = utils.create_unit_test_collection()
        uti = models.UnitTestInfo.objects.get_or_create(unit=utc.unit, test=test)[0]
        uti.tolerance = tol
        uti.save()

        tli = utils.create_test_list_instance(unit_test_collection=utc, created_by=user)
        for value, expected in (("PASS", models.OK),
                                ("Incorrect Linac", models.TOLERANCE),
                                ("something else entirely", models.ACTION)):
            ti = models.TestInstance(
                unit_test_info=uti, tolerance=tol, string_value=value,
                test_list_instance=tli, created_by=user, modified_by=user,
                status=utils.create_status(),
            )
            ti.calculate_pass_fail()
            assert ti.pass_fail == expected, (value, ti.pass_fail)
