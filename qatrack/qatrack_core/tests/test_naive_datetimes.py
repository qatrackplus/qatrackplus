"""Production code must not read the clock without saying which zone it means.

`datetime.now()` and `date.today()` return the *machine's* wall time. Django
points the process at `settings.TIME_ZONE` only where `time.tzset` exists, and
it deliberately does not on Windows - its own comment in `django/conf` says
"breaks Windows". So on a Windows site whose machine zone differs from
`TIME_ZONE`, every one of these calls was quietly reading the wrong clock, and
the symptom was a plausible-looking local time attached to the wrong instant:

- `qa/views/review.py` stamped a review with `make_aware(datetime.now(), ...)`,
  which takes the machine's wall time and labels it with the site's zone. Two
  zones apart is a review two hours wrong. It also resolved a repeated hour to
  the first occurrence without saying so.
- the service-log up-time report took `datetime.now().date()` as its open end,
  so the report covered the wrong day either side of midnight.
- `backup_site` named its dated folder, and measured its retention window, from
  the machine's date.

`timezone.now()`, `timezone.localtime()` and `timezone.localdate()` are correct
on every platform, and `fromtimestamp()` needs an explicit `tz` because an
epoch instant has no zone of its own.

This is a guard rather than three behavioural tests on purpose: the failure only
appears where the machine's zone differs from the site's, which is not something
this suite can arrange on the platform it runs on, and the defect is a *pattern*
that is easy to reintroduce by copying a neighbouring line.
"""

import pathlib
import re

QATRACK = pathlib.Path(__file__).resolve().parents[2]

# The last of these allows `fromtimestamp(x, tz)` and rejects `fromtimestamp(x)`.
FORBIDDEN = {
    'datetime.now()': re.compile(r'\bdatetime\.now\(\s*\)'),
    'datetime.today()': re.compile(r'\bdatetime\.today\(\s*\)'),
    'date.today()': re.compile(r'\bdate\.today\(\s*\)'),
    'utcnow()': re.compile(r'\butcnow\(\s*\)'),
    'utcfromtimestamp()': re.compile(r'\butcfromtimestamp\('),
    'fromtimestamp() with no tz': re.compile(
        r'fromtimestamp\(\s*[^,()]*(?:\([^()]*\))?[^,()]*\)'
    ),
}

REPLACEMENTS = {
    'datetime.now()': 'timezone.now()',
    'datetime.today()': 'timezone.localdate()',
    'date.today()': 'timezone.localdate()',
    'utcnow()': 'timezone.now()',
    'utcfromtimestamp()': 'datetime.fromtimestamp(ts, datetime.UTC)',
    'fromtimestamp() with no tz': 'fromtimestamp(ts, datetime.UTC)',
}

# Tests may construct naive datetimes freely - that is how a fixed instant is
# written - and migrations are historical records that must not be edited.
SKIP_DIRS = {'tests', 'migrations'}


def production_modules():
    return sorted(
        p for p in QATRACK.rglob('*.py')
        if not SKIP_DIRS.intersection(p.parts) and not p.name.startswith('test_')
    )


def offenders():
    found = []
    for path in production_modules():
        for number, line in enumerate(path.read_text(encoding='utf8').splitlines(), 1):
            code = line.split('#')[0]
            for name, pattern in FORBIDDEN.items():
                if pattern.search(code):
                    found.append((path.relative_to(QATRACK.parent), number, name, line.strip()))
    return found


class TestTheSweepLooksAtSomething:

    def test_there_are_modules_to_check(self):
        """Guard the guard: an empty sweep would pass everything."""
        modules = production_modules()
        assert len(modules) > 100, (
            'only found %d production modules under %s' % (len(modules), QATRACK)
        )

    def test_the_patterns_match_what_they_are_meant_to(self):
        """And that the tz-bearing form is not caught by the tz-less pattern."""
        rx = FORBIDDEN['fromtimestamp() with no tz']
        assert rx.search('datetime.fromtimestamp(os.path.getmtime(path))')
        assert not rx.search('datetime.fromtimestamp(ts, datetime.UTC)')
        assert not rx.search('datetime.fromtimestamp(ts, datetime.timezone.utc)')
        assert FORBIDDEN['datetime.now()'].search('x = datetime.now()')
        assert not FORBIDDEN['datetime.now()'].search('x = timezone.now()')


class TestNoProductionCodeReadsTheMachineClock:

    def test_no_naive_clock_reads(self):
        found = offenders()
        assert not found, 'read the clock without a zone:\n' + '\n'.join(
            '  %s:%d  %s -> use %s\n      %s' % (
                path, number, name, REPLACEMENTS[name], line[:100],
            )
            for path, number, name, line in found
        )
