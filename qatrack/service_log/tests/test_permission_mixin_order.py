"""A declared `permission_required` must actually be consulted.

Django resolves `dispatch()` by method order, so a permission mixin listed *after* a
generic view base never runs - `View.dispatch` wins, and `permission_required` sits
there looking enforced. `DeleteServiceEvent` had exactly that shape: the permission was
declared, and any logged-in user could use the view.

**The mistake is invisible where it is made.** The class reads fine, the attribute is
right, and the only symptom is an absence. Nothing fails. So this does not test one
class - it walks every view in the project that declares `permission_required` and
asserts the declaration can take effect. A future view written with the bases in the
wrong order fails here, wherever it is.

Note what this does *not* claim: that each permission is the correct one, or that the
view is reachable only by the right people. It claims the narrower thing that was false -
that the declaration is wired up at all.
"""

import inspect

from braces.views._access import (
    MultiplePermissionsRequiredMixin as BracesMultiplePermissionsRequiredMixin,
)
from braces.views._access import PermissionRequiredMixin as BracesPermissionRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin as DjangoPermissionRequiredMixin
from django.test import TestCase
from django.views.generic import DeleteView, FormView, View

# **Both families, and this is the point of the file.** QATrack+ mostly uses
# `braces.views.PermissionRequiredMixin`, which is *not* a subclass of Django's
# `AccessMixin`. The first version of this sweep tested only Django's, so it skipped
# every class it was written to check and passed while measuring nothing. It was caught
# by the one test here that names a class explicitly.
#
# **And these are the mixins that check a permission, not the ones that check a
# login.** The second version swept for any *access* mixin, which let a
# `LoginRequiredMixin` in front of the view base vouch for a
# `PermissionRequiredMixin` behind it: the login was enforced, the permission was not,
# and the sweep passed. @copilot found that on c#12. So the names below are the three
# classes that actually test a permission, and nothing else counts as one.
PERMISSION_MIXINS = (
    DjangoPermissionRequiredMixin,
    BracesPermissionRequiredMixin,
    BracesMultiplePermissionsRequiredMixin,
)


def permission_mixins_in(cls):
    """The permission mixins in `cls`'s MRO, in MRO order.

    Identity against `PERMISSION_MIXINS` rather than `issubclass`, because a project
    mixin built on one of them keeps its base in the MRO *ahead of the view bases* -
    Python linearises a class before its own bases - so the canonical class is the
    conservative thing to measure.
    """
    return [c for c in cls.__mro__ if c in PERMISSION_MIXINS]


def view_classes_declaring_a_permission():
    """Every class under `qatrack` that is a View and declares `permission_required`."""
    import importlib
    import pkgutil

    import qatrack

    found = {}
    for module in pkgutil.walk_packages(qatrack.__path__, prefix='qatrack.'):
        name = module.name
        # migrations are not views; the accel tool is a standalone script set
        if '.migrations' in name or 'accel_migration_tool' in name:
            continue
        try:
            mod = importlib.import_module(name)
        except Exception:
            # An import error is not this test's business - other tests cover that,
            # and skipping keeps one broken optional module from hiding every view.
            continue
        for attr, obj in vars(mod).items():
            if not inspect.isclass(obj) or not issubclass(obj, View):
                continue
            if 'permission_required' not in {k for c in obj.__mro__ for k in vars(c)}:
                continue
            if getattr(obj, 'permission_required', None) in (None, ''):
                continue
            found['%s.%s' % (obj.__module__, obj.__name__)] = obj
    return found


def dispatch_owner(cls):
    return next(c for c in cls.__mro__ if 'dispatch' in vars(c))


def unenforced_reason(cls):
    """Why `cls`'s declared permission cannot be checked, or None if it can.

    Two ways it cannot be. The view mixes in nothing that reads
    `permission_required`, or it does and that mixin sits behind the generic view
    base: `View.dispatch` does not call `super()`, so it is where the chain stops.
    """
    mixins = permission_mixins_in(cls)
    if not mixins:
        return "declares permission_required but mixes in no permission mixin"

    mro = cls.__mro__
    if View in mro and min(mro.index(m) for m in mixins) > mro.index(View):
        return (
            "%s sits behind the generic View base, whose dispatch does not call "
            "super(); dispatch enters at %s" % (mixins[0].__name__, dispatch_owner(cls).__name__)
        )
    return None


