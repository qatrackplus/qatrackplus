"""Make every configured language use QATrack+'s date formats, not Django's.

``FORMAT_MODULE_PATH`` points Django here, and it resolves formats by importing
``qatrack.formats.<locale>.formats``. The shipped languages have such a module -
each a one-line import of :mod:`qatrack.formats.base` - so they all agree, which
is the intent: a date should not change meaning because someone switched the
interface language.

**A language added the way the documentation describes has no such module.**
``docs/tutorials/internationalization/add_language.rst`` covers translations and
says nothing about format modules, because until the formats became configurable
there was nothing to add. Django then falls through to its own
``django.conf.locale.<locale>.formats``, and the result is the worst of the two
possible failures: the page still tells the browser the configured format -
``siteConfig`` is rendered from the QATrack+ settings - while the server parses
and writes with Django's locale conventions. For German that is ``%d.%m.%Y``
against a configured ``%Y-%m-%d``, so a date picker sends one thing, the server
reads another, **and nothing raises.** The date is simply wrong.

So the gap is filled here instead of being left to whoever adds a language:
every language in ``settings.LANGUAGES`` gets a format module, and
:mod:`qatrack.formats.base` is what it resolves to.

A language whose module exists on disk is left alone, so the shipped ones keep
working exactly as before and a deployer who writes their own
``qatrack/formats/de/formats.py`` still wins.
"""

import sys
import types
from importlib.util import find_spec


def _already_on_disk(module_name):
    """True if `module_name` can be imported normally, so we must not shadow it."""
    try:
        return find_spec(module_name) is not None
    except (ImportError, AttributeError, ValueError):
        # A missing parent package raises rather than returning None.
        return False


def register_format_modules():
    """Give every configured language a format module pointing at `base`.

    Idempotent, and safe to call before or after Django's format cache is
    warm - the caller resets that cache if it needs to.
    """
    from django.conf import settings
    from django.utils.translation import to_locale

    from qatrack.formats import base

    registered = []

    for code, _name in getattr(settings, 'LANGUAGES', []) or []:
        locale = to_locale(code)

        # Django tries the full locale and then the bare language, so filling
        # both means `de` covers `de-at` as well without naming it.
        for name in dict.fromkeys([locale, locale.split('_')[0]]):
            package_name = '%s.%s' % (__name__, name)
            formats_name = '%s.formats' % package_name

            if formats_name in sys.modules or _already_on_disk(formats_name):
                continue

            package = sys.modules.get(package_name)
            if package is None:
                package = types.ModuleType(package_name)
                # No __path__: this is a plain module standing in for a
                # package, which is all `import_module` needs once the child
                # is in sys.modules.
                sys.modules[package_name] = package

            sys.modules[formats_name] = base
            setattr(package, 'formats', base)
            registered.append(formats_name)

    return registered
