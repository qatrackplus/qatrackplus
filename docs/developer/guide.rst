Developers Guide
================


.. toctree::
   :maxdepth: 3
   :caption: Contents:

   schema


Installing QATrack+ For Development
-----------------------------------

.. todo:: Add docs regarding marking strings for translations


Internationalization & Translation
----------------------------------

.. todo:: Add docs regarding marking strings for translations


Formatting & Style Guide
------------------------

.. todo:: Add docs regarding flake8 and yapf (or Black?)



Running The Test Suite
----------------------

Once you have QATrack+ and its dependencies installed you can run the test
suite from the root QATrack+ directory using the `py.test` command:


.. code-block:: sh

    ./qatrackplus> py.test
    Test session starts (platform: linux, Python 3.6.5, pytest 3.5.0, pytest-sugar 0.9.1)
    Django settings: qatrack.settings (from ini file)
    rootdir: /home/randlet/projects/qatrack/qatrackplus, inifile: pytest.ini
    plugins: sugar-0.9.1, django-3.1.2, cov-2.5.1

    qatrack/accounts/tests.py ✓✓✓                              

For more information on using py.test, refer to the `py.test documentation
<https://pytest.org>`__.


Contributing Code to QATrack+
-----------------------------

In general, to contribute code to QATrack+ you will need to create a fork of
QATrack+ on BitBucket, make your changes, then make a pull request to the main
QATrack+ project.  This process is explained in the `BitBucket documentation
<https://confluence.atlassian.com/bitbucket/forking-a-repository-221449527.html>`__.

Copyright & Licensing
~~~~~~~~~~~~~~~~~~~~~

The author of the code (or potentially their employer) retains the copyright of
their work even when contributing code to QATrack+.  However, unless specified
otherwies, by submitting code to the QATrack+ project you agree to have it
distributed using the same `MIT license
<https://bitbucket.org/tohccmedphys/qatrackplus/src/master/LICENSE>`__ as
QATrack+ uses.
