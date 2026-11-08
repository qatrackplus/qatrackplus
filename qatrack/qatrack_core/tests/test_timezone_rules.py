"""The bundled time-zone rules have to be current, and nothing noticed when they were not.

`uv.lock` pinned `tzdata==2026.2`, carrying IANA release **2026b**. Four Canadian
jurisdictions changed their rules during 2026 and 2026b knows about one of them:

| change | zone | first in |
|---|---|---|
| British Columbia, permanent −07 | `America/Vancouver` | 2026b |
| Alberta, permanent −06 | `America/Edmonton` | 2026c |
| Northwest Territories, permanent −06 | `America/Inuvik` | 2026d |
| Manitoba, permanent −05 from 2026-10-31 | `America/Winnipeg` | 2026e |

**Which copy of the rules a site uses depends on the platform**, which is why this
went unseen:

- **Linux** reads the OS `tzdata` package first, so a maintained server was right;
- **Windows** has no OS copy that `zoneinfo` reads - `TZPATH` is empty - so it uses
  the `tzdata` **package**, and a site with `TIME_ZONE = 'America/Edmonton'` or
  `'America/Winnipeg'` showed times an hour off from 1 November;
- **Docker** depends on how old the base image was when it was built.

Measured on a Windows host and in the Docker stack, and reproduced on Linux by
emptying `TZPATH`, which is the mechanism rather than the platform: without the
fix Edmonton came out at −07, Winnipeg at −06 and Inuvik at −07; with it, all four are
correct.

**These tests read the package, not the operating system.** On a developer's Linux
box the OS copy is usually current and would mask exactly the defect being guarded
against.

**What these tests do and do not catch.** They assert the four offsets at a fixed
instant in 2026 and that the installed `tzdata` is at least the release carrying
them. So they catch a *regression* - a lock bump backwards, a stale virtual
environment, a dependency resolution that quietly picks an older package - and
they would have caught this defect before it shipped.

**They do not keep the rules current, and the distinction matters.** If IANA
changes one of these zones again with effect from, say, 2027, a current database
and a 2026f one both return the same offsets at the instant asserted here, so
nothing fails. A unit test cannot know what IANA published this morning without
going to the network, and that is not a thing a test suite should do.

**What would catch it** is a step at release preparation: check the newest IANA
release against the pin, bump both together, and say in the commit which release
carries the change. Until that is in the release checklist, the honest statement
is the one above - this file is a regression guard, not a currency check.
"""

import importlib.resources
import pathlib
import zoneinfo
from datetime import datetime

import pytest
import tzdata

# The release carrying IANA 2026f, the first with all four changes above.
CONFIG_PAGE = pathlib.Path(__file__).resolve().parents[3] / 'docs' / 'install' / 'config.rst'

MINIMUM_TZDATA = (2026, 6)

# Checked at a date after every one of the 2026 transitions, so each expectation
# is about the permanent rule rather than a seasonal offset.
AFTER_THE_CHANGES = datetime(2026, 11, 4, 12, 0)
EXPECTED_OFFSETS = {
    'America/Vancouver': -7,
    'America/Edmonton': -6,
    'America/Inuvik': -6,
    'America/Winnipeg': -5,
}


def package_version():
    return tuple(int(part) for part in tzdata.__version__.split('.')[:2])


def offset_from_the_package(zone):
    """The offset `zoneinfo` gives with no operating-system database to read.

    `reset_tzpath([])` is what makes this the package's answer rather than the
    host's, and it is reset again afterwards so no other test inherits it.
    """
    previous = zoneinfo.TZPATH
    try:
        zoneinfo.reset_tzpath([])
        zoneinfo.ZoneInfo.clear_cache()
        moment = AFTER_THE_CHANGES.replace(tzinfo=zoneinfo.ZoneInfo(zone))
        return moment.utcoffset().total_seconds() / 3600
    finally:
        zoneinfo.reset_tzpath(previous)
        zoneinfo.ZoneInfo.clear_cache()


