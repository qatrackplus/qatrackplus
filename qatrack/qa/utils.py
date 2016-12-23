import json
import math
import io
import os
import tokenize
import token

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from matplotlib.figure import Figure
import scipy.misc


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
    """ A useful debugging decorator for checking the number of queries
    a function is making"""

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


def imsave(obj, fname):

    fmt = os.path.splitext(fname)[-1].strip('.')
    data = io.BytesIO()
    try:
        scipy.misc.imsave(data, obj, format=fmt)
        data.seek(0)
        return data.read()
    except:
        pass


def figure_to_bytes(obj, fname):
    fmt = os.path.splitext(fname)[-1].strip('.')
    if fmt not in ["png", "pdf", "ps", "eps", "svg"]:
        fmt = "png"

    dat = io.BytesIO()
    obj.savefig(dat, format=fmt)
    dat.seek(0)
    return dat.read()


def get_mpl_figure(obj):

    if isinstance(obj, Figure):
        return obj

    if hasattr(obj, "figure") and isinstance(obj.figure, Figure):
        # mpl plot, canvas, axes etc
        return obj.figure
    else:
        try:
            # sometimes mpl returns array of patches which we can get figure from
            return obj[0].figure
        except (TypeError, IndexError, AttributeError):
            pass


    if hasattr(obj, "gcf"):
        try:
            cf = obj.gcf()
            if isinstance(cf, Figure):
                return cf
        except TypeError:
            pass

    if hasattr(obj, "gca"):
        try:
            ca = obj.gca()
            if hasattr(ca, "figure") and isinstance(ca.figure, Figure):
                return ca.figure
        except TypeError:
            pass


def to_bytes(obj, fname=None):

    if isinstance(obj, bytes):
        return obj

    if isinstance(obj, str):
        return bytes(obj, "UTF-8")

    if hasattr(obj, "tobytes"):
        return obj.tobytes()

    mpl_fig = get_mpl_figure(obj)
    if mpl_fig:
        return figure_to_bytes(mpl_fig, fname)

    try:
        return bytes(obj)
    except TypeError:
        pass

    return bytes()


