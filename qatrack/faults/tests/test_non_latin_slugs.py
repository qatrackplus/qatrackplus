"""
#677: a fault type whose code has no ASCII form got an empty slug, and the pages
that link to it raised NoReverseMatch.

`slugify` keeps only characters with an ASCII form, so a code written wholly in
Chinese, Cyrillic, Greek or Arabic reduces to `""`. Both URL patterns that take a
fault type slug require at least one character, so `{% url %}` raised in
`fault_type_actions.html` - on every row of "All Fault Types" - and in
`_fault_details.html`, which is the fault's own page, a 500.

The issue was reported on 2025-08-28 with the expectation that 4.0's
localisation support would fix it. It does not, and cannot: slugs never pass
through translation. That is why the tests below are about slug generation
rather than about languages.
"""

import importlib
from contextlib import contextmanager
from unittest import mock

from django.apps import apps as django_apps
from django.contrib.auth.models import User
from django.db import models
from django.test import TestCase
from django.urls import reverse

from qatrack.faults.models import FaultType
from qatrack.faults.tests import utils
from qatrack.qa.tests import utils as qa_utils

# Chinese for "beam fault" and "dose deviation", the codes from the report.
BEAM_FAULT = "射束故障"
DOSE_DEVIATION = "剂量偏差"
# Cyrillic and Greek, to show it is "no ASCII form", not "Chinese".
CYRILLIC = "Отказ пучка"
GREEK = "τεστ"


class TestNonLatinCodesGetUsableSlugs(TestCase):

    def test_a_code_with_no_ascii_form_still_gets_a_slug(self):
        ft = FaultType.objects.create(code=BEAM_FAULT)
        assert ft.slug, "a code with no ASCII form got an empty slug (#677)"
        # The pattern both URLs use.
        assert reverse("fault_type_details", kwargs={"slug": ft.slug})

    def test_a_second_such_code_does_not_become_a_bare_number(self):
        """
        The uniqueness loop used to append its counter to the *code* and slugify
        the result. slugify strips the leading dash, so the second Chinese code
        came out as the bare `1` - a working address that means nothing, and one
        a real code of "1" would want.
        """

        first = FaultType.objects.create(code=BEAM_FAULT)
        second = FaultType.objects.create(code=DOSE_DEVIATION)

        assert second.slug != first.slug
        assert not second.slug.isdigit(), second.slug
        assert reverse("fault_type_details", kwargs={"slug": second.slug})

    def test_it_is_not_specific_to_chinese(self):
        for code in (CYRILLIC, GREEK):
            ft = FaultType.objects.create(code=code)
            assert ft.slug, code
            assert reverse("fault_type_details", kwargs={"slug": ft.slug})

    def test_every_slug_stays_unique(self):
        codes = [BEAM_FAULT, DOSE_DEVIATION, CYRILLIC, GREEK, "ABC", "Arrêt"]
        slugs = [FaultType.objects.create(code=c).slug for c in codes]
        assert len(set(slugs)) == len(slugs), sorted(slugs)


class TestOrdinaryCodesAreUntouched(TestCase):
    """
    The fix must not rewrite a slug that already works, because `save()`
    regenerates on every save - so any change here would alter live URLs the
    first time somebody edits a fault type's description.
    """

    def test_ascii_codes_are_unchanged(self):
        assert FaultType.objects.create(code="Beam Fault").slug == "beam-fault"
        assert FaultType.objects.create(code="MLC").slug == "mlc"

    def test_accented_latin_still_transliterates(self):
        """`Arrêt` has an ASCII form, so it never had the bug and must not gain one."""

        assert FaultType.objects.create(code="Arrêt").slug == "arret"

    def test_a_partly_ascii_code_keeps_its_ascii_part(self):
        assert FaultType.objects.create(code="Beam %s" % BEAM_FAULT).slug == "beam"

    def test_a_collision_between_ascii_codes_keeps_its_historical_form(self):
        """
        Regression guard, and the reason the loop below still appends to the
        code rather than to the slug.

        `slugify` strips a trailing "-" or "_" from its result but not from the
        middle, so `slugify("Dose_Rate_")` is `dose_rate` while
        `slugify("Dose_Rate_-1")` keeps the underscore and gives `dose_rate_-1`.
        Appending to the slug instead would give `dose_rate-1`. Only a collision
        reaches that line - but a deployment that has one already has the old
        slug in its URLs, and `save()` regenerates on every save, so the address
        would change the first time anyone edited the record.
        """

        first = FaultType.objects.create(code="Dose_Rate")
        second = FaultType.objects.create(code="Dose_Rate_")

        assert first.slug == "dose_rate"
        # Not "dose_rate-1".
        assert second.slug == "dose_rate_-1", second.slug


