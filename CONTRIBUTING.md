# Contributing to QATrack+

Thanks for your interest in contributing! QATrack+ is a free and open-source
Django web application for tracking quality control and maintenance activities
at radiation therapy and diagnostic imaging facilities. It's maintained by and
for the medical physics community, and contributions of every size are welcome —
from typo fixes to new features.

Many people who contribute here have only ever worked on one open-source project,
and for some this is their first exposure to open source at all. Please assume
that everyone is acting in good faith and from a desire to help, and extend the
same patience and respect you'd want in return — including with contributors
writing in a second language, whose phrasing may read more bluntly than they
intend. Everyone should feel welcome here. (See the [Code of
Conduct](CODE_OF_CONDUCT.md) for the full version of this.)

This guide gets you from a clone to a merged pull request with as little
guesswork as possible. If anything here is unclear or out of date, that itself is
worth an issue or PR.

By submitting a contribution, you agree that it is licensed under QATrack+'s
[Apache License 2.0](LICENSE), the same license covering the rest of the
project.

If you're using an AI coding tool (Copilot, Claude Code, Cursor, etc.), see
[AGENTS.md](AGENTS.md)'s **AI policy** section for the project's stance on
AI-assisted contributions — in short, AI-generated PRs are welcome, but only
when a human has read, understood, and tested the change. 
Reviewers and maintainers are held to this same standard. 

## Ways to contribute

You don't need to write code to help:

- **Report bugs** or **request features** by opening an issue.
- **Improve the documentation** in the `docs/` folder (see below).
- **Write a tutorial** showing how to use a QATrack+ feature.
- **Translate** the interface into another language — QATrack+ marks its strings
  for translation, and localization is an active area of work.
