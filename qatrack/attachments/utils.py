import io
import os

from matplotlib.figure import Figure
import scipy.misc



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
    if mpl_fig and fname:
        return figure_to_bytes(mpl_fig, fname)

    try:
        return bytes(obj)
    except TypeError:
        pass

    return bytes()
