# Contributing to QATrack+

Thanks for your interest in contributing! QATrack+ is a free and open-source
Django web application for tracking quality control and maintenance activities
at radiation therapy and diagnostic imaging facilities. It's maintained by and
for the medical physics community, and contributions of every size are welcome —
from typo fixes to new features.

Many people who contribute here have only ever worked on one open-source project,
and for some this is their first exposure to open source at all. Please assume
that everyone is acting in good faith and from a desire to help, and extend the
same patience and respect you'd want in return. Everyone should feel welcome here.

This guide gets you from a clone to a merged pull request with as little
guesswork as possible. If anything here is unclear or out of date, that itself is
worth an issue or PR.

## Ways to contribute

You don't need to write code to help:

- **Report bugs** or **request features** by opening an issue.
- **Improve the documentation** in the `docs/` folder (see below).
- **Write a tutorial** showing how to use a QATrack+ feature.
- **Translate** the interface into another language — QATrack+ marks its strings
  for translation, and localization is an active area of work.
- **Answer questions** and share your experience in
  [GitHub Discussions](https://github.com/qatrackplus/qatrackplus/discussions).
- **Share known issues and solutions** in the
  [Common Issues & Solutions](docs/common_issues/) documentation section.

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
2. Open a new issue and fill in the bug report template. Include:
   - QATrack+ version (`Admin › About`)
   - Operating system and Python version
   - Steps to reproduce the problem
   - What you expected to happen vs. what actually happened
   - Any relevant log output (check `logs/` and the Django debug toolbar)

## Suggesting features

Open an issue and use the feature request template. Describe the use case you
need to solve, not just the solution you have in mind. This makes it easier to
find the right approach together.

## Contributing to the documentation

The documentation lives in `docs/` and is built with
[Sphinx](https://www.sphinx-doc.org). Most pages use
[reStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
(`.rst`).

To build the docs locally:

```bash
pip install -r requirements/docs.txt   # or: pip install sphinx
cd docs
make html
# open _build/html/index.html in your browser
```

### Contributing to the Common Issues & Solutions section

The [Common Issues & Solutions](docs/common_issues/) section collects problems
that users encounter repeatedly along with their solutions. Community members
are strongly encouraged to contribute here — you don't need to be a developer.

**To add a new issue/solution:**

1. Fork the repository and create a branch:
   ```bash
   git checkout -b docs/my-issue-fix
   ```
2. Copy an existing entry from `docs/common_issues/` as a template.
3. Give your file a short, descriptive name, for example
   `email_not_sending.rst` or `missing_migrations.rst`.
4. Follow the format used by other files in that folder:
   - **Symptom** — what the user sees
   - **Cause** — why it happens (keep this brief if you're unsure)
   - **Solution** — step-by-step fix
   - **See also** — links to related docs, issues, or discussion threads
5. Add your new file to the `toctree` in `docs/common_issues/index.rst`.
6. Build the docs locally to confirm there are no warnings.
7. Open a pull request. The bar for these contributions is intentionally low —
   accuracy matters, style does not.

## Contributing code

### Setting up a development environment

1. **Fork & clone** the repository.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate          # Windows: venv\Scripts\activate
   pip install -r requirements/dev.txt
   ```
3. Copy the example settings and configure your local database:
   ```bash
   cp qatrack/local_settings.example.py qatrack/local_settings.py
   # edit qatrack/local_settings.py
   ```
4. Apply migrations and load fixture data:
   ```bash
   python manage.py migrate
   python manage.py loaddata fixtures/demo_data.json
   ```
5. Start the development server:
   ```bash
   python manage.py runserver
   ```

### Coding guidelines

- Follow existing code style. The project uses
  [flake8](https://flake8.pycqa.org/) for linting and
  [isort](https://pycqa.github.io/isort/) for import ordering.
- Write or update tests for every functional change. Tests live alongside the
  application code in `tests/` subdirectories.
- Keep commits focused. One logical change per commit makes review easier and
  history cleaner.
- Use clear commit messages: start with a short imperative summary
  (`Fix email notification when recipients list is empty`), then add a blank
  line and more detail if needed.
- Aim for **engaging, approachable prose** in comments, docstrings, and
  documentation. QATrack+ is used by clinicians as well as developers — write
  as if you are guiding a knowledgeable colleague, not drafting a specification.
  Explain the *why* alongside the *what*, and favour plain language over
  unnecessary jargon.

### Running the tests

```bash
python manage.py test
# or use the helper script:
bash runtests.sh
```

### Opening a pull request

1. Push your branch to your fork.
2. Open a PR against the `Dev` branch (not `master`).
3. Fill in the pull request template completely.
4. Expect review feedback — don't be discouraged if changes are requested.
   This is normal and how the project stays healthy.

PRs that include tests, documentation updates, and a clear description of *why*
the change is needed are merged fastest.

## Code of conduct

This project has a [Code of Conduct](CODE_OF_CONDUCT.md). By participating you
agree to abide by it. The short version: be kind, assume good faith, and treat
everyone the way you'd want to be treated. If you witness or experience
unacceptable behaviour, contact the maintainer at
[medphys@crcrewso.ca](mailto:medphys@crcrewso.ca).
