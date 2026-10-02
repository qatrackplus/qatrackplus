"""Guard against numpy APIs that numpy 2.0 removed.

QATrack+ pins ``numpy<2.0`` and that is deliberate - the pin is not what this
file is about. The problem it addresses is that nothing stops a deprecated name
being *added*, because the suite does not turn ``DeprecationWarning`` into an
error (``setup.cfg``), so a removed-in-2.0 alias keeps working silently for as
long as the pin holds and surfaces only on the day someone lifts it.

That is how a version bump turns into a pile of unrelated fixes. Each one of
these is a two-character change when it is written and an archaeology exercise a
year later, so they are caught here instead.

Asserted statically rather than by exercising the code, because most of these
names have no caller the suite reaches: ``np.NaN`` sat in
``leastsquaresfit.gauss_pdf`` behind a guard no test triggers, which is why it
survived four years.
"""

import os
import re

from django.conf import settings

# Names numpy 2.0 removed outright. The expired aliases are the common ones -
# np.float_, np.NaN and friends - and the rest are functions that were renamed
# or folded into another API.
REMOVED_IN_NUMPY_2 = [
    # expired aliases for scalar types
    'float_', 'complex_', 'unicode_', 'string_', 'object_', 'int0', 'uint0',
    'bool8', 'Bytes0', 'Str0', 'Datetime64', 'Uint32',
    # expired constants
    'NaN', 'NAN', 'Inf', 'Infinity', 'infty', 'NINF', 'PINF',
    # renamed or removed functions
    'alltrue', 'sometrue', 'cumproduct', 'product', 'round_', 'in1d', 'msort',
    'row_stack', 'trapz', 'find_common_type', 'issctype', 'set_string_function',
    'asfarray', 'byte_bounds', 'cast', 'source', 'lookfor', 'who', 'disp',
    'safe_eval', 'recfromcsv', 'deprecate', 'mat', 'add_newdoc',
    'fastCopyAndTranspose', 'get_array_wrap', 'maximum_sctype', 'issubsctype',
    'set_numeric_ops', 'compare_chararrays',
]

REPLACEMENTS = {
    'float_': 'np.float64',
    'complex_': 'np.complex128',
    'NaN': 'np.nan',
    'NAN': 'np.nan',
    'Inf': 'np.inf',
    'Infinity': 'np.inf',
    'infty': 'np.inf',
    'NINF': '-np.inf',
    'PINF': 'np.inf',
    'alltrue': 'np.all',
    'sometrue': 'np.any',
    'cumproduct': 'np.cumprod',
    'product': 'np.prod',
    'round_': 'np.round',
    'in1d': 'np.isin',
    'row_stack': 'np.vstack',
    'trapz': 'np.trapezoid',
    'asfarray': 'np.asarray(x, dtype=float)',
}

FORBIDDEN = re.compile(
    r'\b(?:np|numpy)\.(%s)\b' % '|'.join(REMOVED_IN_NUMPY_2)
)


def _strip_comment(line):
    """Everything before the first ``#``.

    Crude on purpose. A ``#`` inside a string literal truncates the line early,
    which can only ever hide a match, and the names here appear in code far more
    often than in strings. The reason to strip at all is that the two fixes this
    file came with explain themselves in comments that name what they replaced.
    """
    return line.split('#', 1)[0]


def _source_files():
    root = settings.PROJECT_ROOT
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in ('migrations', '__pycache__', 'south_migrations', 'static')
        ]
        for name in filenames:
            if name.endswith('.py') and name != os.path.basename(__file__):
                yield os.path.join(dirpath, name)


class TestNoRemovedNumpyApis:
    """No numpy name that 2.0 removed appears in qatrack/.

    Migrations are excluded: they are a historical record and are not rerun
    against a new numpy in any way that would reach this code.
    """

    def test_no_source_file_uses_an_api_numpy_2_removed(self):
        offenders = []
        for path in _source_files():
            with open(path, encoding='utf-8') as f:
                for n, line in enumerate(f, 1):
                    for name in FORBIDDEN.findall(_strip_comment(line)):
                        rel = os.path.relpath(path, settings.BASE_DIR)
                        hint = REPLACEMENTS.get(name, 'see the numpy 2 migration guide')
                        offenders.append('%s:%d uses np.%s - use %s' % (rel, n, name, hint))

        assert not offenders, (
            "numpy 2.0 removed these, and the pin on numpy<2.0 is the only reason "
            "they still work:\n  " + "\n  ".join(offenders)
        )

    def test_the_guard_can_actually_see_an_offender(self):
        """A negative control: a scan that matches nothing proves nothing."""
        assert FORBIDDEN.findall('    return np.NaN') == ['NaN']
        assert FORBIDDEN.findall('np.float_,') == ['float_']
        assert FORBIDDEN.findall('np.float64, np.nan, np.prod') == []

    def test_comments_may_name_what_they_replaced(self):
        """Both fixes explain themselves by naming the removed alias."""
        assert FORBIDDEN.findall(_strip_comment('x = 1  # np.NaN was here')) == []
        assert FORBIDDEN.findall(_strip_comment('# np.float_ was an alias')) == []
