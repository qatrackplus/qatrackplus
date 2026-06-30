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
- [ ] `uv run pre-commit run --all-files` passes (ruff lint, ruff-format, django-upgrade).
  - `uv run ruff check . --fix` to help resolve linting errors
- [ ] `uv run python -Wd manage.py check` reviewed for new deprecation warnings.
- [ ] `uv run pytest` full test suite passes.
- [ ] `uv run python manage.py makemigrations --check --dry-run` if migrations are found, change should be marked Breaking
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
