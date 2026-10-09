"""Translate one date/time format into the dialects QATrack+ has to speak.

The same format has to be expressed four different ways: Python's strptime
syntax for parsing, Django's template syntax for rendering server side,
flatpickr's for the date pickers, and moment.js's for the rest of the
browser-side formatting. Historically each was written out by hand in
qatrack/formats/<lang>/formats.py, which is how they drifted apart - the
datetime picker wrote ``Y-m-d H:i`` while the date picker wrote ``d M Y`` and
the moment format was different again.

Writing the format once in strptime syntax and deriving the rest keeps them
from disagreeing. strptime is the source dialect because it is the one that
has to be exactly right: it is what parses user input, and a wrong token there
rejects data rather than merely displaying it oddly.

Only the tokens QATrack+ actually uses are mapped. An unmapped ``%X`` raises
rather than silently emitting something wrong - a format that is wrong in the
browser but right on the server is the kind of bug that takes a day to find.
"""

# strptime -> Django template date format
# https://docs.djangoproject.com/en/4.2/ref/templates/builtins/#date
_DJANGO = {
    'Y': 'Y', 'y': 'y', 'm': 'm', 'b': 'M', 'B': 'F', 'd': 'd', 'j': 'z',
    'H': 'H', 'I': 'h', 'M': 'i', 'S': 's', 'p': 'A', 'f': 'u', 'z': 'O',
    'a': 'D', 'A': 'l', '%': '%',
}

# strptime -> flatpickr
# https://flatpickr.js.org/formatting/
_FLATPICKR = {
    'Y': 'Y', 'y': 'y', 'm': 'm', 'b': 'M', 'B': 'F', 'd': 'd', 'j': 'j',
    'H': 'H', 'I': 'h', 'M': 'i', 'S': 'S', 'p': 'K',
    'a': 'D', 'A': 'l', '%': '%',
}

# strptime -> moment.js
# https://momentjs.com/docs/#/displaying/format/
_MOMENT = {
    'Y': 'YYYY', 'y': 'YY', 'm': 'MM', 'b': 'MMM', 'B': 'MMMM', 'd': 'DD',
    'j': 'DDDD', 'H': 'HH', 'I': 'hh', 'M': 'mm', 'S': 'ss', 'p': 'A',
    'f': 'SSSSSS', 'z': 'ZZ', 'a': 'ddd', 'A': 'dddd', '%': '%',
}


class UnsupportedFormat(ValueError):
    """A strptime format used a directive QATrack+ cannot translate."""


def _translate(fmt, table, dialect, escape):
    out = []
    i = 0
    while i < len(fmt):
        char = fmt[i]
        if char != '%':
            out.append(escape(char))
            i += 1
            continue

        if i + 1 >= len(fmt):
            raise UnsupportedFormat("%r ends with a bare '%%'" % fmt)

        directive = fmt[i + 1]
        if directive not in table:
            raise UnsupportedFormat(
                "%%%s is not translatable to %s. Supported directives are: %s"
                % (directive, dialect, ', '.join('%' + k for k in sorted(table)))
            )
        out.append(table[directive])
        i += 2

    return ''.join(out)


def _escape_django(char):
    # Django renders any alphabetic character as a format specifier unless it
    # is backslash escaped, so a literal "T" in a format would silently become
    # the timezone offset.
    return '\\' + char if char.isalpha() else char


def _escape_flatpickr(char):
    return '\\' + char if char.isalpha() else char


def _escape_moment(char):
    # moment takes literals in square brackets rather than escaped.
    return '[' + char + ']' if char.isalpha() else char


def to_django(fmt):
    """``'%Y-%m-%d %H:%M'`` -> ``'Y-m-d H:i'``"""
    return _translate(fmt, _DJANGO, 'a Django template format', _escape_django)


def to_flatpickr(fmt):
    """``'%Y-%m-%d %H:%M'`` -> ``'Y-m-d H:i'``"""
    return _translate(fmt, _FLATPICKR, 'a flatpickr format', _escape_flatpickr)


def to_moment(fmt):
    """``'%Y-%m-%d %H:%M'`` -> ``'YYYY-MM-DD HH:mm'``"""
    return _translate(fmt, _MOMENT, 'a moment.js format', _escape_moment)


def describe(fmt):
    """A human readable rendering of ``fmt``, for form help text.

    ``'%Y-%m-%d %H:%M'`` -> ``'YYYY-MM-DD hh:mm'``. This is what a deployer
    sees underneath a date field, so it follows the convention people expect
    in help text rather than any one library's tokens.
    """
    human = {
        'Y': 'YYYY', 'y': 'YY', 'm': 'MM', 'b': 'MMM', 'B': 'MMMM', 'd': 'DD',
        'j': 'DDD', 'H': 'hh', 'I': 'hh', 'M': 'mm', 'S': 'ss', 'p': 'AM/PM',
        'f': 'ffffff', 'z': 'ZZ', 'a': 'ddd', 'A': 'dddd', '%': '%',
    }
    return _translate(fmt, human, 'a human readable description', lambda c: c)
