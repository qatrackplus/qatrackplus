import io
import json
import math
import token
import tokenize

from django.conf import settings
from django.db.transaction import atomic


class SetEncoder(json.JSONEncoder):
    """Allow handling of sets as lists"""
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)  # pragma: nocover


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
        out.extend(["0"] * -(e + 1))
        out.append(m)

    return "".join(out)


def tokenize_composite_calc(calc_procedure):
    """tokenize a calculation procedure"""
    all_tokens = tokenize.generate_tokens(io.StringIO(calc_procedure).readline)
    tokens = []
    prev = None
    for t in all_tokens:
        val = t[token.NAME]
        if not val:
            prev = val
            continue
        if prev != ".":
            tokens.append(val)
        prev = val
    return tokens


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
    except:  # noqa: E722
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


def get_bool_tols(user_klass=None, tol_klass=None):

    from qatrack.qa import models
    from qatrack.accounts.models import get_internal_user
    user_klass = user_klass or models.User
    tol_klass = tol_klass or models.Tolerance
    user = get_internal_user(user_klass)

    warn, __ = tol_klass.objects.get_or_create(
        type=models.BOOLEAN,
        bool_warning_only=True,
        created_by=user,
        modified_by=user
    )
    act, __ = tol_klass.objects.get_or_create(
        type=models.BOOLEAN,
        bool_warning_only=False,
        created_by=user,
        modified_by=user
    )
    return warn, act


def format_qc_value(val, format_str, _try_default=True):
    """Format a value with given format_str first by trying old style "<foo>" %
    (*args)" and then trying new "<foo>".format(*args) style. If both of those
    methods fail, then we try using settings.DEFAULT_NUMBER_FORMAT before
    falling back to using to_precision and settings.CONSTANT_PRECISION.  If
    that also fails, just return  str(val).  """

    if format_str:
        try:
            return format_str % val
        except TypeError as e:
            old_style_likely = "number is required" in str(e)
            if not old_style_likely:
                try:
                    return format_str.format(val)
                except:  # noqa: E722
                    pass
        except:  # noqa: E722
            pass

    if _try_default and settings.DEFAULT_NUMBER_FORMAT:
        try:
            return format_qc_value(val, settings.DEFAULT_NUMBER_FORMAT, _try_default=False)
        except:  # noqa: E722
            pass

    try:
        # try fall back on old behaviour
        return to_precision(val, settings.CONSTANT_PRECISION)
    except:  # noqa: E722
        pass

    return str(val)


@atomic
def copy_unit_config(from_unit, to_unit):
    """
    This function will copy all UnitTestCollection and reference and tolerances
    from `from_unit` to `to_unit`. If the same TestList(Cycle) is already
    assigned to the to_unit, that assignment is skipped.  Likewise, if a given
    UnitTestInfo already exists on the to_unit, the reference and tolerance
    values won't be updated.
    """

    from qatrack.qa.models import UnitTestCollection, UnitTestInfo

    existing = list(UnitTestCollection.objects.filter(unit=to_unit).values_list("content_type_id", "object_id"))
    existing_utis = list(UnitTestInfo.objects.filter(unit=to_unit).values_list("test_id", flat=True))
    from_utcs = UnitTestCollection.objects.filter(unit=from_unit)

    for utc in from_utcs:
        if (utc.content_type_id, utc.object_id) in existing:
            continue
        visible_to = list(utc.visible_to.all())
        utc.pk = None
        utc.unit = to_unit
        utc.last_instance = None
        utc.due_date = None
        utc.save()

        for vt in visible_to:
            utc.visible_to.add(vt)

        for day in range(len(utc.tests_object)):
            __, tl = utc.get_list(day=day)
            for t in tl.ordered_tests():

                uti_old = UnitTestInfo.objects.get(unit=from_unit, test=t)
                if t.id in existing_utis:
                    continue

                uti_new = UnitTestInfo.objects.get(unit=to_unit, test=t)
                uti_new.reference = uti_old.reference
                uti_new.tolerance = uti_old.tolerance
                uti_new.save()
