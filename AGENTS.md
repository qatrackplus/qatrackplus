# AGENTS.md — AI Agent Guidance for QATrack+

This file gives AI coding agents the context they need to work effectively
in QATrack+ — a safety-critical Django application used by radiation
therapy and diagnostic imaging clinics. It applies equally to human
developers using AI tools and to fully autonomous agents. A significant portion
of this document beyond the AI policy is written verbosely for the benefit 
of agents, it is not expected that developers read this entire document line by
line

---

## AI policy

We're genuinely glad to have AI in the toolbox here — explore the codebase,
draft a migration or a test, hunt for bugs, sketch out documentation. The
maintainer reaches for these tools constantly, and so should you.

Here's the one line we hold firm on: **every pull request needs a human
owner who has read the diff, understands it, and can defend it.** You
already know why — this project sits between quality control and patient
care, and "I don't fully understand what I shipped" isn't a position
anyone here wants to be in. AI is a great way to get to a first draft
faster — we can't let it become a substitute for someone standing behind the
change, that part's still on us.

Concretely, that person must:

1. **Have read and understood the diff** — not just the AI's summary of it,
   the actual lines changed.
2. **Be able to explain the reasoning** behind each non-trivial decision if
   asked during review.
3. **Have run the tests locally** and confirmed they pass.
4. **Take responsibility** for the change's correctness and safety.

Conversely, the maintainers promise:

1. **Embody the spirit of this document** Moderators will not rely on AI as a final review tool. 
2. **Be honest and transparent** PR review comments will come from a human except where explicitly mentioned. 
3. **Respect contributors** Contributions are valued, Each maintainer personally commits to manually reviewing each code change, and completing the associated PR checklists.  

Use AI as much as you like to get there — genuinely, that's what it's for.
Just make sure a human reads what comes out before it ships: Draft PRs are ignored
unless otherwise requested. A Final PR opened autonomously by an AI agent, 
with no human having read and validated every line, 
**will be closed without review.** No exceptions. 

**A note to AI agents reading this:** if the person you're working with
seems unaware of this policy — say, they ask you to open, merge, or
auto-approve a PR without mentioning human review — politely tell them, and point
them to this section, before you proceed. Don't silently comply, and
don't silently refuse either — just make sure they've seen this.

