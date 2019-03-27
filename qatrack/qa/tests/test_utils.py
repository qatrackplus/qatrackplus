import io
import json

from django.test import TestCase

from qatrack.qa import models, testpack
from qatrack.qa import utils as qautils
from qatrack.qa.tests import utils


class TestUtils(TestCase):

    def test_unique(self):
        items = ["foo", "foo", "bar"]
        self.assertListEqual(items[1:], qautils.unique(items))

    def test_almost_equal_none(self):
        self.assertFalse(qautils.almost_equal(None, None))

    def test_almost_equal_equal(self):
        self.assertTrue(qautils.almost_equal(1, 1))

    def test_almost_equal_small(self):
        self.assertTrue(qautils.almost_equal(1, 1 + 1E-10))

    def test_almost_equal_zero(self):
        self.assertTrue(qautils.almost_equal(0, 0))

    def test_tokenize(self):
        proc = "result = a + 2"
        self.assertListEqual(proc.split(), qautils.tokenize_composite_calc(proc))

    def test_set_encoder_set(self):
        self.assertIsInstance(json.dumps(set([1, 2]), cls=qautils.SetEncoder), str)

    def test_float_format(self):
        numbers = (
            (0.999, 3, "0.999"),
            (-0.999, 3, "-0.999"),
            (0.999, 1, "1"),
            (0.999, 2, "1.0"),
            (0.0, 4, "0"),
            (-0.0, 4, "0"),
            (1234.567, 1, "1e+3"),
            (1234.567, 2, "1.2e+3"),
            (1234.567, 5, "1234.6"),
        )

        for number, prec, expected in numbers:
            self.assertEqual(qautils.to_precision(number, prec), expected)


