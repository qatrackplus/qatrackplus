"""Read and write date strings the way the browser does.

flatpickr and moment cannot run under pytest. These helpers turn the formats the page
actually sends to the browser (``siteConfig``) back into strptime, so a test can check
that what the server writes the browser reads, and what the browser writes the server
reads, without a browser.
"""
import datetime
import re

from qatrack.qatrack_core import dateformats

_DIRECTIVES = 'YymbBdHIMSpaA'
_FLATPICKR = {dateformats.to_flatpickr('%' + d): d for d in _DIRECTIVES}
# longest first, so MMMM is not read as MM + MM
_MOMENT = sorted(((dateformats.to_moment('%' + d), d) for d in _DIRECTIVES), key=lambda kv: -len(kv[0]))

SITE_CONFIG_FORMATS = [
    'MOMENT_DATE_DATA_FMT', 'MOMENT_DATE_FMT', 'MOMENT_DATETIME_FMT',
    'FLATPICKR_DATE_FMT', 'FLATPICKR_DATETIME_FMT', 'DATERANGEPICKER_DATE_FMT',
]


def site_config(html):
    """The siteConfig format strings in a rendered page, decoded as JavaScript decodes them."""
    out = {}
    for key in SITE_CONFIG_FORMATS:
        raw = re.search(r"%s: '((?:[^'\\]|\\.)*)'" % key, html).group(1)
        # one pass, as JavaScript does: \uXXXX is a character, any other \x is just x
        out[key] = re.sub(r"\\(u[0-9a-fA-F]{4}|.)",
                          lambda m: chr(int(m.group(1)[1:], 16)) if len(m.group(1)) == 5 else m.group(1), raw)
    return out


def flatpickr_to_strptime(fmt):
    out, i = [], 0
    while i < len(fmt):
        c = fmt[i]
        if c == '\\' and i + 1 < len(fmt):
            out.append(fmt[i + 1])
            i += 2
        else:
            out.append('%' + _FLATPICKR[c] if c in _FLATPICKR else c)
            i += 1
    return ''.join(out)


def moment_to_strptime(fmt):
    out, i = [], 0
    while i < len(fmt):
        if fmt[i] == '[':
            j = fmt.index(']', i)
            out.append(fmt[i + 1:j])
            i = j + 1
            continue
        for token, directive in _MOMENT:
            if fmt.startswith(token, i):
                out.append('%' + directive)
                i += len(token)
                break
        else:
            out.append(fmt[i])
            i += 1
    return ''.join(out)


def _strptime(fmt_for_strptime, browser_fmt):
    def read(text):
        try:
            return datetime.datetime.strptime(text, fmt_for_strptime)
        except (ValueError, TypeError):
            raise AssertionError(
                "the server wrote %r, which the browser (format %r) cannot read; a date picker "
                "would silently replace it with a different date" % (text, browser_fmt))
    return read


def read_flatpickr(text, fmt):
    return _strptime(flatpickr_to_strptime(fmt), fmt)(text)


def read_moment(text, fmt):
    return _strptime(moment_to_strptime(fmt), fmt)(text)


def write_flatpickr(value, fmt):
    return value.strftime(flatpickr_to_strptime(fmt))


def write_moment(value, fmt):
    return value.strftime(moment_to_strptime(fmt))
