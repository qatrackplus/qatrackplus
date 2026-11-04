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

Found and patched by crane on 2026-11-04 against develop `0bbbcf64`, measured on a
Windows host and in the Docker stack. Reproduced on Linux by emptying `TZPATH`,
which is the mechanism rather than the platform - unpatched gave Edmonton −07,
Winnipeg −06 and Inuvik −07; patched gives all four correct.

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
nothing fails. @copilot made this point on c#34 and it is right: a unit test
cannot know what IANA published this morning without going to the network, which
is not a thing a test suite should do.

**What would catch it** is a step at release preparation: check the newest IANA
release against the pin, bump both together, and say in the commit which release
carries the change. Until that is in the release checklist, the honest statement
is the one above - this file is a regression guard, not a currency check.
"""

import importlib.resources
import zoneinfo
from datetime import datetime

import pytest

tzdata = pytest.importorskip("tzdata")

# The release carrying IANA 2026f, the first with all four changes above.
MINIMUM_TZDATA = (2026, 6)

# Checked at a date after every one of the 2026 transitions, so each expectation
# is about the permanent rule rather than a seasonal offset.
AFTER_THE_CHANGES = datetime(2026, 11, 4, 12, 0)
EXPECTED_OFFSETS = {
    "America/Vancouver": -7,
    "America/Edmonton": -6,
    "America/Inuvik": -6,
    "America/Winnipeg": -5,
}


def package_version():
    return tuple(int(part) for part in tzdata.__version__.split(".")[:2])


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
            "tzdata %s is older than %s, the release carrying IANA 2026f. A "
            "Windows site reads its rules from this package, so Alberta, "
            "Manitoba and NWT sites will be an hour out. Bump it with "
            "`uv lock --upgrade-package tzdata --upgrade-package pytz`."
            % (tzdata.__version__, ".".join(str(p) for p in MINIMUM_TZDATA))
        )

    @pytest.mark.parametrize("zone,expected", sorted(EXPECTED_OFFSETS.items()))
    def test_the_package_knows_the_2026_canadian_rules(self, zone, expected):
        got = offset_from_the_package(zone)
        assert got == expected, (
            "%s is %+.0f from the tzdata package, expected %+d. Either the pin "
            "has gone backwards, or IANA has changed this zone again - in which "
            "case update this expectation and the pin in the same commit."
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
        package = importlib.resources.files("tzdata").joinpath("zoneinfo")
        planted = tmp_path / "America" / "Edmonton"
        planted.parent.mkdir()
        planted.write_bytes(package.joinpath("Etc", "GMT-14").read_bytes())
        with package.joinpath("America", "Edmonton").open("rb") as f:
            from_the_package_file = AFTER_THE_CHANGES.replace(
                tzinfo=zoneinfo.ZoneInfo.from_file(f)).utcoffset().total_seconds() / 3600

        previous = zoneinfo.TZPATH
        try:
            zoneinfo.reset_tzpath([str(tmp_path)])
            zoneinfo.ZoneInfo.clear_cache()
            from_the_plant = AFTER_THE_CHANGES.replace(
                tzinfo=zoneinfo.ZoneInfo("America/Edmonton")).utcoffset().total_seconds() / 3600
            through_the_helper = offset_from_the_package("America/Edmonton")
        finally:
            zoneinfo.reset_tzpath(previous)
            zoneinfo.ZoneInfo.clear_cache()

        assert from_the_plant == 14, "the planted database was not read, so it shows nothing"
        assert through_the_helper == from_the_package_file, (
            "the helper gave %+.0f for America/Edmonton and the package's own file "
            "gives %+.0f, so the tests above are reading the host"
            % (through_the_helper, from_the_package_file)
        )
        assert zoneinfo.TZPATH == previous, "TZPATH was not restored"
