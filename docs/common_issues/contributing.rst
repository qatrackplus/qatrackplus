.. _contributing_issues_guide:

How to Contribute an Issue or Solution
=======================================

Anyone can add a new entry to this section — you don't need to be a developer
or a documentation expert. If you spent time solving a QATrack+ problem that
isn't documented here, please share the solution with the community.

File format
-----------

Each issue lives in its own ``.rst`` file in ``docs/common_issues/``. Use the
template below as a starting point. Delete any section that doesn't apply.

.. code-block:: rst

   .. _my_issue_label:

   Short Title Describing the Problem
   ===================================

   Symptom
   -------

   What the user sees — error messages, unexpected behaviour, broken pages, etc.
   Quote the exact error text where possible.

   .. code-block:: text

      Paste the exact error or log output here.

   Affected versions
   -----------------

   List the QATrack+ versions where this problem occurs, if known.

   Cause
   -----

   Why the problem happens. Keep this brief; it is okay to write
   "Unknown" if you solved the problem without understanding the root cause.

   Solution
   --------

   Step-by-step instructions to fix the problem.

   #. First step.
   #. Second step.

      .. code-block:: bash

         # paste any shell commands here

   #. Third step.

   Verification
   ------------

   How to confirm the problem is resolved.

   See also
   --------

   * Link to the relevant GitHub issue or discussion.
   * Link to the relevant documentation page.

Step-by-step guide
------------------

1. **Fork the repository** on GitHub and clone your fork locally.

2. **Create a branch** from ``Dev``::

      git checkout -b docs/my-issue-solution

3. **Create a new file** in ``docs/common_issues/`` using the template above.
   Name it after the problem, for example ``email_not_sending.rst``.

4. **Add your file** to the ``toctree`` in ``docs/common_issues/index.rst``::

      .. toctree::
         :maxdepth: 1

         contributing
         installation_issues
         your_new_file      ← add this line

5. **Build the docs locally** to check for warnings::

      cd docs
      make html

   Open ``_build/html/index.html`` in a browser and navigate to your new page.

6. **Open a pull request** against the ``Dev`` branch. Describe the problem and
   the environment where you encountered it (OS, QATrack+ version, database).

The bar for these contributions is intentionally low: accuracy matters, style
does not. A maintainer will review and may suggest small improvements before
merging.
