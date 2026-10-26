"""An autosave written in an older date format still loads as the right date.

A Date test's value is autosaved as the string the user saw, so an autosave
written before QATRACK_DATE_FORMAT was introduced - or before any later change
to it - holds that value in the *old* display format. `qa.js` hands it to
flatpickr's `setDate()`, which parses with the *current* format and succeeds on
the wrong date rather than failing, so the operator sees a plausible date that
is not the one they typed.

The defect and the fix are nsmela's, from his review of q#873.
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from qatrack.qa import models
from qatrack.qa.tests import utils
from qatrack.qatrack_core.dates import (
    format_as_date,
    format_datetime,
    parse_date,
    parse_datetime,
)


class TestAutoSaveLoadsDatesInTheCurrentFormat(TestCase):

    def setUp(self):
        user = User.objects.create_superuser("autosave_fmt", "a@b.com", "password")
        self.client.force_login(user)
        self.utc = utils.create_unit_test_collection()
        self.test_list = self.utc.tests_object
        self.load_url = reverse("autosave_load")

    def add_test(self, name, test_type):
        # No UnitTestInfo needed: the normalisation reads the test list's own
        # tests, and create_unit_test_collection has already made the rows for
        # the list it built.
        test = utils.create_test(name=name, test_type=test_type)
        utils.create_test_list_membership(self.test_list, test)
        return test

    def load(self, stored):
        auto = models.AutoSave.objects.create(
            unit_test_collection=self.utc,
            test_list=self.test_list,
            created_by=self.test_list.created_by,
            modified_by=self.test_list.created_by,
            data={'tests': stored},
        )
        resp = self.client.get(self.load_url, {'autosave_id': auto.pk})
        assert resp.status_code == 200, resp.status_code
        return json.loads(resp.content)['data']['tests']

    def test_a_date_stored_in_the_old_display_format_is_returned_in_the_current_one(self):
        """The server must hand over the current format, not the stored one.

        This is where the assertion has to bite. The misparse itself happens in
        the browser - flatpickr reads `03 May 2026` with the current format and
        lands on 1 January without complaining - so a Python test cannot
        observe the wrong date. What it can observe is the only thing that
        prevents it: that the value leaving the server is already in the format
        the picker is configured to parse.

        Asserting on the *content* of the string (that it still says 2026, say)
        passes without the fix, because the raw stored value says 2026 too.
        """
        test = self.add_test("old_format_date", models.DATE)
        out = self.load({test.slug: "03 May 2026"})
        expected = format_as_date(parse_date("03 May 2026"))
        assert out[test.slug] == expected
        assert out[test.slug] != "03 May 2026", "the stored format was passed straight through"

    def test_a_date_already_in_the_current_format_is_unchanged(self):
        test = self.add_test("current_format_date", models.DATE)
        stored = self.load({test.slug: "2026-05-03"})[test.slug]
        assert self.load({test.slug: stored})[test.slug] == stored

    def test_a_datetime_stored_in_the_old_display_format_is_returned_in_the_current_one(self):
        test = self.add_test("old_format_datetime", models.DATETIME)
        out = self.load({test.slug: "03 May 2026 13:45"})
        expected = format_datetime(parse_datetime("03 May 2026 13:45"))
        assert out[test.slug] == expected
        assert out[test.slug] != "03 May 2026 13:45", "the stored format was passed straight through"

    def test_an_unparseable_value_is_dropped_so_the_field_comes_up_empty(self):
        """Blank is recoverable; a plausible wrong date is not.

        Passing the value through would not avoid a guess - it hands the string
        to flatpickr, the parser that misreads dates silently. Dropping the key
        means `qa.js` never calls set_value() for that test, because it iterates
        the keys that are present, so the operator sees an empty field.
        """
        test = self.add_test("nonsense_date", models.DATE)
        out = self.load({test.slug: "not a date at all"})
        assert test.slug not in out, out

    def test_dropping_one_value_leaves_the_others_alone(self):
        """One unreadable date must not cost the operator the whole session."""
        bad = self.add_test("unreadable", models.DATE)
        good = self.add_test("readable", models.DATE)
        out = self.load({bad.slug: "???", good.slug: "03 May 2026", "a_comment": "kept"})
        assert bad.slug not in out
        assert out[good.slug] == format_as_date(parse_date("03 May 2026"))
        assert out["a_comment"] == "kept"

    def test_non_date_tests_are_left_alone(self):
        test = self.add_test("a_string", models.STRING)
        assert self.load({test.slug: "03 May 2026"})[test.slug] == "03 May 2026"

    def test_an_autosave_with_no_tests_key_still_loads(self):
        auto = models.AutoSave.objects.create(
            unit_test_collection=self.utc,
            test_list=self.test_list,
            created_by=self.test_list.created_by,
            modified_by=self.test_list.created_by,
            data={},
        )
        resp = self.client.get(self.load_url, {'autosave_id': auto.pk})
        assert resp.status_code == 200
        assert json.loads(resp.content)['data'] == {}
