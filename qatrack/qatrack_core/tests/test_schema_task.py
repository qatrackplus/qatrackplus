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

`make schema` is now RETIRED, by Cody's decision of 2026-11-05: since make
support is going away, a target that was broken prints that it is retired and
names the poe task instead of running. So there is once again exactly one
implementation and one place the version comes from - and the Makefile's
`VERSION=`, a fourth hand-written copy of the release version, went with the
target that was its only consumer.

That makes this file's original assertion true again, and it is asserted again
below: neither runner hardcodes a version. The retirement message itself is
covered in `test_poe_tasks.py`, which checks the target no longer renders, names
`poe schema`, and fails rather than reporting success.

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

    def test_neither_runner_hardcodes_a_version(self):
        """The copies that made the two runners disagree, all of them gone.

        There were three: `[tool.poe.env]` said 4.0.0, `[project]` said 4.0.0,
        and the Makefile said 3.1.0 - so `make schema` and `poe schema` wrote
        *different files*, and the Makefile's wrote over the committed 3.1.0
        diagram.

        `[tool.poe.env]` went when the poe task started reading the installed
        package metadata. The Makefile's went on 2026-11-05 with the retirement
        of the target that was its only consumer - which also removed a fourth
        hand-written copy of the release version, after `settings.py`,
        `pyproject.toml` and `uv.lock`, none of which anything cross-checks.
        """

        assert not re.search(r"^VERSION\s*=", read(MAKEFILE), re.M), (
            "the Makefile defines VERSION again; the schema target was the only "
            "thing that ever used it, and a hardcoded copy is what made "
            "`make schema` and `poe schema` write different files"
        )
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

    def make_schema_block(self):
        compat = read(os.path.join(REPO_ROOT, "poe_tasks", "make_compat.toml"))
        return compat.split("[tasks.make-schema]", 1)[1].split("\n[tasks.", 1)[0]

    def test_the_make_schema_mirror_is_retired_like_its_target(self):
        """`make schema` refuses and explains itself, so the mirror does too.

        A mirror that kept the withdrawn name working would leave the
        retirement half done: every checklist, script or habit that says
        `make-schema` would carry on unwarned.
        """

        block = self.make_schema_block()
        assert not re.search(r'^ref\s*=\s*"schema"\s*$', block, re.M), (
            "poe make-schema still delegates to the schema task, so the retired "
            "name keeps working: %r" % block
        )
        assert re.search(r'sys\.exit\(', block), (
            "poe make-schema does not fail, so a caller cannot tell it refused: %r" % block
        )

    def test_the_make_schema_mirror_names_its_replacement(self):
        """Refusing without saying what to run instead is the failure this is
        meant to prevent, not a smaller version of it."""

        block = self.make_schema_block()
        assert "uv run poe schema" in block, (
            "poe make-schema refuses without naming `uv run poe schema`: %r" % block
        )

    def test_the_make_schema_mirror_has_no_version_handling(self):
        """It must not acquire a second copy of the name the diagram is
        written under - that duplication is what made the two runners disagree
        in the first place."""

        assert "VERSION" not in self.make_schema_block()

    def test_the_makefile_no_longer_points_at_the_retired_mirror(self):
        """`make schema` used to end with "or, by this name: uv run poe
        make-schema". That now names a task that refuses."""

        makefile = read(os.path.join(REPO_ROOT, "Makefile"))
        target = makefile.split("\nschema:", 1)[1].split("\n\n", 1)[0]
        assert "uv run poe schema" in target, "the target no longer names the replacement"
        assert "poe make-schema" not in target, (
            "`make schema` still sends the reader to the retired mirror: %r" % target
        )

    def test_the_diagram_stays_gitignored(self):
        """
        Regenerating to look at the schema must not stage an 838 KB SVG. Only a
        deliberate `git add -f` adds one for a new minor line.
        """

        assert "docs/developer/images/qatrack_schema_*.svg" in read(
            os.path.join(REPO_ROOT, ".gitignore")
        )
