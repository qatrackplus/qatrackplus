# Pull Request Template

## Summary

_Enter PR description here... what is it supposed to do, and why?_

## Related Issues

_e.g. "Closes #1234", "Refs #1234". Write "None" if not applicable._

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature ( adds functionality, always assumed to be breaking until tested by maintainers)
- [ ] Breaking change (fix or addition that changes existing behaviour)
- [ ] Documentation only

## Target Branch

_Confirm which branch this targets (e.g. master)._

## AI Usage Disclosure

- [ ] No AI tools were used in this PR.
- [ ] AI tools were used:
  - **Tools / where used:** _e.g. GitHub Copilot for boilerplate_
  - [ ] I've reviewed every AI-generated line as if I wrote it myself, and confirm: no PHI shared, no license-incompatible content (Apache-2.0).

---

## PR Procedure

### Coder Tasks

- [ ] Rebased / merged `develop` branch; no merge conflicts.
- [ ] `uv run poe ci` passes. It is four tasks in order, cheapest first, so a
  failure can be re-run on its own: `poe lint` (the pre-commit suite over every
  file), `poe deps` (the lockfile and installed packages), `poe docs` (the
  documentation build, failing on any warning) and `poe test` (the suite).
- [ ] Lint and formatting fixes, if `poe ci` reported any:
  - `uv run poe lint-fix` applies ruff's automatic lint fixes.
  - `uv run poe format-changed` formats only what this branch changed. It works
    the file list out from git — this branch's commits plus anything
    uncommitted — and prints it before formatting, because formatting has never
    been applied repo-wide and `ruff format .` produces a large unrelated diff
    (see AGENTS.md). `uv run poe format-changed --check` reports what it would
    reformat without writing anything.
- [ ] `uv run poe check-deprecations` reviewed for new deprecation warnings.
- [ ] `uv run poe test` passes — the suite without the GUI tests, which are
  skipped by default.
- [ ] `uv run poe test-gui` passes — only the GUI/Selenium tests. **Headless is
  the default**, so no display server is needed. The browser is an optional
  option (`poe test-gui --mode headless --browser chromium`); omit either and
  your own settings choose that half. `--mode visible` and `--mode watch` show
  the run instead.
  For a single GUI test, go through pytest — `uv run pytest -m selenium -k
  test_name` — since the tasks take no pytest flags. These are
  `continue-on-error` in CI, so a red GUI run does not block the build; check
  it here rather than trusting the tick.
- [ ] `uv run poe check-migrations` passes. If it reports migrations, they
  belong in this PR and the change should be marked Breaking. (It runs
  `makemigrations --dry-run` for the listing and `--check --dry-run` for the
  exit code, because neither form gives both.)
- [ ] Docker builds succeed if touched.
- [ ] Docs updated under `docs/` if behaviour, settings, or APIs changed.
- [ ] `release_notes.md` updated if user-facing.
- [ ] No secrets, debug code, or stray `print`/`console.log` left in.

### Review Code

- [ ] Reviewer verifies the target branch.
- [ ] For non-trivial changes: pulled the branch, ran it locally, and confirmed it works as described.
- [ ] CI is green; test suite and `pre-commit` pass.
- [ ] Reads through all changed files for anything weird or unintended.
- [ ] Logic is correct; edge cases and error handling considered.
- [ ] Migrations are sane and reversible where possible.
- [ ] Changes are consistent with the modernization direction (no reintroduction
      of patterns being migrated away from, e.g. flake8/yapf-era conventions).
- [ ] No security concerns (input validation, permissions, injection, XSS).
- [ ] Comments are sufficient and not overkill.
- [ ] Typos, spellcheck, professional.
- [ ] Reviewer sends back review.

### Edits

- [ ] Coder fixes any issues.
- [ ] Reviewer approves.

> Maintainer review is required for breaking changes, new features, and migrations.
> For bug fixes, refactors, and docs-only changes, reviewer approval is sufficient to merge.

---

## Testing Notes

_How was this tested? List manual steps, affected units/test lists, browsers,
and whether you ran via uv or Docker._

## Screenshots

_If there are UI changes, add before/after screenshots. Otherwise write "N/A"._