- **Answer questions** and share your experience in
  [GitHub Discussions](https://github.com/qatrackplus/qatrackplus/discussions).

If you want to contribute code, read on.

## Getting help

For questions about contributing, git, or the codebase, use
[GitHub Discussions](https://github.com/qatrackplus/qatrackplus/discussions) or
the [QATrack+ Google Group](https://groups.google.com/g/qatrack). The
[project wiki](https://github.com/qatrackplus/qatrackplus/wiki) collects FAQs and
community guides. For anything not covered by those channels, email
[medphys@crcrewso.ca](mailto:medphys@crcrewso.ca).

## Reporting bugs

1. Check the [existing issues](https://github.com/qatrackplus/qatrackplus/issues)
   first — your bug may already be reported.
2. Open a new issue and include:
   - QATrack+ version (`Admin › About`)
   - Operating system and Python version
   - Steps to reproduce the problem
   - What you expected to happen vs. what actually happened
   - Any relevant log output (check `logs/` and the Django debug toolbar)

## Suggesting features

Open an issue describing the use case you need to solve, not just the
solution you have in mind. This makes it easier to find the right approach
together.

## Contributing to the documentation

The documentation lives in `docs/` and is built with
[Sphinx](https://www.sphinx-doc.org). Most pages use
[reStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
(`.rst`).

To build the docs locally:

```bash
uv sync --dev          # Sphinx and its extensions are part of the dev group
uv run make docs       # from the repository root
# open docs/_build/html/index.html in your browser
```

While writing, `uv run make docs-autobuild` serves the docs at
<http://127.0.0.1:8008> and rebuilds them as you save (add
`port=8010` to use a different port).

## Contributing code

### Setting up a development environment

The steps below are the short version. [`uv-setup.md`](uv-setup.md) is a
copy-paste quickstart of the same sequence, and the *Developers Guide*
([`docs/developer/guide.rst`](docs/developer/guide.rst)) is the canonical,
fuller treatment — including Windows, the per-engine test settings, and the
Selenium setup.

1. **Fork & clone** the repository.
2. Install dependencies with [uv](https://docs.astral.sh/uv/) (uv creates and
   manages the virtual environment for you — pip + a manually-activated venv
   is only used for production Windows/MS SQL Server deployments that cannot rely on uv):
   ```bash
   uv sync --dev
   ```
3. Install the pre-commit hooks, so lint and correctness checks run automatically
   on each commit:
   ```bash
   uv run pre-commit install
   ```
4. Copy the example settings and configure your local database:
   ```bash
   cp deploy/dev/local_settings.dev.py qatrack/local_settings.py
   cp deploy/dev/local_test_settings.sqlite.py qatrack/local_test_settings.py
   # edit qatrack/local_settings.py
   ```
   `deploy/dev/` has a template per engine (`memory`, `postgres`, `mysql`,
   `mssql`) if you'd rather test against something else - the developer
   guide's *`local_test_settings.py` templates* table says what each one
   needs.
5. Apply migrations and load fixture data:
   ```bash
   mkdir db
   uv run python manage.py migrate
   uv run python manage.py createcachetable
   uv run python manage.py loaddata fixtures/defaults/*/*.json
   uv run python manage.py collectstatic --noinput
   ```
   If you also want the in-memory database available (it is the fastest way
   to run the suite), copy that template alongside the first:
   ```bash
   cp deploy/dev/local_test_settings.memory.py qatrack/local_test_settings.memory.py
   ```
6. Start the development server:
   ```bash
   uv run python manage.py runserver
   ```
There is no frontend build step at the moment, and Node.js is not needed —
see the note in [AGENTS.md](AGENTS.md#getting-started). One is expected back
no earlier than 4.1.

### Coding guidelines

Please attempt your best effort at these guidelines, but don't be afraid if you miss something. You are human, so are we, and it's the maintainers' responsibility to bring your valued contributions to the community as a whole. 

- Aim for **engaging, approachable prose** in comments, docstrings, and
  documentation. QATrack+ is used by clinicians as well as developers — write
  as if you are guiding a knowledgeable colleague, not drafting a specification.
  Explain the *why* alongside the *what*, and favour plain language over
  unnecessary jargon.
- Follow existing code style. The project uses [ruff](https://docs.astral.sh/ruff/)
  for linting, formatting, and import ordering:
  ```bash
  uv run ruff check .                 # lint
  uv run ruff format <files you changed>   # auto-format
  ```
  Repo-wide `ruff format` hasn't been applied yet, so don't run it across the
  whole codebase — that would surface a large, unrelated reformatting diff.
  Scope it to the files you actually touched.
- Write or update tests for every functional change. Tests live alongside the
  application code in `tests/` subdirectories. If you feel that your changes require testing you are unsure of how to implement, reach out. We are here to help
- Keep commits focused. One logical change per commit makes review easier and history cleaner. PRs aggressively squash commits so lean towards being too clear. 
- Try to use clear commit messages: start with a short imperative summary
  (`Fix email notification when recipients list is empty`), then add a blank
  line and more detail if needed.

### Running the tests

```bash
uv run pytest
```

GUI (Selenium/browser) tests are skipped by default, since they need a real
Chromium or Firefox on the host. Add `--run-selenium` to also run them.
`python manage.py test` uses Django's own test runner, not pytest, and
doesn't support marker filtering or `--run-selenium` — prefer `pytest`
directly. See
[AGENTS.md](AGENTS.md#running-the-tests) for more detail.

To test against a specific database engine without touching your usual
`qatrack/local_test_settings.py`, use `make test-sqlite`/`test-memory`/
`test-postgres`/`test-mysql`/`test-mssql` (create
`qatrack/local_test_settings.<engine>.py` first from the matching
`deploy/dev/` template). `make test-integration` provisions a brand-new
sqlite database the way a real deployment would and runs the suite against
it directly.

Before opening a PR, it's also worth running the full pre-commit suite
against the whole codebase, not just your changed files:

```bash
uv run pre-commit run --all-files
```

### Opening a pull request

1. Push your branch to your fork.
2. Open a PR against the `develop` branch (not `master`).
3. Fill in the pull request template completely.
4. Expect review feedback — don't be discouraged if changes are requested.
   This is normal and how any project stays healthy.
5. If you used an AI coding tool, make sure you've personally read, understood,
   and tested the diff before opening a Final PR — see
   [AGENTS.md](AGENTS.md#ai-policy)'s AI policy. A Final PR that reads as
   AI-generated with no evidence of that will be closed with a pointer to this
   policy, not reviewed line by line.

PRs that include tests, documentation updates, and a clear description of *why*
the change is needed are merged fastest.

## Code of conduct

This project has a [Code of Conduct](CODE_OF_CONDUCT.md). By participating you
agree to abide by it. The short version: be kind, assume good faith, and treat
everyone the way you'd want to be treated. If you witness or experience
unacceptable behaviour, contact the maintainer at
[medphys@crcrewso.ca](mailto:medphys@crcrewso.ca).
