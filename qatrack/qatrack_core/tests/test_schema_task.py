"""
The schema diagram's filename: one source, and the minor line.

`make schema` and `poe schema` are meant to be the same command through two
runners. They were not: the name came from a `VERSION` that existed in three
places - `VERSION=3.1.0` in the Makefile, `version = "4.0.0"` under `[project]`,
and `VERSION = "4.0.0"` in `[tool.poe.env]`. So the two runners wrote *different
files*, and the Makefile's wrote over the committed 3.1.0 diagram. The Makefile
carried a WARNING about that rather than a fix.

The poe task now reads the name from the installed package metadata, truncated
to the minor line because the schema is identical across every patch of a line.
That is the one correct implementation.

The Makefile is NOT that implementation, and deliberately so. It is frozen for
4.1 and removed during that cycle, so it still carries its own `VERSION=` and
still renders the diagram itself. The two runners therefore *can* disagree, and
these tests pin that rather than pretend otherwise: the Makefile's copy is
asserted to be exactly where it is and nowhere else, so an edit to it has to
come past a test, and the removal has something to delete against. `poe schema`
is the spelling to use; `poe make-schema` delegates to it rather than mirroring
the Makefile, precisely so the mirror does not carry a third copy.

These tests read the files as text. That is deliberate: running the task needs
pygraphviz and a database, and the defect was never in the rendering - it was in
two files disagreeing about the name, which is exactly what text can show.
"""

import importlib.metadata
import os
import re

from django.conf import settings

REPO_ROOT = os.path.dirname(settings.PROJECT_ROOT)
MAKEFILE = os.path.join(REPO_ROOT, "Makefile")
POE_DOCS = os.path.join(REPO_ROOT, "poe_tasks", "docs.toml")
PYPROJECT = os.path.join(REPO_ROOT, "pyproject.toml")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def schema_recipe():
    """The `schema:` target's recipe lines, without the comments above it."""

    text = read(MAKEFILE)
    body = text.split("\nschema:\n", 1)[1]
    # A recipe ends at the first line that is neither indented nor blank.
    lines = []
    for line in body.splitlines():
        if line and not line.startswith(("\t", " ")):
            break
        lines.append(line)
    return "\n".join(lines)


class TestTheSchemaNameHasOneSource:

    def test_the_minor_line_is_what_gets_named(self):
        version = importlib.metadata.version("qatrackplus")
        assert re.match(r"^\d+\.\d+", version), version
        minor = ".".join(version.split(".")[:2])
        # Two components, not three: qatrack_schema_4.0.svg, not 4.0.0.svg.
        assert minor.count(".") == 1, minor
        assert version.startswith(minor)

    def test_poe_does_not_hardcode_a_version(self):
        """The copy that *was* removed, and must not come back.

        `[tool.poe.env]` held `VERSION = "4.0.0"`, the third of the three copies.
        The poe task reads the installed metadata instead, so there is nothing
        for this table to hold any more.

        The Makefile's own copy is a separate matter, pinned by the test below:
        that file is frozen, so its copy is a known defect with a date on it
        rather than something to assert away.
        """

        # A table header at the start of a line, not the word anywhere - the
        # note in pyproject.toml explains why the table was removed and would
        # otherwise fail this.
        assert not re.search(r"^\[tool\.poe\.env\]", read(PYPROJECT), re.M), (
            "[tool.poe.env] is back; it held the third copy of the version"
        )

    def test_the_poe_task_reads_the_installed_package_and_truncates(self):
        """The one implementation, so this is where the name is decided."""

        task = read(POE_DOCS)
        assert "importlib.metadata" in task
        assert "qatrackplus" in task
        # The truncation is the part that makes it the minor line.
        assert "split('.')[:2]" in task, "the poe task does not truncate"
        assert "docs/developer/images/qatrack_schema_" in task

    def test_the_frozen_makefile_carries_exactly_one_version_and_poe_carries_none(self):
        """The Makefile's hardcoded version, pinned rather than removed.

        The Makefile is frozen for 4.1 and deleted during that cycle, so
        `VERSION=` stays where it is. This is not an endorsement of it. It is a
        *fourth* place the release version is written down, after `settings.py`,
        `pyproject.toml` and `uv.lock`, and nothing cross-checks the four - all
        three of the others have already been found dozens of commits stale at
        once. When this one goes stale, `make schema` writes a differently named
        SVG from `poe schema`, which is the original defect returning.

        It happens to be right today: `SCHEMA_VERSION=$(basename $(VERSION))`
        relies on GNU make's `basename` stripping `.2` from `4.0.2` as if it
        were a file extension, giving `4.0`, which is the committed diagram's
        name. That it is correct by a coincidence of string handling is the
        reason to pin it rather than trust it.

        Asserted as one occurrence, not as an absence, so that an edit to the
        frozen file has to come past a test, and so the removal in 4.1 has
        something concrete to delete against.
        """

        makefile = read(MAKEFILE)
        version_lines = re.findall(r"^VERSION\s*=.*$", makefile, re.M)
        assert len(version_lines) == 1, (
            "the frozen Makefile should carry its one historical VERSION line "
            "and no more; found %r" % (version_lines,)
        )
        # Only the schema name derives from it. Anything else using it would
        # widen what the 4.1 removal has to replace.
        users = [
            line for line in makefile.splitlines()
            if "$(SCHEMA_VERSION)" in line or "$(VERSION)" in line
        ]
        assert len(users) == 2, (
            "VERSION/SCHEMA_VERSION are used somewhere new in the Makefile; the "
            "schema filename was the only consumer. Found: %r" % (users,)
        )

        recipe = schema_recipe()
        assert "graph_models" in recipe, (
            "the frozen Makefile's schema target no longer renders the diagram; "
            "if it now delegates, this test and the freeze note are both stale"
        )

    def test_the_make_schema_mirror_delegates_instead_of_copying_the_target(self):
        """`poe make-schema` is one of the three deliberate non-mirrors.

        Every other `make-*` task reproduces what its target does. This one
        delegates to `poe schema`, because copying the target would copy the
        hardcoded version with it and make a third runner that can disagree.
        The mirror's help line says so; this asserts the delegation itself.
        """

        compat = read(os.path.join(REPO_ROOT, "poe_tasks", "make_compat.toml"))
        block = compat.split("[tasks.make-schema]", 1)[1].split("\n[tasks.", 1)[0]
        assert re.search(r'^ref\s*=\s*"schema"\s*$', block, re.M), (
            "poe make-schema no longer delegates to the schema task: %r" % block
        )
        assert "VERSION" not in block, (
            "the make-schema mirror has acquired its own version handling"
        )

    def test_the_diagram_stays_gitignored(self):
        """
        Regenerating to look at the schema must not stage an 838 KB SVG. Only a
        deliberate `git add -f` adds one for a new minor line.
        """

        assert "docs/developer/images/qatrack_schema_*.svg" in read(
            os.path.join(REPO_ROOT, ".gitignore")
        )