class TestPermissionMixinsActuallyRun(TestCase):

    def test_there_are_views_to_check(self):
        """Guards the sweep itself: an empty sweep would pass everything below."""
        found = view_classes_declaring_a_permission()
        assert len(found) > 20, "only found %d views declaring permission_required" % len(found)

    def test_every_declared_permission_is_reachable_by_dispatch(self):
        offenders = []
        for label, cls in sorted(view_classes_declaring_a_permission().items()):
            problem = unenforced_reason(cls)
            if problem:
                offenders.append("%s: %s" % (label, problem))

        assert not offenders, (
            "these views declare a permission that is never checked:\n  " + "\n  ".join(offenders)
        )

    def test_the_sweep_rejects_a_view_whose_permission_mixin_is_behind_the_view(self):
        """The negative control, without which the test above proves nothing.

        This is the shape @copilot named on c#12: a login mixin in front, which the
        earlier version of the sweep accepted on the permission mixin's behalf, and the
        permission mixin itself behind `DeleteView`, where `View.dispatch` - which does
        not call `super()` - ends the chain before it is reached.

        It is defined inside the test rather than at module level on purpose: the sweep
        walks every module under `qatrack`, test modules included, so a deliberately
        broken view left at module scope would be swept up and fail the real test.
        """
        from braces.views import LoginRequiredMixin

        class MisorderedView(
            LoginRequiredMixin, DeleteView, FormView, BracesPermissionRequiredMixin
        ):
            permission_required = 'service_log.delete_serviceevent'

        assert unenforced_reason(MisorderedView), (
            "the sweep accepted a view whose permission mixin sits behind View.dispatch"
        )

        class OrderedView(
            BracesPermissionRequiredMixin, LoginRequiredMixin, DeleteView, FormView
        ):
            permission_required = 'service_log.delete_serviceevent'

        assert unenforced_reason(OrderedView) is None, (
            "the sweep rejected a correctly ordered view: %s" % unenforced_reason(OrderedView)
        )

    def test_a_declaration_with_no_permission_mixin_at_all_is_reported(self):
        """`permission_required` on a view that mixes in nothing to read it is a
        declaration with no effect, and reads exactly like an enforced one."""

        class DeclaredButUnmixed(DeleteView):
            permission_required = 'service_log.delete_serviceevent'

        assert unenforced_reason(DeclaredButUnmixed) == "declares permission_required but " \
            "mixes in no permission mixin"

    def test_delete_service_event_specifically(self):
        """The one that was wrong, named so a reader can find the history."""
        from qatrack.service_log.views import DeleteServiceEvent

        assert unenforced_reason(DeleteServiceEvent) is None
        assert permission_mixins_in(DeleteServiceEvent), "no permission mixin at all"
        assert DeleteServiceEvent.permission_required == 'service_log.delete_serviceevent'
        # FormView must survive the reorder - the view's delete form depends on it
        assert any(c.__name__ == 'FormView' for c in DeleteServiceEvent.__mro__)
        assert DeleteServiceEvent.form_class.__name__ == 'ServiceEventDeleteForm'


class TestDeleteServiceEventRefusesTheWrongUser(TestCase):
    """And the behaviour, not only the wiring.

    The existing admin tests use a superuser throughout, which is why this went
    unnoticed: a superuser passes every permission check, so an absent check looks
    identical to a satisfied one.
    """

    def setUp(self):
        from django.contrib.auth.models import Permission, User

        from qatrack.service_log.tests import utils as sl_utils

        self.service_event = sl_utils.create_service_event()
        self.url = '/service-log/delete/%d/' % self.service_event.pk

        self.plain = User.objects.create_user('plain-sl', 'p@e.com', 'pw')
        self.allowed = User.objects.create_user('allowed-sl', 'a@e.com', 'pw')
        self.allowed.user_permissions.add(
            Permission.objects.get(content_type__app_label='service_log',
                                   codename='delete_serviceevent'))
        self.allowed = User.objects.get(pk=self.allowed.pk)

    def resolve(self):
        """The URL name, rather than a hand-built path that may not match the conf."""
        from django.urls import NoReverseMatch, reverse

        for name in ('se_delete',):
            try:
                return reverse(name, kwargs={'pk': self.service_event.pk})
            except NoReverseMatch:
                continue
        return None

    def test_a_user_without_the_permission_is_refused(self):
        url = self.resolve()
        if url is None:
            self.skipTest("could not resolve the delete URL by name")
        self.client.force_login(self.plain)
        assert self.client.get(url).status_code == 403

    def test_a_user_with_the_permission_is_not_refused(self):
        """Without this the test above would pass if the view were simply broken."""
        url = self.resolve()
        if url is None:
            self.skipTest("could not resolve the delete URL by name")
        self.client.force_login(self.allowed)
        assert self.client.get(url).status_code != 403
