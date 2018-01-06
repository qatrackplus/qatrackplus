import io
import json

from django.core.serializers import deserialize
from django.test import TestCase

from qatrack.qa import models
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
        utils.create_test_list_membership(self.tl1, self.t1)
        utils.create_test_list_membership(self.tl2, self.t2)
        utils.create_test_list_membership(self.tl3, self.t3)

        self.tlqs = models.TestList.objects.filter(pk=self.tl3.pk)
        self.tlcqs = models.TestListCycle.objects.filter(pk=self.tlc.pk)

    def test_create_pack(self):

        pack = qautils.create_testpack(self.tlqs, self.tlcqs)

        assert 'meta' in pack
        assert 'objects' in pack
        assert len(pack['objects']) == 7

        test_found = False
        list_found = False
        for qs in pack['objects']:
            for o in deserialize('json', qs):
                if hasattr(o.object, "name"):
                    if o.object.name == self.tl1.name:
                        list_found = True
                    elif o.object.name == self.t1.name:
                        test_found = True

        assert list_found and test_found

    def test_save_pack(self):
        pack = qautils.create_testpack(self.tlqs, self.tlcqs)
        fp = io.StringIO()
        qautils.save_test_pack(pack, fp)
        fp.seek(0)
        # check the accented character in test list 1 name was written
        assert "\\u00e9" in fp.read()

    def test_non_destructive_load(self):
        ntl = models.TestList.objects.count()
        nt = models.Test.objects.count()
        pack = qautils.create_testpack(self.tlqs, self.tlcqs)
        fp = io.StringIO()
        qautils.save_test_pack(pack, fp)
        fp.seek(0)
        qautils.load_test_pack(fp)
        assert models.TestList.objects.count() == 2 * ntl
        assert models.Test.objects.count() == 2 * nt

    def test_load(self):
        pack = qautils.create_testpack(self.tlqs, self.tlcqs)
        models.TestList.objects.all().delete()
        models.Test.objects.all().delete()
        models.TestListCycle.objects.all().delete()

        fp = io.StringIO()
        qautils.save_test_pack(pack, fp)
        fp.seek(0)
        qautils.load_test_pack(fp)

        assert models.TestList.objects.filter(name=self.tl1.name).exists()
        assert models.Test.objects.filter(name=self.t1.name).exists()
        assert models.TestListCycle.objects.filter(name=self.tlc.name).exists()
        assert self.tl1.name in models.TestListCycle.objects.values_list("test_lists__name", flat=True)

    def test_object_names(self):
        pack = qautils.create_testpack(self.tlqs, self.tlcqs)
        fp = io.StringIO()
        qautils.save_test_pack(pack, fp)
        fp.seek(0)
        names = qautils.test_pack_object_names(fp.read())
        expected = {
            'test': [self.t1.name, self.t2.name, self.t3.name],
            'testlist': [self.tl1.name, self.tl2.name, self.tl3.name],
            'testlistcycle': [self.tlc.name]
        }
        assert names == expected

    def test_selective_load(self):
        pack = qautils.create_testpack(self.tlqs, self.tlcqs)
        models.TestList.objects.all().delete()
        models.Test.objects.all().delete()
        models.TestListCycle.objects.all().delete()

        fp = io.StringIO()
        qautils.save_test_pack(pack, fp)
        fp.seek(0)
        qautils.load_test_pack(fp, test_names=[self.t1.name], test_list_names=[self.tl1.name], cycle_names=[])

        assert models.TestList.objects.count() == 1
        assert models.Test.objects.count() == 1
        assert models.TestListCycle.objects.count() == 0

    def test_existing_created_user_not_overwritten(self):
        user2 = utils.create_user(uname="user2")
        pack = qautils.create_testpack(self.tlqs, self.tlcqs)

        fp = io.StringIO()
        qautils.save_test_pack(pack, fp)
        fp.seek(0)
        qautils.load_test_pack(fp, user2)

        assert models.TestList.objects.get(slug=self.tl1.slug).created_by != user2

    def test_existing_objs_not_deleted(self):
        pack = qautils.create_testpack(self.tlqs, self.tlcqs)

        fp = io.StringIO()
        qautils.save_test_pack(pack, fp)
        fp.seek(0)
        qautils.load_test_pack(fp, test_names=[self.t1.name], test_list_names=[self.tl1.name], cycle_names=[])

        assert models.TestList.objects.filter(name__in=[self.tl2.name, self.tl3.name]).count() == 2
        assert models.Test.objects.filter(name__in=[self.t2.name, self.t3.name]).count() == 2
        assert models.TestListCycle.objects.filter(name__in=[self.tlc.name]).count() == 1

    def test_extra_tests(self):
        extra = utils.create_test("extra test")
        extra_qs = models.Test.objects.filter(pk=extra.pk)
        pack = qautils.create_testpack(self.tlqs, self.tlcqs, extra_tests=extra_qs)
        fp = io.StringIO()
        qautils.save_test_pack(pack, fp)
        fp.seek(0)
        assert "extra test" in fp.read()

    def test_extra_tests_loaded(self):
        extra = utils.create_test("extra test")
        extra_qs = models.Test.objects.filter(pk=extra.pk)
        pack = qautils.create_testpack(self.tlqs, self.tlcqs, extra_tests=extra_qs)
        fp = io.StringIO()
        qautils.save_test_pack(pack, fp)
        fp.seek(0)
        models.Test.objects.all().delete()
        qautils.load_test_pack(fp, test_names=[extra.name], test_list_names=[], cycle_names=[])
        assert models.Test.objects.filter(name=extra.name).exists()
