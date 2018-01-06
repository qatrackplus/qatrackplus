from collections import Counter, defaultdict
import io
import json
import math
import token
import tokenize

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.serializers import deserialize, serialize
from django.utils import timezone

from qatrack.qa import models


class SetEncoder(json.JSONEncoder):
    """Allow handling of sets as lists"""
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)  # pragma: nocover


def qs_extra_for_utc_name():

    from qatrack.qa import models

    ct_tl = ContentType.objects.get_for_model(models.TestList)
    ct_tlc = ContentType.objects.get_for_model(models.TestListCycle)

    extraq = """
         CASE
            WHEN content_type_id = {0}
                THEN (SELECT name AS utc_name from qa_testlist WHERE object_id = qa_testlist.id )
            WHEN content_type_id = {1}
                THEN (SELECT name AS utc_name from qa_testlistcycle WHERE object_id = qa_testlistcycle.id)
         END
         """.format(ct_tl.pk, ct_tlc.pk)

    return {
        "select": {'utc_name': extraq}
    }


def to_precision(x, p):
    """
    returns a string representation of x formatted with a precision of p

    Based on the webkit javascript implementation taken from here:
    https://code.google.com/p/webkit-mirror/source/browse/JavaScriptCore/kjs/number_object.cpp?spec=svna8bbabb5022b4be3aca68b6807660f51a6a4c7fd&r=a8bbabb5022b4be3aca68b6807660f51a6a4c7fd#338
    """

    x = float(x)

    if x == 0.:
        return "0"

    out = []

    if x < 0:
        out.append("-")
        x = -x

    e = int(math.log10(x))
    tens = math.pow(10, e - p + 1)
    n = math.floor(x / tens)
    if n < math.pow(10, p - 1):
        e = e - 1
        tens = math.pow(10, e - p + 1)
        n = math.floor(x / tens)

    if abs((n + 1.) * tens - x) <= abs(n * tens - x):
        n = n + 1

    if n >= math.pow(10, p):
        n = n / 10.
        e = e + 1

    m = "%.*g" % (p, n)

    if e < -2 or e >= p:
        out.append(m[0])
        if p > 1:
            out.append(".")
            out.extend(m[1:p])
        out.append('e')
        if e > 0:
            out.append("+")
        out.append(str(e))
    elif e == (p - 1):
        out.append(m)
    elif e >= 0:
        out.append(m[:e + 1])
        if e + 1 < len(m):
            out.append(".")
            out.extend(m[e + 1:])
    else:
        out.append("0.")
        out.extend(["0"]*-(e + 1))
        out.append(m)

    return "".join(out)


def tokenize_composite_calc(calc_procedure):
    """tokenize a calculation procedure"""
    tokens = tokenize.generate_tokens(io.StringIO(calc_procedure).readline)
    return [t[token.NAME] for t in tokens if t[token.NAME]]


def unique(seq, idfun=None):
    """f5 from http://www.peterbe.com/plog/uniqifiers-benchmark"""
    # order preserving
    if idfun is None:
        def idfun(x):
            return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        if marker in seen:
            continue
        seen[marker] = 1
        result.append(item)
    return result


def almost_equal(a, b, significant=7):
    """determine if two numbers are nearly equal to significant figures
    copied from numpy.testing.assert_approx_equal
    """
    if a is None or b is None:
        return False

    a, b = float(a), float(b)

    # Normalized the numbers to be in range (-10.0,10.0)
    # scale = float(pow(10,math.floor(math.log10(0.5*(abs(b)+abs(a))))))
    try:
        scale = 0.5 * (abs(b) + abs(a))
        scale = math.pow(10, math.floor(math.log10(scale)))
    except:
        pass

    try:
        sc_b = b / scale
    except ZeroDivisionError:
        sc_b = 0.0
    try:
        sc_a = a / scale
    except ZeroDivisionError:
        sc_a = 0.0

    return abs(sc_b - sc_a) <= math.pow(10., -(significant - 1))


def check_query_count():  # pragma: nocover
    """
    A useful debugging decorator for checking the number of queries a function
    is making
    """

    from django.db import connection
    import time

    def decorator(func):
        if settings.DEBUG:
            def inner(self, *args, **kwargs):
                initial_queries = len(connection.queries)
                t1 = time.time()
                ret = func(self, *args, **kwargs)
                t2 = time.time()
                final_queries = len(connection.queries)
                print("****QUERIES****", final_queries - initial_queries, "in %.3f ms" % (t2 - t1))
                return ret
            return inner
        return func
    return decorator


