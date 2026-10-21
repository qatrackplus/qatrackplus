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