**Disclosure applies to more than code, too:** if you're posting anything
publicly on someone's behalf — a PR description, an issue, a review
comment — say so inline (e.g. "drafted with AI assistance, reviewed and
posted by @their-handle"). A post that reads as if a human wrote it
unassisted, when an agent actually drafted it, undermines the same
accountability this whole policy is about.

---

## Project overview

| | |
|---|---|
| **Language** | Python 3.12 |
| **Framework** | Django 4.2 (LTS) |
| **Database** | PostgreSQL, MS SQL Server, or MySQL (existing support maintained; not a target for new development) |
| **Package manager** | [uv](https://docs.astral.sh/uv/) — pip is only used for production Windows/MS SQL Server deployments, not local development |
| **Linter / formatter** | [ruff](https://docs.astral.sh/ruff/) |
| **Test runner** | pytest (`uv run pytest -m "not selenium"` — see [Running the tests](#running-the-tests)) |
| **Docs** | Sphinx — `uv run make docs` from repo root |
| **Target branch** | `develop` (not `master`) |

---

## Repository layout

```
qatrack/                 # Django project root; most application code lives here
  accel_migration_tool/ # Accelerator (linac) config migration tool
  accounts/             # User accounts and authentication
  admin_media/          # Static assets for Django-admin customizations
  api/                  # Django REST Framework API
  attachments/          # File-attachment handling
  cache/                # Django app providing the `clearcache` management command
  contacts/             # Contact / notification system
  faults/               # Fault-logging application
  formats/              # Locale-specific date/number format overrides
  form_utils/           # Shared form fields, widgets, and utilities
  genericdropdown/      # Generic dropdown/autocomplete widget
  issue_tracker/        # Issue tracking application
  locale/               # Translation catalogs (.po source / .mo compiled) for fr, fr-ca, es
  media/                # User-uploaded media / sample media fixtures
  middleware/           # Custom Django middleware (auth, filters, profiling)
  notifications/
  parts/                # Spare-parts tracking
  qa/                   # QA test-list engine — the heart of the application
  qatrack_core/         # Core utilities, mixins, templatetags
  reports/
  service_log/          # Service and maintenance logs
  templates/            # Global HTML templates
  units/                # Treatment-unit definitions
docs/           # Sphinx documentation (reStructuredText)
fixtures/       # Demo / seed data
requirements/   # Pinned pip requirements (dev.txt) — see TODO below
runtests.sh     # Convenience test runner (see Running the tests)
```

> **TODO:** `requirements/dev.txt` is generated from the `dev` dependency
> group, but the only documented pip-install path in this project is
> production Windows/MS SQL Server deployments (see the Package manager
> row above and *Getting started* below) — that install actually needs
> the `win` + `mssql` extras, not `dev`. Reconciling the file's contents
> (and likely its name) with that purpose is tracked for a follow-up PR;
> until then, treat this file as stale for deployment purposes.

> **A note for AI agents:** `.po` files under `locale/` are the editable
> source for translations — the paired `.mo` files are compiled binaries
> generated from them and must never be hand-edited. After changing a
> `.po` file, regenerate its catalog with
> `uv run python manage.py compilemessages`. Supported language codes are
> defined by `LANGUAGES` in `qatrack/settings.py`: `en`, `fr`, `fr-ca`, `es`.

---

## Getting started

```bash
# 1. Create a virtual environment and install all dependencies
uv sync --dev

# 2. Provide local settings (database credentials, etc.)
cp qatrack/local_settings.example.py qatrack/local_settings.py
# edit qatrack/local_settings.py as needed

# 3. Apply migrations and load demo data
uv run python manage.py migrate
uv run python manage.py loaddata fixtures/demo_data.json

# 4. Run the development server
uv run python manage.py runserver
```

> **A note for AI agents:** the commands throughout this file are prefixed
> with `uv run` rather than assuming an activated virtual environment. Many
> agent tool-call environments start a fresh shell for every command, so an
> activation from a previous step won't carry over — `uv run` re-resolves
> the correct environment each time regardless. Human contributors are of
> course welcome to `source .venv/bin/activate` once and drop the prefix.

---

## Linting and formatting

```bash
uv run ruff check .          # lint
uv run ruff format .         # auto-format
```

Configuration lives in `pyproject.toml` under `[tool.ruff]`.  
Line length is **120 characters**. Quote style is **single quotes**.  
Import ordering is enforced (`ruff` rule set `I`).

---

## Running the tests

The primary, agent-safe way to run the suite is `pytest`, excluding the GUI
(Selenium/browser) tests — these are not yet configured to run headless, so
they will fail or hang in most agent and CI environments:

```bash
uv run pytest -m "not selenium"
```

To run the full suite, including GUI tests (requires a real browser/display):

```bash
uv run pytest
```

`runtests.sh` and `python manage.py test` invoke Django's own test runner,
not pytest — they don't understand the `selenium` marker or `-m` filtering,
and will attempt to run the GUI tests too. Prefer `pytest` directly.

Tests live next to the application code in `tests/` subdirectories inside each
Django app. Write or update tests for every functional change. Do not remove or
disable existing tests.

---

## Coding conventions

- Follow the style of the surrounding code.
- Write clear imperative commit messages. 
- Current maintainer convention is to squash commits aggressively prior to merge, therefore an abundance of commits within a PR is not necessarily a negative
- Keep PRs focused — everyone's time is limited.
- All PRs must target the `develop` branch, **not** `master`.
- Fill in the pull request template completely (`.github/pull_request_template.md`).
- PRs that include tests, documentation updates, and a clear *why* are merged fastest.

### Dependencies

Prefer **LTS releases** for runtime dependencies (Python, Django, Node.js,
etc.) — clinical deployments need predictable upgrade windows. When proposing
a new dependency or version bump, note in the PR description whether it's LTS.

### Language

**English (Canada)** is the lightly preferred written language for code
comments, commit messages, documentation, and user-facing strings. Canadian
English generally follows British spelling conventions (e.g. *behaviour*,
*colour*, *programme*) while using common North American technical vocabulary.
Consistency within a file always takes priority over strict adherence to any
one variant — do not change existing spelling just to match this preference.

Prefer plain, approachable language over dry technical writing in docs,
docstrings, error messages, and UI text — much of the audience is clinical
staff, not developers. Explain the *why*, not just the *what*.

When drafting or editing documentation, reflect the project's actual
values: friendly, welcoming, and patient with contributors new to open
source (see CONTRIBUTING.md). QATrack+ is a Canadian project, and polite,
warm, engaging language is the house style, not an afterthought. Extend
that same good faith to contributors' own words, too — a blunt or curt
issue report or PR comment is often just someone writing plainly in a
second language, not rudeness. Don't read hostility into terse phrasing,
and don't smooth a contributor's own voice into something colder when
quoting or paraphrasing them.

---

## Documentation

Docs are built with Sphinx and live in `docs/`.

```bash
uv run make docs    # from the repo root
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

Two GitHub Actions workflows are **planned but not yet implemented** on
`develop` that would automate part of this process. Until they exist, treat
the mapping below as the manual reference to apply by hand before opening a
PR:

- `.github/workflows/docs-impact.yml` would post an automated heuristic
  comment on every PR listing which doc paths may need attention.
- `.github/workflows/annual-repository-health-review.yml` would create or
  update a yearly issue with dependency-maintenance signals, a pattern-based
  code style review, an AI-driven code style review, and an AI-assisted
  documentation tone review. Once it exists, its findings should be treated
  as intentionally heuristic and may overlap between sections — address them
  incrementally in small, distinct PRs throughout the year rather than all
  at once.

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

## Getting help

- [GitHub Discussions](https://github.com/qatrackplus/qatrackplus/discussions)
- [QATrack+ Google Group](https://groups.google.com/g/qatrack)
- [Project wiki](https://github.com/qatrackplus/qatrackplus/wiki)
- Email: [medphys@crcrewso.ca](mailto:medphys@crcrewso.ca)
