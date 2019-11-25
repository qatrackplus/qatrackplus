from django.test import TestCase
from django.utils.text import slugify

from qatrack.qa.models import Category
from qatrack.qa.tests import utils
from qatrack.qatrack_core.views import category_tree, units_with_categories
from qatrack.units.models import Site


class TestLoginViews(TestCase):

    def setUp(self):

        self.cats = [
            ('A', None),
            ('B', None),
            ('C', None),
            ('B1', 'B'),
            ('B2', 'B'),
            ('C1', 'C'),
            ('C2', 'C'),
            ('C21', 'C2'),
            ('C22', 'C2'),
            ('C211', 'C21'),
        ]

        s = Site.objects.create(name="site1")

        unit1 = utils.create_unit(name="unit1", number=1, site=s)
        unit2 = utils.create_unit(name="unit2", number=2)
        for cat_name, parent in self.cats:
            cat = Category.objects.create(
                name=cat_name,
                slug=slugify(cat_name),
                parent=Category.objects.filter(name=parent).first(),
            )
            test = utils.create_test(cat_name, category=cat)
            utils.create_unit_test_info(test=test, unit=unit1)
            utils.create_unit_test_info(test=test, unit=unit2)

    def test_units_with_categories(self):
        unit_cats = units_with_categories()
        assert len(unit_cats) == len(self.cats)
        for cat_id, units in unit_cats.items():
            assert units == [(None, 'unit2', 2), ('site1', 'unit1', 1)]

    def test_empty_tree(self):
        cats = category_tree({})

        expected = [{
            'text': 'QC by Category <i class="fa fa-tags fa-fw"></i>',
            'nodes': [],
            'state': {
                'expanded': 0
            },
        }]

        assert cats == expected

    def test_full_tree(self):
        tree = category_tree(units_with_categories())
        assert len(tree) == 1  # should only be one top level node
        root_nodes = tree[0]['nodes']
        assert len(root_nodes) == 3  # A, B, C
        c_nodes = root_nodes[-1]
        assert len(c_nodes) == 3
        assert c_nodes['text'].startswith("C ")
        assert c_nodes['nodes'][0]['text'].startswith("C ")
        assert c_nodes['nodes'][1]['text'].startswith("C1 ")
        assert c_nodes['nodes'][2]['text'].startswith("C2 ")