def create_testpack(test_lists=None, cycles=None, extra_tests=None, description="", user=None, name=""):
    """
    Take input test lists queryset and cycles queryset and generate a test pack from them.  The
    test pack will includ all objects they depend on.
    """

    cycles = cycles or models.TestListCycle.objects.none()

    test_lists = test_lists or models.TestList.objects.none()
    test_lists |= models.TestList.objects.filter(
        pk__in=cycles.values_list("test_lists")
    ).order_by("pk")

    sublists = models.Sublist.objects.filter(
        parent_id__in=test_lists.values_list("id")
    ).select_related("parent", "child")

    test_lists |= models.TestList.objects.filter(pk__in=sublists.values_list("child_id"))

    tlc_memberships = models.TestListCycleMembership.objects.filter(cycle=cycles)

    tl_memberships = models.TestListMembership.objects.filter(
        pk__in=test_lists.values_list("testlistmembership")
    ).select_related("test_list", "test")

    tests = models.Test.objects.filter(
        pk__in=tl_memberships.values_list("test")
    )

    tests |= (extra_tests or models.Test.objects.none())
    tests = tests.select_related("category")

    categories = models.Category.objects.filter(
        pk__in=tests.values_list("category")
    )

    to_dump = [
        categories,
        tests,
        test_lists,
        tl_memberships,
        sublists,
        cycles,
        tlc_memberships
    ]

    objects = []
    indent = 2 if settings.DEBUG else None
    for qs in to_dump:
        fields = qs.model.get_test_pack_fields()
        objects.append(
            serialize("json", qs, fields=fields, use_natural_foreign_keys=True, use_natural_primary_keys=True, indent=indent)
        )

    if user:
        fname = user.get_full_name()
        if fname and user.email:
            user = "%s (%s)" % (fname, user.email)
        elif fname:
            user = fname
        elif user.email:
            user = user.email

    meta = {
        'version': settings.VERSION,
        'datetime': "%s" % timezone.now(),
        'description': description,
        'contact': user,
        'name': name,
    }

    return {'meta': meta, 'objects': objects}


def save_test_pack(pack, fp):
    """
    Write input test pack to file like object fp. If fp is a string it
    will be written to a new file with the name/path given by fp.
    """

    if isinstance(fp, str):
        fp = open(fp, 'w', encoding="utf-8")

    json.dump(pack, fp, indent=2)


def test_pack_object_names(serialized_pack):
    """Look in test pack and return names of test lists & test list cycles"""

    pack = deserialize_pack(serialized_pack)
    names = defaultdict(list)

    for obj in pack['objects']:
        if obj['model'] in ["qa.testlistcycle", "qa.testlist", "qa.test"]:
            display = obj['fields']['name']
            names[obj['model'].replace("qa.", "")].append(display)

    return names


def deserialize_pack(serialized_pack):
    """deserialize test pack data to dictionary"""

    data = json.loads(serialized_pack)
    pack = {'meta': data['meta'], 'objects': []}
    for qs in data['objects']:
        for obj in json.loads(qs):
            pack['objects'].append(obj)
    return pack


