import io
import os

from PIL import Image
import imageio
from matplotlib.figure import Figure
import pydicom


def imsave(obj, fname):

    def reseek(obj, data):
        try:
            obj.seek(0)
        except:
            pass
        try:
            data.seek(0)
        except:
            pass

    fmt = os.path.splitext(fname)[-1].strip('.')
    data = io.BytesIO()
    try:
        imageio.imwrite(data, obj, format=fmt)
        reseek(obj, data)
        return data.read()
    except:
        reseek(obj, data)

    try:
        im = Image.open(obj)
        im.save(data, format=fmt)
        reseek(obj, data)
        return data.read()
    except:
        reseek(obj, data)

    try:
        try:
            pixels = obj.pixel_array
        except AttributeError:
            pixels = pydicom.read_file(obj, force=True).pixel_array
        imageio.imwrite(data, pixels, format=fmt)
        reseek(obj, data)
        return data.read()
    except:
        reseek(obj, data)


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

    if hasattr(obj, "read"):
        # read from file like objects for handling bytes/string below
        if hasattr(obj, "seek"):
            obj.seek(0)
        obj = obj.read()

    if isinstance(obj, bytes):
        return obj

    if isinstance(obj, str):
        return bytes(obj, "UTF-8")

    # numpy array
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