class TestTheReportedPagesLoad(TestCase):
    """The failures as a user met them, rather than at the model layer."""

    def setUp(self):
        self.unit = qa_utils.create_unit()
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

        self.first = FaultType.objects.create(code=BEAM_FAULT)
        self.second = FaultType.objects.create(code=DOSE_DEVIATION)
        self.fault = utils.create_fault(unit=self.unit, fault_type=self.first)

    def test_all_fault_types_returns_its_rows(self):
        """
        The page itself answered 200 before; its data request raised
        NoReverseMatch while rendering fault_type_actions.html, so the table
        stayed on "Processing..." with no rows and no error shown.
        """

        resp = self.client.get(
            reverse("fault_type_list"), {},
            content_type='application/json',
            headers={"x-requested-with": 'XMLHttpRequest'},
        )
        assert resp.status_code == 200
        assert len(resp.json()['aaData']) == 2

    def test_the_fault_page_loads(self):
        """`_fault_details.html` links the fault's types; this was a 500."""

        resp = self.client.get(reverse("fault_details", kwargs={'pk': self.fault.pk}))
        assert resp.status_code == 200

    def test_the_fault_type_page_loads(self):
        resp = self.client.get(reverse("fault_type_details", kwargs={'slug': self.first.slug}))
        assert resp.status_code == 200


class TestTheRepairMigration(TestCase):
    """
    `0016_repair_empty_fault_type_slugs` fixes deployments that already have a
    broken fault type. They cannot be repaired by hand: the record's own page is
    a 500, and it is unreachable from "All Fault Types" for the same reason.

    The migration receives a *historical* model, which has no `save()` override,
    so `save()` is patched down to Django's for these tests. Without that the
    override would regenerate the slug from the code and the assertions would
    pass whatever the migration's own logic did.
    """

    @staticmethod
    def _repair():
        # The module name starts with a digit, so it cannot be imported by name.
        module = importlib.import_module(
            "qatrack.faults.migrations.0016_repair_empty_fault_type_slugs"
        )
        return module.repair_empty_slugs(django_apps, None)

    @contextmanager
    def _historical(self):
        """Make FaultType behave like the migration's historical model."""

        with mock.patch.object(FaultType, "save", models.Model.save):
            yield

    def test_an_empty_slug_is_repaired(self):
        ft = FaultType.objects.create(code=BEAM_FAULT)
        FaultType.objects.filter(pk=ft.pk).update(slug="")

        with self._historical():
            self._repair()

        ft.refresh_from_db()
        assert ft.slug == "faulttype"
        assert reverse("fault_type_details", kwargs={"slug": ft.slug})

    def test_it_does_not_collide_with_an_existing_slug(self):
        squatter = FaultType.objects.create(code="faulttype")
        broken = FaultType.objects.create(code=BEAM_FAULT)
        FaultType.objects.filter(pk=broken.pk).update(slug="")

        with self._historical():
            self._repair()

        broken.refresh_from_db()
        squatter.refresh_from_db()
        assert squatter.slug == "faulttype"
        assert broken.slug == "faulttype-1"

    def test_it_keeps_counting_past_a_taken_suffix(self):
        """
        Exercises the migration's loop rather than just its first step.

        The case it exists for - several empty slugs at once - cannot be set up
        here: `slug` is unique and SQLite enforces it, so a second `update(slug="")`
        raises IntegrityError. That case belongs to MS SQL Server deployments,
        where 4.0 is known to have dropped unique constraints. Forcing the
        counter past two taken names covers the same code.
        """

        FaultType.objects.create(code="faulttype")
        FaultType.objects.create(code="faulttype-1")
        broken = FaultType.objects.create(code=BEAM_FAULT)
        FaultType.objects.filter(pk=broken.pk).update(slug="")

        with self._historical():
            self._repair()

        broken.refresh_from_db()
        assert broken.slug == "faulttype-2"

    def test_working_slugs_are_left_alone(self):
        """
        Including the meaningless numeric ones the old uniqueness loop produced.
        They are working addresses that may be linked, and are indistinguishable
        from a fault type legitimately coded "1".
        """

        ascii_ft = FaultType.objects.create(code="ABC")
        numeric = FaultType.objects.create(code=DOSE_DEVIATION)
        FaultType.objects.filter(pk=numeric.pk).update(slug="1")
        broken = FaultType.objects.create(code=CYRILLIC)
        FaultType.objects.filter(pk=broken.pk).update(slug="")

        with self._historical():
            self._repair()

        ascii_ft.refresh_from_db()
        numeric.refresh_from_db()
        broken.refresh_from_db()
        assert ascii_ft.slug == "abc"
        assert numeric.slug == "1"
        assert broken.slug == "faulttype"

    def test_it_does_nothing_when_there_is_nothing_to_repair(self):
        FaultType.objects.create(code="ABC")

        with self._historical():
            self._repair()

        assert list(FaultType.objects.values_list("slug", flat=True)) == ["abc"]
