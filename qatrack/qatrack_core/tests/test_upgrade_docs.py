"""Upgrade instructions must stop the web application server before they
replace what it is running.

This is a test about documentation because the documentation is the procedure:
there is no upgrade script to get wrong. `linux_upgrade_from_4_0.rst` told the
reader to stop nginx and django-q2 and then run `uv sync` and `collectstatic` -
leaving gunicorn, which supervisor runs as its own program, serving with its
Python already imported while the dependencies and templates changed under it.
Raised by Copilot on PR crcrewso#18, 2026-10-19.

A reviewer cannot be relied on to notice an omission in a list of shell
commands, so the invariant is pinned here instead.
"""

import pathlib
import re
import unittest

DOCS = pathlib.Path(__file__).resolve().parents[3] / "docs" / "install"

# Programs that serve requests, as opposed to the task cluster. Each upgrade
# page is for a particular starting point, so which one it stops differs: a
# 4.0 install runs gunicorn under supervisor, a 3.x install ran under apache.
WEB_SERVERS = ("gunicorn", "apache2", "apache")

# What must not happen before the web server is stopped. `uv sync` replaces
# installed packages; collectstatic replaces what the templates reference.
DESTRUCTIVE = ("uv sync", "collectstatic")


def _procedure(text):
    """The commands, without the summary that precedes them.

    These pages open with a numbered overview ("3. ``uv sync`` with your
    database's extra") before the section that gives the commands. Order only
    means anything in the latter, so the overview would otherwise read as
    `uv sync` happening before anything is stopped.
    """
    for heading in ("Running the upgrade", "Running the Upgrade"):
        if heading in text:
            return text[text.index(heading):]
    return text


def _linux_upgrade_pages():
    return sorted(
        p for p in DOCS.glob("*upgrade*.rst")
        if "linux" in p.name and not p.name.startswith("_")
    )


class TestLinuxUpgradePagesStopTheWebServer(unittest.TestCase):

    def test_there_are_pages_to_check(self):
        """Guard against the glob quietly matching nothing."""
        assert _linux_upgrade_pages(), "no Linux upgrade pages found under %s" % DOCS

    def test_each_page_stops_a_web_server_before_changing_what_it_serves(self):
        for page in _linux_upgrade_pages():
            with self.subTest(page=page.name):
                text = _procedure(page.read_text(encoding="utf-8"))

                # Both orders occur in these pages: `supervisorctl stop
                # gunicorn` names the program after the verb, `service apache2
                # stop` before it. Match the line, not the word order.
                stop_positions = [
                    m.start() for m in re.finditer(r"(?m)^.*$", text)
                    if "stop" in m.group(0)
                    and any(server in m.group(0) for server in WEB_SERVERS)
                ]
                assert stop_positions, (
                    "%s never stops a web application server (%s). Replacing "
                    "dependencies or static files under live workers leaves old "
                    "code serving new templates." % (
                        page.name, ", ".join(WEB_SERVERS),
                    )
                )

                first_stop = min(stop_positions)
                for command in DESTRUCTIVE:
                    position = text.find(command)
                    if position == -1:
                        continue
                    assert position > first_stop, (
                        "%s runs `%s` before it stops the web server" % (
                            page.name, command,
                        )
                    )

    def test_whatever_is_started_again_was_stopped_first(self):
        """An upgrade that ends with a program it never stopped is suspect.

        The 3.x page is the honest exception and is excluded: gunicorn does not
        exist on a 3.x install, so that page legitimately starts a program it
        could not have stopped.
        """
        programs = re.compile(r"supervisorctl\s+(stop|start)\s+([a-z0-9\- ]+)")

        for page in _linux_upgrade_pages():
            if "from_3" in page.name:
                continue
            with self.subTest(page=page.name):
                text = page.read_text(encoding="utf-8")
                stopped, started = set(), set()
                for action, names in programs.findall(text):
                    (stopped if action == "stop" else started).update(names.split())
                assert started <= stopped, (
                    "%s starts %s without stopping it" % (
                        page.name, ", ".join(sorted(started - stopped)),
                    )
                )


class TestInstallDocsDoNotTeachTheDeprecatedSeleniumForm(unittest.TestCase):
    """`-m "not selenium"` works today, warns, and goes away in 4.2.

    Since #867 plain `pytest` skips the GUI tests, and the conftest raises a
    `PytestDeprecationWarning` for the marker expression. An install page that
    still tells a site administrator to type it hands them a command that will
    stop working, and - worse here - the paragraph that carried it also told
    them the GUI tests *error at setup*, which is the behaviour from before that
    change. A reader following an upgrade page has no way to know which of the
    two they are on.

    `docs/developer/` is deliberately excluded: those pages document the
    deprecation itself and have to name the form to deprecate it.

    **The pages that upgrade a site *to* a pre-4.1 release are excluded too**,
    and for the opposite reason. A reader of
    `*_upgrade_from_4_0*.rst` ends the page on 4.0.x, which has no
    `conftest.py`: there, plain `pytest` errors at setup on ~40 GUI tests and
    `--run-selenium` is not understood. The marker expression is the only form
    that works on the release those pages deliver, and it keeps working on 4.1
    until it is removed in 4.2 - so it is correct for that audience on both
    sides of the upgrade, which plain `pytest` is not.

    Banning it there made those three pages tell operators to run a command
    that fails on the code they are running. The ban is right everywhere a
    reader is already on 4.1 or later.
    """

    #: Pages whose reader finishes on a release older than the conftest change.
    #: Matched on the whole filename, not as a substring, because
    #: `linux_upgrade_from_4_0_2.rst` upgrades *to* 4.1 and must stay checked
    #: while `linux_upgrade_from_4_0_1.rst` upgrades to 4.0.2 and must not.
    #: A loose `"upgrade_from_4_0" in name` test cannot tell those apart.
    PRE_CONFTEST_SUFFIXES = ("_upgrade_from_3.rst", "_upgrade_from_4_0.rst",
                             "_upgrade_from_4_0_1.rst")
    PRE_CONFTEST_FRAGMENTS = ("_upgrade_4_0_before.rst", "_upgrade_4_0_after.rst",
                              "_upgrade_4_0_1_before.rst", "_upgrade_4_0_1_after.rst")

    @classmethod
    def delivers_a_pre_conftest_release(cls, name):
        return name.endswith(cls.PRE_CONFTEST_SUFFIXES) or name in cls.PRE_CONFTEST_FRAGMENTS

    def test_there_are_pages_to_check(self):
        assert sorted(DOCS.glob("*.rst")), "no install pages found under %s" % DOCS

    def test_no_install_page_asks_for_the_marker_expression(self):
        for page in sorted(DOCS.glob("*.rst")):
            if self.delivers_a_pre_conftest_release(page.name):
                continue
            with self.subTest(page=page.name):
                assert "not selenium" not in page.read_text(encoding="utf-8"), (
                    '%s tells the reader to pass `-m "not selenium"`, which is '
                    "deprecated for removal in 4.2 - plain `pytest` already "
                    "skips the GUI tests" % page.name
                )
