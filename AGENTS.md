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


Every pull request requires a human owner to understand and explain the 
included code fully. Concretely, that person must:

1. **Have read and understood the diff** — not just the AI's summary of it,
   the actual lines changed.
2. **Be able to explain the reasoning** behind each non-trivial decision if
   asked during review.
3. **Have run the tests locally** and confirmed they pass.
4. **Take responsibility** for the change's correctness and safety.

Conversely, the maintainers promise:

1. **Embody the spirit of this document** Maintainers will not rely on AI as a final review tool. 
2. **Be honest and transparent** PR review comments will come from a human except where explicitly mentioned. 
3. **Respect contributors** Contributions are valued, Each maintainer personally commits to manually reviewing each code change, and completing the associated PR checklists.  

Use AI as much as you like to get there — genuinely, that's what it's for.
Just make sure a human reads what comes out before it ships: Draft PRs are ignored
unless otherwise requested. A Final PR opened autonomously by an AI agent, 
with no human having read and validated every line, 
**will be closed with a pointer to this policy — reopen once a human has read
the diff.** (See CONTRIBUTING.md's [Opening a pull
request](CONTRIBUTING.md#opening-a-pull-request) section too.)

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
| **Frontend** | Server-rendered Django templates with HTMX and jQuery. No build step, no Node.js — a Vue/Vite bundle was retired and is expected back no earlier than 4.1 |
| **Linter / formatter** | [ruff](https://docs.astral.sh/ruff/) |
| **Test runner** | pytest (`uv run pytest` — GUI tests are skipped by default, see [Running the tests](#running-the-tests)) |
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
```

> **TODO:** `requirements/dev.txt` is generated from the `dev` dependency
> group, but the only documented pip-install path in this project is
> production Windows/MS SQL Server deployments (see the Package manager
> row above and *Getting started* below) — that install actually needs
> the `win` + `mssql` extras, not `dev`. Reconciling the file's contents
> (and likely its name) with that purpose is tracked for a follow-up PR;
> until then, treat this file as stale for deployment purposes.
>
> Concretely, it is stale for tooling too: it still pins `flake8`, `isort`,
> `yapf` and `pep8`, none of which are in the `dev` dependency group any
> more — ruff replaced all of them (see *Code style* below, and
> `docs/developer/guide.rst`). Do not take that file as evidence those
> tools are still in use; they are not.

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
cp deploy/dev/local_settings.dev.py qatrack/local_settings.py
cp deploy/dev/local_test_settings.sqlite.py qatrack/local_test_settings.py
# edit qatrack/local_settings.py as needed

# 3. Apply migrations and load demo data
mkdir db
uv run python manage.py migrate
uv run python manage.py createcachetable
uv run python manage.py loaddata fixtures/defaults/*/*.json
uv run python manage.py collectstatic --noinput

# 4. Run the development server
uv run python manage.py runserver
```

> **There is no frontend build step at present.** QATrack+ had a Vue 3 +
> Vite bundle, and the faults UI now uses server-rendered HTMX with jQuery
> instead; `package.json` went with it. Node.js is **not** a prerequisite for
> anything today — `npm ci` would fail, because there is no manifest to read.
>
> A frontend build is expected to return no earlier than 4.1. The release
> workflow already tests for `package.json` and runs the Node steps only if
> it is there, so nothing needs changing here when it comes back.

`local_test_settings.sqlite.py` is one of five ready-made templates under
`deploy/dev/` (`sqlite`, `memory`, `postgres`, `mysql`, `mssql`) - copy a
different one instead to run the suite against a different engine. The
developer guide's *`local_test_settings.py` templates* table says what each
one requires (a reachable server and credentials, for the three that need
them). Copying `local_test_settings.memory.py` to
`qatrack/local_test_settings.memory.py` as well makes `make test-memory` work
with no further setup. See [Running the tests](#running-the-tests) for
`make test-<engine>`.

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
```

Repo-wide `ruff format` hasn't been applied yet, so running it across the
whole codebase will surface a large, unrelated reformatting diff — scope
`ruff format` to just the files you actually changed instead of running it
repo-wide.

Configuration lives in `pyproject.toml` under `[tool.ruff]`.  
Line length is **120 characters**. Quote style is **single quotes**.  
Import ordering is enforced (`ruff` rule set `I`).

Before opening a PR, also run the full pre-commit suite:

```bash
uv run pre-commit run --all-files
```

---

## Running the tests

The primary, agent-safe way to run the suite is plain `pytest` — GUI
(Selenium/browser) tests are skipped automatically, since they need a real
browser (Chromium or Firefox) on the host, which most agent sandboxes won't
have available (this project's own CI does - see `.github/workflows/ci.yml`'s
dedicated `selenium-tests`/`selenium-tests-windows` jobs, which run on
GitHub-hosted runners that come with Chrome/Chromium/Firefox pre-installed):

```bash
uv run pytest
```

To also run the GUI tests (requires Chromium or Firefox installed -
headless mode needs no display; see `SELENIUM_BROWSER` and
`SELENIUM_HEADLESS` in `qatrack/settings.py`):

```bash
uv run pytest --run-selenium
```

`-m selenium` also still works to run *only* the GUI tests - it bypasses
the automatic skip the same way `--run-selenium` does.

`-m "not selenium"` also still works to exclude them explicitly, but is
**deprecated**: it needs quoting on every shell for no benefit now that
plain `pytest` does the same thing with nothing to type at all. It emits a
`PytestDeprecationWarning` and will be removed in QATrack+ 4.2 - use plain
`pytest` instead.

`python manage.py test` invokes Django's own test runner, not pytest — it
doesn't understand the `selenium` marker, `-m` filtering, or
`--run-selenium`, and will attempt to run the GUI tests too. Prefer
`pytest` directly.

`make test-<engine>` (`sqlite`, `memory`, `postgres`, `mysql`, `mssql`) runs
the suite against a specific database engine without disturbing whatever
`qatrack/local_test_settings.py` you normally use day to day - it swaps in
`qatrack/local_test_settings.<engine>.py` (create it first from the matching
`deploy/dev/local_test_settings.<engine>.py` template) for the run, then
restores your previous file afterward regardless of whether the tests
passed. `make test-integration` goes a step further: provisions a brand-new
sqlite database exactly the way a fresh deployment would (migrate,
createcachetable, collectstatic, createsuperuser) and runs the suite with
`--reuse-db` directly against it, so the whole deployment sequence is
exercised for real, not just a disposable test database.

Tests live next to the application code in `tests/` subdirectories inside each
Django app. Write or update tests for every functional change. Do not remove or
disable existing tests.

### Checking migrations: `--dry-run` or `--check`, not both by habit

These answer different questions, and picking the wrong one is quiet rather
than loud:

```
python manage.py makemigrations --dry-run    # prints what it would create
python manage.py makemigrations --check      # exits 1 if anything is missing
```

Django 4.1 made `--check` **silent**. It sets an exit status and prints
nothing, so `--check --dry-run` at a terminal shows you an empty result that
reads exactly like "nothing to generate".

- Working by hand, or following the PR checklist? Use `--dry-run` and read the
  output.
- Writing a hook, a CI step or a script? Use `--check` and read `$?`.

If you script it, mind the shell too: in `makemigrations --check | tail`, `$?`
belongs to `tail`, not to Django, and the pipeline reports success no matter
what Django decided.

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
*colour*, *licence* as a noun) while using common North American technical
vocabulary — notably, *program* stays *program* in the software sense; unlike
British usage, Canadian English doesn't switch to *programme* there.
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
developer workflow (`docs/developer/`, `AGENTS.md`, `CONTRIBUTING.md`,
`uv-setup.md`) and the installation guides (`docs/install/`) overlap on topics
such as Python version, Node.js version, the package manager, how to activate
(or skip activating) the virtual environment, how to run the tests, and how to
build the docs. Whenever any one of these is updated, the others should be
reviewed for consistency. The four developer-facing files in particular say
much the same thing in four places, so a change to any one of them is very
likely to need a matching change in the others.

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
| `AGENTS.md` | `docs/developer/`, `docs/install/`, `CONTRIBUTING.md`, `uv-setup.md` |
| `docs/developer/` | `docs/install/`, `AGENTS.md`, `CONTRIBUTING.md`, `uv-setup.md` |
| `docs/install/` | `docs/developer/`, `AGENTS.md` |
| `CONTRIBUTING.md` | `AGENTS.md`, `docs/developer/`, `uv-setup.md` |
| `uv-setup.md` | `AGENTS.md`, `CONTRIBUTING.md`, `docs/developer/` |
| `Makefile` | `AGENTS.md`, `CONTRIBUTING.md`, `docs/developer/guide.rst` |
| `conftest.py` | `AGENTS.md`, `CONTRIBUTING.md`, `docs/developer/guide.rst` |

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
