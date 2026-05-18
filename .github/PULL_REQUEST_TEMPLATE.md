## Summary

_Enter PR description here... what is it supposed to do, and why?_

## Related Issues

<!-- e.g. "Closes #1234", "Refs #1234". Write "None" if not applicable. -->

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that changes existing behaviour)
- [ ] Modernization / migration (part of the qatrackplus modernization effort)
- [ ] Documentation only
- [ ] Refactor / chore (no functional change)

## Target Branch

<!-- Confirm which branch this targets (e.g. master). -->

## AI Usage Disclosure

_Select one. If AI tools (Copilot, Claude, ChatGPT, Cursor, etc.) were used,
the coder remains fully responsible for the correctness, licensing, and quality
of all submitted code._

- [ ] No AI tools were used in this PR.
- [ ] AI tools were used. Details below.

<!-- If AI was used, fill this in: -->
- **Tools used:** <!-- e.g. GitHub Copilot, Claude, Cursor -->
- **Where / how:** <!-- e.g. boilerplate, test scaffolding, refactor suggestions, full feature draft -->
- [ ] I have reviewed and understand every line of AI-generated code as if I wrote it myself.
- [ ] No proprietary, secret, or PHI/patient data was shared with an AI tool.
- [ ] AI-generated code introduces no license-incompatible content (Apache-2.0).

---

## PR Procedure

### Coder Tasks

- [ ] Coder merges the target branch into the feature branch (no merge conflicts).
- [ ] Environment synced with `uv` (`uv sync`); `pyproject.toml` / lockfile updated if deps changed.
- [ ] `pre-commit run --all-files` passes (ruff lint, ruff-format, django-upgrade).
- [ ] No new `ruff` violations; code is ruff-formatted.
- [ ] `django-upgrade` (target 4.2) introduced no regressions; no deprecated Django APIs added.
- [ ] New/changed code has tests; full suite passes (`runtests.sh`).
- [ ] Django migrations generated and committed if models changed.
- [ ] `python -Wd manage.py check` reviewed for new deprecation warnings.
- [ ] Docker builds succeed if touched (`docker-compose.dev.yml` / `docker-compose.yml`).
- [ ] Docs updated under `docs/` if behaviour, settings, or APIs changed.
- [ ] `release_notes.md` updated if user-facing.
- [ ] No secrets, credentials, debug code, or stray `print`/`console.log` left in.
- [ ] CI (GitHub Actions) is green on the latest commit.
- [ ] Coder reviews their own diff as below.
- [ ] Coder creates PR and assigns a reviewer.

### Review Code

- [ ] Reviewer merges the target branch into the feature branch.
- [ ] Pulls the branch, runs it (uv or Docker), and confirms it works as described.
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
- [ ] Reviewer assigns the maintainer for final review.

### Maintainer Review

- [ ] Maintainer reviews and sends back review.
- [ ] Coder fixes any issues.
- [ ] Maintainer approves.
- [ ] Maintainer merges.

---

## Testing Notes

_How was this tested? List manual steps, affected units/test lists, browsers,
and whether you ran via uv or Docker._

## Screenshots

_If there are UI changes, add before/after screenshots. Otherwise write "N/A"._
