"""The failure-screenshot hook, tested without a browser.

A screenshot only ever matters when a GUI test has already failed, so a
broken hook is discovered at the worst possible moment - in CI, when the
picture is the only evidence of what the page looked like. Nothing else
would notice: the hook depends on pytest internals, on tearDown running
before the report hook, and on the name `_failure_screenshot_png`, and any
of those can change without a test going red.

These cover the decision-and-write half, which is the part that breaks
silently. The browser's own ability to produce a PNG is checked separately,
inside a live session, by SeleniumTests.test_driver_can_screenshot.
"""
import pathlib
import types

import pytest

import conftest

# 8-byte PNG signature, enough to prove the bytes were written through
# unmodified rather than re-encoded.
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'
FAKE_PNG = PNG_MAGIC + b'sentinel'


def _report(when='call', failed=True):
    return types.SimpleNamespace(when=when, failed=failed)


def _outcome(report):
    return types.SimpleNamespace(get_result=lambda: report)


def _item(nodeid, instance):
    return types.SimpleNamespace(nodeid=nodeid, instance=instance)


def _run(item, report):
    """Drive the hookwrapper the way pytest does."""
    gen = conftest.pytest_runtest_makereport(item, call=None)
    next(gen)
    try:
        gen.send(_outcome(report))
    except StopIteration:
        pass


@pytest.fixture(autouse=True)
def _screenshot_dir(tmp_path, monkeypatch):
    target = tmp_path / 'selenium-screenshots'
    monkeypatch.setattr(conftest, 'SCREENSHOT_DIR', target)
    return target


class TestFailureScreenshotIsWritten:

    def test_a_failed_test_writes_its_screenshot(self, _screenshot_dir):
        instance = types.SimpleNamespace(_failure_screenshot_png=FAKE_PNG)
        _run(_item('qatrack/qa/tests/test_selenium.py::TestPerformQC::test_x', instance),
             _report())

        written = list(_screenshot_dir.glob('*.png'))
        assert len(written) == 1, written
        assert written[0].read_bytes() == FAKE_PNG

    def test_the_file_is_named_after_the_test(self, _screenshot_dir):
        instance = types.SimpleNamespace(_failure_screenshot_png=FAKE_PNG)
        _run(_item('qatrack/qa/tests/test_selenium.py::TestPerformQC::test_x', instance),
             _report())

        name = list(_screenshot_dir.glob('*.png'))[0].name
        # Recoverable back to the node id: no separators left that would
        # nest it into directories, and the class and test still present.
        assert '/' not in name and '::' not in name
        assert 'TestPerformQC' in name and 'test_x' in name

    def test_the_directory_is_created_on_demand(self, _screenshot_dir):
        assert not _screenshot_dir.exists()
        instance = types.SimpleNamespace(_failure_screenshot_png=FAKE_PNG)
        _run(_item('a.py::T::t', instance), _report())
        assert _screenshot_dir.is_dir()

    def test_it_reads_the_attribute_tearDown_sets(self):
        """Pins the name the two halves agree on."""
        import inspect

        from qatrack.qatrack_core.tests.live import SeleniumTests

        assert '_failure_screenshot_png' in inspect.getsource(SeleniumTests.tearDown)
        assert '_failure_screenshot_png' in inspect.getsource(conftest.pytest_runtest_makereport)


class TestNothingIsWrittenOtherwise:

    def test_a_passing_test_writes_nothing(self, _screenshot_dir):
        instance = types.SimpleNamespace(_failure_screenshot_png=FAKE_PNG)
        _run(_item('a.py::T::t', instance), _report(failed=False))
        assert not _screenshot_dir.exists()

    @pytest.mark.parametrize('when', ['setup', 'teardown'])
    def test_only_the_call_phase_is_captured(self, when, _screenshot_dir):
        """A teardown-phase failure would otherwise overwrite the real one."""
        instance = types.SimpleNamespace(_failure_screenshot_png=FAKE_PNG)
        _run(_item('a.py::T::t', instance), _report(when=when))
        assert not _screenshot_dir.exists()

    def test_a_non_gui_test_is_unaffected(self, _screenshot_dir):
        """No instance at all - an ordinary function-based test."""
        _run(types.SimpleNamespace(nodeid='a.py::test_plain', instance=None), _report())
        assert not _screenshot_dir.exists()


class TestFallbackWhenTearDownDidNotRun:
    """A failure in setUp or setUpClass leaves nothing captured."""

    def test_it_asks_the_live_driver(self, _screenshot_dir):
        driver = types.SimpleNamespace(get_screenshot_as_png=lambda: FAKE_PNG)
        instance = types.SimpleNamespace(driver=driver)   # no _failure_screenshot_png
        _run(_item('a.py::T::t', instance), _report())
        assert list(_screenshot_dir.glob('*.png'))[0].read_bytes() == FAKE_PNG

    def test_no_driver_means_no_file_and_no_error(self, _screenshot_dir):
        _run(_item('a.py::T::t', types.SimpleNamespace()), _report())
        assert not _screenshot_dir.exists()

    def test_a_driver_that_raises_is_swallowed(self, _screenshot_dir):
        def boom():
            raise RuntimeError('session deleted')

        instance = types.SimpleNamespace(driver=types.SimpleNamespace(get_screenshot_as_png=boom))
        _run(_item('a.py::T::t', instance), _report())
        assert not _screenshot_dir.exists()


class TestSavingNeverMasksTheRealFailure:

    def test_an_unwritable_directory_does_not_raise(self, monkeypatch, tmp_path):
        """The test has already failed; losing the evidence is the lesser harm."""
        monkeypatch.setattr(conftest, 'SCREENSHOT_DIR', tmp_path / 'nope')

        def denied(*a, **k):
            raise OSError('read-only file system')

        monkeypatch.setattr(pathlib.Path, 'mkdir', denied)
        instance = types.SimpleNamespace(_failure_screenshot_png=FAKE_PNG)
        _run(_item('a.py::T::t', instance), _report())   # must not raise
