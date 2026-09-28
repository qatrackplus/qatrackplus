"""
The schema diagram's filename: one source, and the minor line.

`make schema` and `poe schema` are meant to be the same command through two
runners. They were not: the name came from a `VERSION` that existed in three
places - `VERSION=3.1.0` in the Makefile, `version = "4.0.0"` under `[project]`,
and `VERSION = "4.0.0"` in `[tool.poe.env]`. So the two runners wrote *different
files*, and the Makefile's wrote over the committed 3.1.0 diagram. The Makefile
carried a WARNING about that rather than a fix.

Both now derive the name from the installed package metadata and truncate it to
the minor line, because the schema is identical across every patch of a line.

These tests read the two files as text. That is deliberate: running either task
needs pygraphviz and a database, and the defect was never in the rendering - it
was in the two files disagreeing about the name, which is exactly what text can
show.
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

    def test_neither_runner_hardcodes_a_version(self):
        """
        The `VERSION=3.1.0` that made the two disagree, and the poe copy of it.
        """

        assert not re.search(r"^VERSION\s*=", read(MAKEFILE), re.M), (
            "the Makefile defines VERSION again; the schema target is the only "
            "thing that ever used it, and a hardcoded copy is what made "
            "`make schema` and `poe schema` write different files"
        )
        # A table header at the start of a line, not the word anywhere - the
        # note in pyproject.toml explains why the table was removed and would
        # otherwise fail this.
        assert not re.search(r"^\[tool\.poe\.env\]", read(PYPROJECT), re.M), (
            "[tool.poe.env] is back; it held the third copy of the version"
        )

    def test_both_runners_read_the_installed_package(self):
        for path, text in ((MAKEFILE, schema_recipe()), (POE_DOCS, read(POE_DOCS))):
            assert "importlib.metadata" in text, path
            assert "qatrackplus" in text, path

    def test_both_truncate_to_two_components(self):
        """
        The truncation is the part that makes it the minor line. Written the same
        way in both, so a reader comparing them sees one expression.
        """

        truncation = "split('.')[:2]"
        assert truncation in schema_recipe(), "the Makefile target does not truncate"
        assert truncation in read(POE_DOCS), "the poe task does not truncate"

    def test_the_output_path_is_the_same_in_both(self):
        path = "docs/developer/images/qatrack_schema_"
        assert path in schema_recipe()
        assert path in read(POE_DOCS)

    def test_the_diagram_stays_gitignored(self):
        """
        Regenerating to look at the schema must not stage an 838 KB SVG. Only a
        deliberate `git add -f` adds one for a new minor line.
        """

        assert "docs/developer/images/qatrack_schema_*.svg" in read(
            os.path.join(REPO_ROOT, ".gitignore")
        )