class TestTheBundledRulesAreCurrent:

    def test_the_tzdata_package_is_new_enough(self):
        """The pin, asserted directly, because it is the thing that goes stale."""
        assert package_version() >= MINIMUM_TZDATA, (
            'tzdata %s is older than %s, the release carrying IANA 2026f. A '
            'Windows site reads its rules from this package, so Alberta, '
            'Manitoba and NWT sites will be an hour out. Bump it with '
            '`uv lock --upgrade-package tzdata --upgrade-package pytz`.'
            % (tzdata.__version__, '.'.join(str(p) for p in MINIMUM_TZDATA))
        )

    @pytest.mark.parametrize('zone,expected', sorted(EXPECTED_OFFSETS.items()))
    def test_the_package_knows_the_2026_canadian_rules(self, zone, expected):
        got = offset_from_the_package(zone)
        assert got == expected, (
            '%s is %+.0f from the tzdata package, expected %+d. Either the pin '
            'has gone backwards, or IANA has changed this zone again - in which '
            'case update this expectation and the pin in the same commit.'
            % (zone, got, expected)
        )

    def test_the_helper_reads_the_package_whatever_the_host_has(self, tmp_path):
        """The control. Without it, the tests above could be reading the host.

        On a maintained Linux box the OS copy is current, so a test that
        accidentally read it would pass while the package was two releases
        behind - which is precisely how this went unnoticed.

        So a host database that is wrong on purpose is planted on `TZPATH`:
        an `America/Edmonton` holding the rules of `Etc/GMT-14`, fourteen
        hours ahead of UTC. `zoneinfo` has to read the plant, which shows it
        is on the path; the helper has to give the package's own answer
        instead. It needs no OS database of its own and does not care whether
        the host's copy is current, so it means the same on Windows, where
        `TZPATH` is empty, as on Linux.
        """
        package = importlib.resources.files('tzdata').joinpath('zoneinfo')
        planted = tmp_path / 'America' / 'Edmonton'
        planted.parent.mkdir()
        planted.write_bytes(package.joinpath('Etc', 'GMT-14').read_bytes())
        with package.joinpath('America', 'Edmonton').open('rb') as f:
            from_the_package_file = AFTER_THE_CHANGES.replace(
                tzinfo=zoneinfo.ZoneInfo.from_file(f)).utcoffset().total_seconds() / 3600

        previous = zoneinfo.TZPATH
        try:
            zoneinfo.reset_tzpath([str(tmp_path)])
            zoneinfo.ZoneInfo.clear_cache()
            from_the_plant = AFTER_THE_CHANGES.replace(
                tzinfo=zoneinfo.ZoneInfo('America/Edmonton')).utcoffset().total_seconds() / 3600
            through_the_helper = offset_from_the_package('America/Edmonton')
        finally:
            zoneinfo.reset_tzpath(previous)
            zoneinfo.ZoneInfo.clear_cache()

        assert from_the_plant == 14, 'the planted database was not read, so it shows nothing'
        assert through_the_helper == from_the_package_file, (
            "the helper gave %+.0f for America/Edmonton and the package's own file "
            'gives %+.0f, so the tests above are reading the host'
            % (through_the_helper, from_the_package_file)
        )
        assert zoneinfo.TZPATH == previous, 'TZPATH was not restored'


