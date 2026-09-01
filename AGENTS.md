# AGENTS.md — AI Agent Guidance for QATrack+

This file gives AI coding agents the context they need to contribute effectively
to QATrack+, a free and open-source Django application for managing quality
control and maintenance activities at radiation therapy and diagnostic imaging
facilities. It is used in safety-critical clinical environments around the world.

---

## Who can use this file

This guidance applies equally to human developers using agentic AI tools
(GitHub Copilot, Claude Code, Cursor, etc.) and to fully automated AI agents
exploring or drafting changes in this repository.

---

## Project overview

| | |
|---|---|
| **Language** | Python 3.12 / 3.13 |
| **Framework** | Django 4.2 (LTS) |
| **Database** | PostgreSQL, MySQL, or MS SQL Server |
| **Package manager** | [uv](https://docs.astral.sh/uv/) (preferred) or pip |
| **Linter / formatter** | [ruff](https://docs.astral.sh/ruff/) |
| **Test runner** | pytest via `runtests.sh` or `python manage.py test` |
| **Docs** | Sphinx — `make docs` from repo root |
| **Target branch** | `Dev` (not `master`) |

---

## Repository layout

```
qatrack/        # Django project root; most application code lives here
  accounts/     # User accounts and authentication
  api/          # Django REST Framework API
  attachments/  # File-attachment handling
  contacts/     # Contact / notification system
  core/         # Core utilities, mixins, templatetags
  faults/       # Fault-logging application
  notifications/
  parts/        # Spare-parts tracking
  qa/           # QA test-list engine — the heart of the application
  reports/
  service_log/  # Service and maintenance logs
  units/        # Treatment-unit definitions
docs/           # Sphinx documentation (reStructuredText)
fixtures/       # Demo / seed data
requirements/   # Pinned requirement files (base, dev, docs)
runtests.sh     # Convenience test runner
```

---

## Getting started

```bash
# 1. Create a virtual environment and install all dependencies
uv sync --dev          # preferred
# or: pip install -r requirements/dev.txt

# 2. Provide local settings (database credentials, etc.)
cp qatrack/local_settings.example.py qatrack/local_settings.py
# edit qatrack/local_settings.py as needed

# 3. Apply migrations and load demo data
python manage.py migrate
python manage.py loaddata fixtures/demo_data.json

# 4. Run the development server
python manage.py runserver
```

---

## Linting and formatting

```bash
ruff check .          # lint
ruff format .         # auto-format
```

Configuration lives in `pyproject.toml` under `[tool.ruff]`.  
Line length is **120 characters**. Quote style is **single quotes**.  
Import ordering is enforced (`ruff` rule set `I`).

---

## Running the tests

```bash
bash runtests.sh
# or equivalently:
python manage.py test
# or with pytest directly:
pytest
```

Tests live next to the application code in `tests/` subdirectories inside each
Django app. Write or update tests for every functional change. Do not remove or
disable existing tests.

---

## Coding conventions

- Follow the style of the surrounding code.
- One logical change per commit; write clear imperative commit messages.
- Keep PRs focused — reviewers' time is limited.
- All PRs must target the `Dev` branch, **not** `master`.
- Fill in the pull request template completely (`.github/pull_request_template.md`).
- PRs that include tests, documentation updates, and a clear *why* are merged
  fastest.

### Dependencies

Prefer **Long-Term Support (LTS)** releases for all runtime dependencies whenever
one is available. This applies to Python, Django, Node.js, and any other
framework or major library the project depends on. LTS releases receive security
and bug-fix backports for a predictable window, which matters for a project
deployed in clinical environments where upgrades must be planned carefully.
When proposing a new dependency or a version bump, check whether the target
version is an LTS release and note it in the PR description.

### Language

**English (Canada)** is the lightly preferred written language for code
comments, commit messages, documentation, and user-facing strings. Canadian
English generally follows British spelling conventions (e.g. *behaviour*,
*colour*, *programme*) while using common North American technical vocabulary.
Consistency within a file always takes priority over strict adherence to any
one variant — do not change existing spelling just to match this preference.

Prefer **clear, engaging prose** over technically dry writing. QATrack+ is used
by medical physicists and clinical staff who bring deep domain expertise but
may not have a software background. Documentation, docstrings, error messages,
and UI text should feel approachable and human — explain the *why* alongside
the *what*, use plain language where technical jargon adds nothing, and write
as if you are guiding a knowledgeable colleague rather than producing a
specification.

---

## Documentation

Docs are built with Sphinx and live in `docs/`.

```bash
make docs           # from the repo root
# open docs/_build/html/index.html
```

Most pages use reStructuredText (`.rst`). When adding a new page, add it to
the relevant `toctree` directive in the section's `index.rst`.

---

## Documentation impact

When making code changes, check whether any of the following documentation
pages may be affected. If they are, either update the docs as part of the same
PR or call them out explicitly in the PR description under a
**"📚 Documentation to review"** heading.

A GitHub Actions workflow (`.github/workflows/docs-impact.yml`) posts an
automated heuristic comment on every PR that lists which doc paths may need
attention. The mapping it uses is reproduced here so that AI agents and
developers can apply the same logic before a PR is even opened.

The repository also includes an annual workflow
(`.github/workflows/annual-repository-health-review.yml`) that creates or
updates a yearly issue with dependency-maintenance signals, a pattern-based
code style review, an AI-driven code style review, and an AI-assisted
documentation tone review. Its findings are intentionally heuristic and may
overlap between sections; contributors should address them incrementally in
small, distinct PRs throughout the year.

The table also covers **cross-references between documentation files**: the
developer workflow (`docs/developer/`, `AGENTS.md`) and the installation guides
(`docs/install/`) overlap on topics such as Python version, Node.js version, and
the package manager. Whenever any one of these is updated, the others should be
reviewed for consistency.

| Changed path | Documentation to check |
|---|---|
| `qatrack/qa/` | `docs/admin/qa/`, `docs/user/qa/` |
| `qatrack/service_log/` | `docs/admin/service_log/`, `docs/user/service_log/`, `docs/tutorials/service_log/` |
| `qatrack/api/` | `docs/api/` |
| `qatrack/notifications/` | `docs/admin/notifications/` |
| `qatrack/faults/` | `docs/admin/faults/`, `docs/user/faults/` |
| `qatrack/parts/` | `docs/admin/service_log/parts.rst`, `docs/user/service_log/parts.rst` |
| `qatrack/accounts/` | `docs/admin/qa/auth.rst`, `docs/user/auth/` |
| `qatrack/units/` | `docs/admin/units/`, `docs/user/units/` |
| `qatrack/reports/` | `docs/user/reports/` |
| `qatrack/contacts/` | `docs/admin/qa/contacts.rst`, `docs/admin/qa/email.rst` |
| `qatrack/settings.py` | `docs/install/config.rst` |
| `qatrack/local_settings*`, `deploy/` | `docs/install/` |
| `qatrack/qatrack_core/` | `docs/developer/` |
| `AGENTS.md` | `docs/developer/`, `docs/install/` |
| `docs/developer/` | `docs/install/`, `AGENTS.md` |
| `docs/install/` | `docs/developer/`, `AGENTS.md` |

When reviewing or authoring a PR as an AI agent, look specifically for:

- Setting names or default values that appear in the docs but have changed in
  the code.
- URL patterns, view names, or admin page names that have been renamed or
  removed.
- Model fields that are described in user-facing guides but have been altered.
- New features or behaviour changes with no corresponding doc update.

If you find affected pages, include a block like this in the PR description:

```
📚 Documentation to review:
- `docs/admin/qa/tests.rst` — the `MyModel.some_field` field was renamed
```

---

## AI policy

### Agentic AI is encouraged

QATrack+ explicitly welcomes the use of agentic AI tools — GitHub Copilot,
Claude Code, Cursor, and similar assistants. These tools help developers
understand unfamiliar code, draft implementations, generate test cases, and
catch mistakes. The maintainer uses them too.

**Good uses for AI agents in this repository:**

- Exploring the codebase and explaining how a feature works.
- Drafting migrations, serializers, views, or tests for human review.
- Suggesting refactors or surfacing potential bugs.
- Writing or improving documentation and docstrings.
- Generating a first-pass implementation that a human then reads, tests, and
  revises.

### Direct AI-authored PRs are not accepted

This project does **not** accept pull requests submitted without meaningful
human review and understanding. This is not a rule against AI; it is a rule
about accountability.

QATrack+ is used in radiation therapy clinics where software defects can have
patient-safety implications. The maintainers do not have the resources to
perform the deep review that would be needed to compensate for a contribution
the author themselves does not fully understand. Every pull request must be
owned by a person who:

1. **Has read and understands the diff** — not just the summary, but the
   actual lines changed.
2. **Can explain the reasoning** behind each non-trivial decision if asked
   during review.
3. **Has run the tests locally** and confirmed they pass.
4. **Takes responsibility** for the correctness and safety of the change.

If you used an AI tool to help write the code, that is great — please say so
in the PR description. What is not acceptable is submitting AI-generated code
that you have not reviewed and do not understand.

> **In short:** AI as a tool, human as the author. PRs authored by AI
> agents acting autonomously, without a human reading and validating every
> line, will be closed without review.

---

## Getting help

- [GitHub Discussions](https://github.com/qatrackplus/qatrackplus/discussions)
- [QATrack+ Google Group](https://groups.google.com/g/qatrack)
- [Project wiki](https://github.com/qatrackplus/qatrackplus/wiki)
- Email: [medphys@crcrewso.ca](mailto:medphys@crcrewso.ca)