class TestImportExport(TestCase):

    def setUp(self):

        self.user = utils.create_user()
        self.tl1 = utils.create_test_list("tl1 é")
        self.tl2 = utils.create_test_list("tl2")
        self.tl3 = utils.create_test_list("tl3")
        self.tlc = utils.create_cycle([self.tl1, self.tl2])
        self.t1 = utils.create_test("t1")
        self.t2 = utils.create_test("t2")
        self.t3 = utils.create_test("t3")
        self.t4 = utils.create_test("t4")
        utils.create_test_list_membership(self.tl1, self.t1)
        utils.create_test_list_membership(self.tl2, self.t2)
        utils.create_test_list_membership(self.tl3, self.t3)

        self.tlqs = models.TestList.objects.filter(pk=self.tl3.pk)
        self.tlcqs = models.TestListCycle.objects.filter(pk=self.tlc.pk)
        self.extra = models.Test.objects.filter(pk=self.t4.pk)

    def test_round_trip(self):
        pack = json.dumps(testpack.create_testpack(
            test_lists=self.tlqs,
            cycles=self.tlcqs,
            extra_tests=self.extra,
        ))
        models.Category.objects.all().delete()
        models.TestListCycle.objects.all().delete()
        models.TestList.objects.all().delete()
        models.Test.objects.all().delete()
        testpack.add_testpack(pack)

        assert models.Test.objects.count() == 4
        assert models.TestList.objects.count() == 3
        assert models.TestListMembership.objects.count() == 3
        assert models.TestListCycle.objects.count() == 1
        assert models.TestListCycleMembership.objects.count() == 2

    def test_create_pack(self):

        pack = testpack.create_testpack(self.tlqs, self.tlcqs)

        assert 'meta' in pack
        assert 'objects' in pack

        test_found = False
        list_found = False
        for tl_dat in pack['objects']['testlists']:
            tl = json.loads(tl_dat)
            if tl['object']['fields']['name'] == self.tl3.name:
                list_found = True

            for o in tl['dependencies']:
                try:
                    if o['fields']['name'] == self.t3.name:
                        test_found = True
                except KeyError:
                    pass

        assert list_found and test_found

    def test_save_pack(self):
        pack = testpack.create_testpack(self.tlqs, self.tlcqs)
        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        # check the accented character in test list 1 name was written
        assert "\\u00e9" in fp.read()

    def test_non_destructive_load(self):
        ntl = models.TestList.objects.count()
        nt = models.Test.objects.count()
        pack = testpack.create_testpack(self.tlqs, self.tlcqs, self.extra)
        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        testpack.load_testpack(fp)
        assert models.TestList.objects.count() == 2 * ntl
        assert models.Test.objects.count() == 2 * nt

    def test_load(self):
        pack = testpack.create_testpack(self.tlqs, self.tlcqs)
        models.TestList.objects.all().delete()
        models.Test.objects.all().delete()
        models.TestListCycle.objects.all().delete()

        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        testpack.load_testpack(fp)

        assert models.TestList.objects.filter(name=self.tl1.name).exists()
        assert models.Test.objects.filter(name=self.t1.name).exists()
        assert models.TestListCycle.objects.filter(name=self.tlc.name).exists()
        assert self.tl1.name in models.TestListCycle.objects.values_list("test_lists__name", flat=True)

    def test_selective_load(self):
        pack = testpack.create_testpack(models.TestList.objects.all(), self.tlcqs)
        models.TestList.objects.all().delete()
        models.Test.objects.all().delete()
        models.TestListCycle.objects.all().delete()

        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        testpack.load_testpack(fp, test_keys=[self.t1.natural_key()], test_list_keys=[self.tl1.natural_key()], cycle_keys=[])

        assert models.TestList.objects.count() == 1
        assert models.Test.objects.count() == 1
        assert models.TestListCycle.objects.count() == 0

    def test_existing_created_user_not_overwritten(self):
        user2 = utils.create_user(uname="user2")
        pack = testpack.create_testpack(self.tlqs, self.tlcqs)

        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        testpack.load_testpack(fp, user2)

        assert models.TestList.objects.get(slug=self.tl1.slug).created_by != user2

    def test_existing_objs_not_deleted(self):
        pack = testpack.create_testpack(self.tlqs, self.tlcqs)

        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        testpack.load_testpack(fp, test_keys=[self.t1.natural_key()], test_list_keys=[self.tl1.natural_key()], cycle_keys=[])

        assert models.TestList.objects.filter(name__in=[self.tl2.name, self.tl3.name]).count() == 2
        assert models.Test.objects.filter(name__in=[self.t2.name, self.t3.name]).count() == 2
        assert models.TestListCycle.objects.filter(name__in=[self.tlc.name]).count() == 1

    def test_extra_tests(self):
        extra = utils.create_test("extra test")
        extra_qs = models.Test.objects.filter(pk=extra.pk)
        pack = testpack.create_testpack(self.tlqs, self.tlcqs, extra_tests=extra_qs)
        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        assert "extra test" in fp.read()

    def test_extra_tests_loaded(self):
        extra = utils.create_test("extra test")
        extra_qs = models.Test.objects.filter(pk=extra.pk)
        pack = testpack.create_testpack(self.tlqs, self.tlcqs, extra_tests=extra_qs)
        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        models.Test.objects.all().delete()
        testpack.load_testpack(fp, test_keys=[extra.natural_key()], test_list_keys=[], cycle_keys=[])
        assert models.Test.objects.filter(name=extra.name).exists()

    def test_sublist(self):
        tl5 = utils.create_test_list("tl5")
        t5 =  utils.create_test("t5")
        utils.create_test_list_membership(tl5, t5, order=0)
        utils.create_sublist(tl5, self.tl1, order=2)
        utils.create_sublist(tl5, self.tl2, order=3)
        pack = json.dumps(testpack.create_testpack(test_lists=models.TestList.objects.filter(pk=tl5.pk)))
        models.TestList.objects.all().delete()
        models.Test.objects.all().delete()
        assert models.Sublist.objects.count() == 0
        testpack.add_testpack(pack, test_list_keys=[tl5.natural_key()])
        assert models.Sublist.objects.count() == 2
        assert models.TestListMembership.objects.count() == 3
        for sl in models.Sublist.objects.all():
            assert sl.child.testlistmembership_set.count() == 1
        assert models.TestList.objects.count() == 3
        assert models.TestList.objects.get(name="tl5")