class TestThePageTellsASiteSomethingItCanActOn:
    """`docs/install/config.rst`'s time-zone section, held to two claims.

    Documentation is the procedure here - there is no command that updates the
    rules for you - so a sentence that reads like an instruction and does
    nothing is a defect, not a wording preference. Both of these were found by
    review rather than by anybody's site going wrong, which is the only cheap
    way to find them.

    1. **The restart instruction has to restart something.** The note said
       `docker compose up -d` would do it. That recreates containers when the
       image or the configuration has changed and does nothing when neither
       has: it prints `Container Running` and leaves the processes untouched.
       The reader of that sentence is, by construction, somebody whose rules
       just changed *underneath* an unchanged image - so the one command given
       was the one that could not work, and it reports success.

    2. **Docker has to be given somewhere to go between releases.** The
       section's premise is that stale rules are silent, which invites "what if
       IANA publishes before the next QATrack+ release?". The page answered that
       for Linux and for Windows-with-pip and told Docker "there is nothing to
       do" - true of a release upgrade, and read as a general reassurance.
    """

    @staticmethod
    def section():
        """The time-zone material, not the whole page."""
        text = CONFIG_PAGE.read_text(encoding='utf8')
        start = text.index('Keeping the time zone rules current')
        return text[start:text.index('\nOrganization Logo', start)]

    def test_the_section_is_still_where_this_looks_for_it(self):
        assert 'PYTHONTZPATH' in self.section(), (
            'the time-zone section of config.rst has moved or been renamed; the two tests '
            'below are reading the wrong text'
        )

    def test_the_docker_restart_is_a_command_that_restarts(self):
        section = self.section()
        assert 'docker compose restart' in section, (
            "config.rst does not give Docker a command that restarts the processes. "
            "`docker compose up -d` is not one when the image has not changed - it reports "
            "`Container Running` and does nothing, which is indistinguishable from success."
        )
        restart_block = section[section.index('restart QATrack+ after updating'):]
        assert 'Not ``docker compose up -d``' in restart_block, (
            "the page no longer says why `docker compose up -d` is the wrong command here. "
            "Without that, the next person to tidy this will replace `restart` with it again, "
            "because everywhere else in the Docker documentation `up -d` is right."
        )

    def test_the_windows_route_does_not_tell_a_site_to_run_a_bare_uv_sync(self):
        """`uv sync` is exact by default, so a bare one uninstalls the extras.

        The between-releases route ends in a sync on Windows, and the first
        version of it said plain `uv sync`. That removes CherryPy, pywin32,
        mssql-django and the LDAP packages from a Windows site - a working site
        broken by a command given to correct a clock. @nsmela caught it on
        q#926 with a dry run; reproduced here as `Would uninstall 2 packages`.
        """
        # Command lines only - the indented contents of a `code-block`. The
        # prose around them has to be free to say `uv sync` while explaining
        # why a bare one is wrong, and an earlier version of this test flagged
        # exactly that explanation.
        commands = [
            line.strip() for line in self.section().splitlines()
            if line.startswith('    ') and line.strip().startswith('uv sync')
        ]
        assert commands, (
            'no `uv sync` command line in the time-zone section; if the Windows route has '
            'moved or been dropped, re-read it rather than deleting this test'
        )
        bare = [c for c in commands if '--extra' not in c and '--dry-run' not in c]
        assert not bare, (
            'the time-zone section tells a site to run uv sync without the extras it '
            'installed with, which uninstalls them: %r' % bare
        )

    def test_no_bold_run_in_the_section_contains_a_literal(self):
        """RST inline markup cannot nest, and `sphinx -W` does not say so.

        `**Not a bare ``uv sync``.**` does not parse. It does not warn either -
        the strict build reported zero warnings - it simply renders with the
        double backticks showing as text on the page. That happened twice in
        this file in one day, and both times the only thing that caught it was
        reading the built HTML rather than the source.

        Checked by pairing the `**` markers instead of pattern-matching them: a
        regex for the whole construct also matches the gap *between* two bold
        runs, which is how a first attempt at this found 27 instances in
        `docs/` that were all false.
        """
        for paragraph in self.section().split('\n\n'):
            runs = paragraph.split('**')
            # Even count of markers means they pair; odd means one is a stray
            # and this crude split would mis-assign the halves.
            if len(runs) % 2 == 0:
                continue
            for inside in runs[1::2]:
                assert '``' not in inside, (
                    'a bold run contains a literal, which RST will not parse and the '
                    'docs build will not warn about - it renders with the backticks '
                    'visible: %r' % ('**%s**' % inside)
                )

    def test_docker_is_told_how_to_get_new_rules_before_a_release(self):
        section = self.section()
        assert 'uv lock --upgrade-package tzdata' in section, (
            'config.rst does not say how a Docker or uv-based Windows site gets new rules '
            'between QATrack+ releases. Both take them from uv.lock, so the lockfile is the '
            'only thing that can move.'
        )
        assert 'site-requirements' in section, (
            "the page does not warn that site-requirements/ cannot serve as that route. It is "
            "where an administrator will look first, and a newer tzdata there fails the build: "
            "the Dockerfile constrains site packages to QATrack+'s own frozen versions."
        )
