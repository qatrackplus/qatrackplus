from collections import defaultdict
import io
import json
import math
import token
import tokenize

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.serializers import serialize, deserialize
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


def create_testpack(test_lists=None, cycles=None, extra_tests=None):
    """
    Take input test lists queryset and cycles queryset and generate a test pack from them.  The
    test pack will includ all objects they depend on.
    """

    cycles = cycles or models.TestListCycle.objects.none()

    test_lists = test_lists or models.TestList.objects.none()
    test_lists |= models.TestList.objects.filter(
        pk__in=cycles.values_list("test_lists")
    ).order_by("pk")

    tlc_memberships = models.TestListCycleMembership.objects.filter(cycle=cycles)

    tl_memberships = models.TestListMembership.objects.filter(
        pk__in=test_lists.values_list("testlistmembership")
    )

    tests = models.Test.objects.filter(
        pk__in=tl_memberships.values_list("test")
    )

    tests |= (extra_tests or models.Test.objects.none())


    categories = models.Category.objects.filter(
        pk__in=tests.values_list("category")
    )

    to_dump = [
        categories,
        tests,
        test_lists,
        tl_memberships,
        cycles,
        tlc_memberships
    ]

    objects = []
    for qs in to_dump:
        fields = qs.model.get_test_pack_fields()
        objects.append(
            serialize("json", qs, fields=fields, use_natural_foreign_keys=True, use_natural_primary_keys=True)
        )

    meta = {
        'version': settings.VERSION,
        'datetime': "%s" % timezone.now(),
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

    def include_test(obj):
        if not test_names:
            return True
        return

    modified = created = timezone.now()
    user = user or User.objects.earliest("pk")

    data = json.loads(serialized_pack)
    to_delete = []
    for qs in data['objects']:
        for obj in deserialize("json", qs):

            exclude = (
                (obj.object._meta.model_name == "test" and test_names is not None and obj.object.name not in test_names) or
                (obj.object._meta.model_name == "testlist" and test_list_names is not None and obj.object.name not in test_list_names) or
                (obj.object._meta.model_name == "testlistcycle" and cycle_names is not None and obj.object.name not in cycle_names)
            )

            try:
                existing_obj = obj.object._meta.model.objects.get_by_natural_key(*obj.object.natural_key())
            except obj.object._meta.model.DoesNotExist:
                existing_obj = None

            if exclude and not existing_obj:
                to_delete.append(obj.object)

            if hasattr(obj.object, "created"):
                obj.object.created = created
                obj.object.created_by = user

            if hasattr(obj.object, "modified"):
                obj.object.modified = modified
                obj.object.modified_by = user

            if not existing_obj:
                obj.save()

    for obj in to_delete:
        obj.delete()


def load_test_pack(fp, user=None, test_names=None, test_list_names=None, cycle_names=None):
    """Takes a file like object or path and loads the test pack into the database."""

    if isinstance(fp, str):
        fp = open(fp, 'r', encoding="utf-8")

    add_test_pack(fp.read(), user, test_names, test_list_names, cycle_names)