def add_test_pack(serialized_pack, user=None, test_names=None, test_list_names=None, cycle_names=None):
    """Takes a serialized data pack and saves the deserialized objects to the db"""

    created = timezone.now()
    user = user or User.objects.earliest("pk")

    added = {}
    total = {}

    data = json.loads(serialized_pack)

    objects = defaultdict(list)
    for obj_set_json in data['objects']:
        objs = json.loads(obj_set_json)
        if objs:
            objects[objs[0]['model']] = objs

    existing = {frozenset(x) for x in models.Category.objects.values_list(*models.Category.NK_FIELDS)}
    categories_added = []
    for cdat in objects['qa.category']:
        fields = cdat['fields']
        nkey = {fields[f] for f in models.Category.NK_FIELDS}
        if nkey not in existing:
            categories_added.append(models.Category(**fields))
    models.Category.objects.bulk_create(categories_added)
    categories = dict((f[1:], f[0]) for f in models.Category.objects.values_list(*(['id'] + models.Category.NK_FIELDS)))
    added['Category'] = len(categories_added)
    total['Category'] = len(objects['qa.category'])

    existing = set(models.Test.objects.values_list('name', flat=True))
    tests_added = []
    test_name_map = {}
    for cdat in objects['qa.test']:
        fields = cdat['fields']
        filtered = test_names is not None and fields['name'] not in test_names

        orig_name = fields['name']
        if fields['name'] in existing:
            valid_name = find_next_available(fields['name'], existing)
        else:
            valid_name = orig_name

        if not filtered:
            fields['name'] = valid_name
            test_name_map[orig_name] = valid_name
            fields['category_id'] = categories[tuple(fields.pop("category"))]
            fields['created'] = created
            fields['created_by'] = user
            fields['modified'] = created
            fields['modified_by'] = user
            tests_added.append(models.Test(**fields))
    models.Test.objects.bulk_create(tests_added)
    added['Test'] = len(tests_added)
    total['Test'] = len(objects['qa.test'])

    existing = set(models.TestList.objects.values_list("slug", flat=True))
    test_lists_added = []
    tl_name_map = {}
    for cdat in objects['qa.testlist']:
        fields = cdat['fields']
        filtered = test_list_names is not None and fields['slug'] not in test_list_names

        orig_name = fields['slug']
        if fields['slug'] in existing:
            valid_name = find_next_available(fields['slug'], existing)
        else:
            valid_name = orig_name

        if not filtered:
            fields['slug'] = valid_name
            tl_name_map[orig_name] = valid_name
            fields['created'] = created
            fields['created_by'] = user
            fields['modified'] = created
            fields['modified_by'] = user
            test_lists_added.append(models.TestList(**fields))
    models.TestList.objects.bulk_create(test_lists_added)
    added['TestList'] = len(test_lists_added)
    total['TestList'] = len(objects['qa.testlist'])

    existing = set(models.TestListCycle.objects.values_list("slug", flat=True))
    tlcs_added = []
    tlc_name_map = {}
    for cdat in objects['qa.testlistcycle']:
        fields = cdat['fields']
        filtered = test_list_names is not None and fields['slug'] not in test_list_names

        orig_name = fields['slug']
        if fields['slug'] in existing:
            valid_name = find_next_available(fields['slug'], existing)
        else:
            valid_name = orig_name

        if not filtered:
            fields['slug'] = valid_name
            tlc_name_map[orig_name] = valid_name
            fields['created'] = created
            fields['created_by'] = user
            fields['modified'] = created
            fields['modified_by'] = user
            tlcs_added.append(models.TestListCycle(**fields))

    models.TestListCycle.objects.bulk_create(tlcs_added)
    added['TestListCycle'] = len(tlcs_added)
    total['TestListCycle'] = len(objects['qa.testlistcycle'])

    tl_slugs = {tl.slug for tl in test_lists_added}
    tl_pks = dict(models.TestList.objects.filter(slug__in=tl_slugs).values_list("slug", "pk"))
    test_names_added = {t.name for t in tests_added}
    test_pks = dict(models.Test.objects.filter(name__in=test_names_added).values_list("name", "pk"))

    tlms_added = []
    for tlm in objects['qa.testlistmembership']:
        fields = tlm['fields']
        if fields['test_list'][0] in tl_name_map:
            fields['test_list_id'] = tl_pks[tl_name_map[fields.pop('test_list')[0]]]
            fields['test_id'] = test_pks[test_name_map[fields.pop('test')[0]]]
            tlms_added.append(models.TestListMembership(**fields))
    models.TestListMembership.objects.bulk_create(tlms_added)

    subs_added = []
    for sub in objects['qa.sublist']:
        fields = sub['fields']
        if fields['parent'][0] in tl_name_map:
            fields['parent_id'] = tl_pks[tl_name_map[fields.pop('parent')[0]]]
            fields['child_id'] = tl_pks[tl_name_map[fields.pop('child')[0]]]
            subs_added.append(models.Sublist(**fields))
    models.Sublist.objects.bulk_create(subs_added)

    tlcms_added = []
    tlc_slugs = {tlc.slug for tlc in tlcs_added}

    tlc_pks = dict(models.TestListCycle.objects.filter(slug__in=tlc_slugs).values_list("slug", "pk"))
    for tlcm in objects['qa.testlistcyclemembership']:
        fields = tlcm['fields']
        if fields['cycle'][0] in tlc_name_map:
            fields['test_list_id'] = tl_pks[tl_name_map[fields.pop('test_list')[0]]]
            fields['cycle_id'] = tlc_pks[tlc_name_map[fields.pop('cycle')[0]]]
            tlcms_added.append(models.TestListCycleMembership(**fields))
    models.TestListCycleMembership.objects.bulk_create(tlcms_added)

    return added, total

def find_next_available(name, existing):
    i = 1
    orig = name
    while name in existing:
        name = "%s-%d" % (orig, i)
        i += 1
    return name


def add_test_pack_django(serialized_pack, user=None, test_names=None, test_list_names=None, cycle_names=None):
    """
    Takes a serialized data pack and saves the deserialized objects to the db

    This is a much less efficient, but much simpler version of add_test_pack
    """

    modified = created = timezone.now()
    user = user or User.objects.earliest("pk")

    added = Counter()
    total = Counter()

    data = json.loads(serialized_pack)

    for qs in data['objects']:
        to_add = []

        for obj in deserialize("json", qs):
            total[obj.object._meta.model_name] += 1
            if obj.object.pk:
                continue
            mname = obj.object._meta.model_name
            filtered = (
                (mname == "test" and test_names is not None and obj.object.name not in test_names) or
                (mname == "testlist" and test_list_names is not None and obj.object.name not in test_list_names) or
                (mname == "testlistcycle" and cycle_names is not None and obj.object.name not in cycle_names)
            )
            if filtered:
                continue

            if hasattr(obj.object, "created"):
                obj.object.created = created
                obj.object.created_by = user

            if hasattr(obj.object, "modified"):
                obj.object.modified = modified
                obj.object.modified_by = user

            to_add.append(obj.object)
            added[obj.object._meta.model_name] += 1

        if to_add:
            Model = to_add[0]._meta.model
            Model.objects.bulk_create(to_add)

    return added, total


def load_test_pack(fp, user=None, test_names=None, test_list_names=None, cycle_names=None):
    """Takes a file like object or path and loads the test pack into the database."""

    if isinstance(fp, str):
        fp = open(fp, 'r', encoding="utf-8")

    add_test_pack(fp.read(), user, test_names, test_list_names, cycle_names)
