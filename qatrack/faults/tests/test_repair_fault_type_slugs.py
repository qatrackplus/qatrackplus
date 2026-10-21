"""Repairing fault types whose slug was never usable.

A code with no ASCII form slugified to an empty string, which the field allows
and the URL patterns refuse: `{% url %}` raises `NoReverseMatch` and the page
500s. The generator now falls back to the model name, but only when a record is
saved - and a record whose pages 500 cannot be saved through the site. These
tests cover the repair of what is already in the database. Raised by Copilot on
PR crcrewso#18.
"""

from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from qatrack.faults.models import FaultType


class TestRepairFaultTypeSlugs(TestCase):

    def _break(self, code, slug=""):
        """A record as the old generator would have left it."""
        fault_type = FaultType.objects.create(code=code)
        FaultType.objects.filter(pk=fault_type.pk).update(slug=slug)
        fault_type.refresh_from_db()
        assert fault_type.slug == slug
        return fault_type

    def _run(self, *args):
        out = StringIO()
        call_command("repair_fault_type_slugs", *args, stdout=out, stderr=StringIO())
        return out.getvalue()

    def test_an_empty_slug_is_repaired(self):
        fault_type = self._break("测试")
        self._run()
        fault_type.refresh_from_db()
        assert fault_type.slug, "the slug is still unusable"
        assert fault_type.slug.strip() == fault_type.slug

    def test_the_repaired_slug_reverses(self):
        """The whole point: the page stops returning 500."""
        fault_type = self._break("测试")
        with self.assertRaises(NoReverseMatch):
            reverse("fault_type_details", kwargs={"slug": fault_type.slug})

        self._run()
        fault_type.refresh_from_db()
        assert reverse("fault_type_details", kwargs={"slug": fault_type.slug})

    def test_working_slugs_are_left_exactly_alone(self):
        """Rewriting a working slug would break a working URL."""
        ordinary = FaultType.objects.create(code="ABC-123")
        before = ordinary.slug
        assert before

        self._break("测试")
        self._run()

        ordinary.refresh_from_db()
        assert ordinary.slug == before

    def test_only_one_record_can_be_broken_this_way(self):
        """`slug` is unique, so a second empty slug cannot exist.

        Which bounds the problem: a site has at most one fault type with an
        empty slug - the first code that had no ASCII form. The second such
        code got `slugify("<code>-1")`, and because slugify strips the leading
        dash, that left the bare slug `1`: meaningless, but a working URL.
        This command does not touch those. Rewriting a slug that resolves
        would break a link that works today, and the generator's docstring
        makes the same promise.
        """
        self._break("测试")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._break("試験")

    def test_a_repair_does_not_collide_with_an_existing_slug(self):
        """The fallback base is the model name, which a code could already own."""
        taken = FaultType.objects.create(code="faulttype")
        assert taken.slug == "faulttype"

        broken = self._break("测试")
        self._run()

        broken.refresh_from_db()
        taken.refresh_from_db()
        assert broken.slug and broken.slug != taken.slug
        assert taken.slug == "faulttype", "an untouched record was rewritten"

    def test_dry_run_writes_nothing(self):
        fault_type = self._break("测试")
        output = self._run("--dry-run")
        fault_type.refresh_from_db()
        assert fault_type.slug == "", "a dry run wrote to the database"
        assert "nothing was written" in output
        assert "测试" in output, "a dry run must say what it would change"

    def test_a_clean_database_says_so(self):
        FaultType.objects.create(code="ABC-123")
        assert "No fault type needs repair" in self._run()
