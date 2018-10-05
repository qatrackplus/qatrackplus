from collections import Counter, defaultdict
import json
import time
import uuid

from django.conf import settings
from django.core.serializers import get_serializer
from django.db.transaction import atomic
from django.utils import timezone
import pytest

from qatrack.qa.utils import get_internal_user

pytestmark = pytest.mark.skip("This file doesn't actually have tests")


def get_model_map():
    """wrap in function to prevent circular import"""

    from qatrack.qa import models

    return {
        'qa.test': models.Test,
        'qa.category': models.Category,
        'qa.testlist': models.TestList,
        'qa.testlistcycle': models.TestListCycle,
        'qa.testlistmembership': models.TestListMembership,
        'qa.testlistcyclemembership': models.TestListCycleMembership,
        'qa.sublist': models.Sublist,
    }


class TestPackMixin:

    def to_testpack(self):
        s = get_serializer("json")()
        to_serialize = list(self.get_testpack_dependencies())
        dependencies = []
        kwargs = {"use_natural_foreign_keys": True, "use_natural_primary_keys": True}
        for model, qs in to_serialize:
            dependencies += json.loads(s.serialize(qs, fields=model.get_testpack_fields(), **kwargs))
        fields = json.loads(s.serialize([self], fields=self._meta.model.get_testpack_fields(), **kwargs))[0]
        return json.dumps({'key': self.natural_key(), 'object': fields, 'dependencies': dependencies})

    def get_testpack_dependencies(self):  # pragma: no cover
        raise NotImplementedError

    def get_testpack_fields(cls):  # pragma: no cover
        raise NotImplementedError


def create_testpack(test_lists=None, cycles=None, extra_tests=None, description="", user=None, name="", timeout=0):
    """
    Take input test lists queryset and cycles queryset and generate a test pack from them.  The
    test pack will includ all objects they depend on.
    """

    from qatrack.qa import models

    user = user or get_internal_user()
    testpack = {
        'objects': {
            'tests': [],
            'testlists': [],
            'testlistcycles': [],
        },
        'meta': {
            'version': settings.VERSION,
            'datetime': "%s" % (timezone.now().astimezone(timezone.utc)),
            'description': description,
            'contact': testpack_user_string(user),
            'name': name,
            'id': str(uuid.uuid4()),
        },
    }

    tests = (extra_tests or models.Test.objects.none()).select_related("category")
    test_lists = (test_lists or models.TestList.objects.none())
    cycles = cycles or models.TestListCycle.objects.none()

    t0 = time.time()

    def check_timeout():
        delta = time.time() - t0
        if timeout and timeout > 0 and delta > timeout:
            raise RuntimeError(
                "Sorry, exporting your TestPack timed out in %ds. Please reduce the "
                "number of objects in the TestPack and try again" % (int(delta))
            )

    for t in tests:
        testpack['objects']['tests'].append(t.to_testpack())
        check_timeout()

    for tl in test_lists:
        testpack['objects']['testlists'].append(tl.to_testpack())
        check_timeout()

    for c in cycles:
        testpack['objects']['testlists'].append(c.to_testpack())
        check_timeout()

    return testpack


def testpack_user_string(user):  # pragma: no cover
    """User string for testpack output"""

    fname = user.get_full_name()
    if fname and user.email:
        user = "%s (%s)" % (fname, user.email)
    elif fname:
        user = fname
    elif user.email:
        user = user.email
    else:
        user = user.username

    return user


def save_testpack(pack, fp):
    """
    Write input test pack to file like object fp. If fp is a string it
    will be written to a new file with the name/path given by fp.
    """

    if isinstance(fp, str):  # pragma: no cover
        fp = open(fp, 'w', encoding="utf-8")

    json.dump(pack, fp, indent=2)


@atomic
def add_testpack(serialized_pack, user=None, test_keys=None, test_list_keys=None, cycle_keys=None):
    """
    Takes a serialized data pack and saves the deserialized objects to the db.

    """

    from qatrack.qa import models

    created = timezone.now()
    user = user or get_internal_user()

    # track # of objects added and total number of objects in testpack
    added = Counter()
    total = Counter()

    testpack = json.loads(serialized_pack)

    model_map = get_model_map()

    model_key_include_map = {
        'tests': list(map(tuple, test_keys)) if test_keys is not None else None,
        'testlists': list(map(tuple, test_list_keys)) if test_list_keys is not None else None,
        'testlistcycles': list(map(tuple, cycle_keys)) if cycle_keys is not None else None,
    }

    # this section deserialized all objects from the testpack, and populates
    # to_import with those objects which the user has requested be created
    to_import = defaultdict(list)
    for model in ['tests', 'testlists', 'testlistcycles']:

        for objects in testpack['objects'][model]:

            data = json.loads(objects)  # deserialize the object and its dependencies

            keys_to_include = model_key_include_map[model]
            include_all = keys_to_include is None
            include = include_all or tuple(data['key']) in keys_to_include
            if include:
                to_import[data['object']['model']].append(data['object']['fields'])
                for dep in data['dependencies']:
                    to_import[dep['model']].append(dep['fields'])

            added[model] += include
            total[model] += 1

    # this section looks for natural key conflicts that may occur for the
    # models. Note Categories are handled separately below as we can just reuse
    # existing categories
    nk_lookups = defaultdict(dict)
    for model_name in ['qa.test', 'qa.testlist', 'qa.testlistcycle']:
        model = model_map[model_name]
        existing = frozenset(model.objects.values_list(*model.NK_FIELDS))
        for obj in to_import[model_name]:
            nk_vals = tuple(obj[k] for k in model.NK_FIELDS)
            unique_nk_vals = find_next_available(nk_vals, existing)
            nk_lookups[model_name][nk_vals] = unique_nk_vals

    # populate categories lookup with Category objects for assigning to Tests below
    categories = {}
    for obj in to_import['qa.category']:
        nk_vals = tuple(obj[k] for k in models.Category.NK_FIELDS)
        try:
            categories[nk_vals] = models.Category.objects.get_by_natural_key(*nk_vals)
        except models.Category.DoesNotExist:
            categories[nk_vals] = models.Category.objects.create(**obj)

    # we cann= now create the actual primary records (m2m relationships done below
    extra_kwargs = {'created': created, 'modified': created, 'created_by': user, 'modified_by': user}
    for model_name in ['qa.test', 'qa.testlist', 'qa.testlistcycle']:

        seen = set()
        to_create = []

        model = model_map[model_name]

        for obj in to_import[model_name]:

            # some objects might be duplicated (e.g. test belonging to multiple
            # test lists). Skip the object if we've already seen it
            nk_vals = tuple(obj[k] for k in model.NK_FIELDS)
            if nk_vals in seen:  # pragma: no cover
                continue
            seen.add(nk_vals)

            # test is the only object with an extra fk
            if model_name == "qa.test":
                obj['category'] = categories[tuple(obj['category'])]

            # add extra kwargs and fix natural key conflicts
            obj.update(extra_kwargs)
            obj.update(dict(zip(model.NK_FIELDS, nk_lookups[model_name][nk_vals])))
            to_create.append(model(**obj))

        model.objects.bulk_create(to_create)

    # create mapping of natural keys (including freshly created) to object ids
    test_lists = models.TestList.objects.values_list("id", *models.TestList.NK_FIELDS)
    test_lists = {tuple(f[1:]): f[0] for f in test_lists}
    tests = models.Test.objects.values_list("id", *models.Test.NK_FIELDS)
    tests = {tuple(f[1:]): f[0] for f in tests}
    cycles = models.TestListCycle.objects.values_list("id", *models.TestListCycle.NK_FIELDS)
    cycles = {tuple(f[1:]): f[0] for f in cycles}

    m2ms = [
        ('qa.sublist', 'parent', 'qa.testlist', test_lists, 'child', 'qa.testlist', test_lists),
        ('qa.testlistmembership', 'test_list', 'qa.testlist', test_lists, 'test', 'qa.test', tests),
        ('qa.testlistcyclemembership', 'cycle', 'qa.testlistcycle', cycles, 'test_list', 'qa.testlist', test_lists),
    ]

    for mname, parent_attr, parent_model, parent_objs, child_attr, child_model, child_objs in m2ms:

        to_create = []
        model = model_map[mname]

        for obj in to_import[mname]:

            # keys used to lookup FK object ids
            parent_key = nk_lookups[parent_model][tuple(obj[parent_attr])]
            child_key = nk_lookups[child_model][tuple(obj[child_attr])]

            # use the fk__id  attributes rather than the fk attribute itself
            obj['%s_id' % parent_attr] = parent_objs[parent_key]
            obj['%s_id' % child_attr] = child_objs[child_key]
            del obj[parent_attr]
            del obj[child_attr]

            to_create.append(model(**obj))

        model.objects.bulk_create(to_create)

    return added, total


def find_next_available(fields, existing):
    """iterate until a fields does not conflic with an item in existing"""
    i = 1
    orig = tuple(fields)
    while fields in existing:
        fields = tuple("%s-%d" % (f, i) for f in orig)
        i += 1
    return tuple(fields)


def load_testpack(fp, user=None, test_keys=None, test_list_keys=None, cycle_keys=None):
    """Takes a file like object or path and loads the test pack into the database."""

    if isinstance(fp, str):  # pragma: no cover
        fp = open(fp, 'r', encoding="utf-8")

    add_testpack(fp.read(), user, test_keys, test_list_keys, cycle_keys)
