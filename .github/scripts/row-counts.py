"""Row counts for the tables an upgrade must carry, one `name=count` per line.

Read by `manage.py shell` on stdin, before and after the Docker upgrade job's
upgrade, and the two outputs are compared with `diff`. It runs under the release
being upgraded *from* as well as the one being upgraded to, so it uses only
models and managers that both releases have.
"""

from django.contrib.auth.models import User

from qatrack.faults.models import Fault
from qatrack.qa.models import (
    Test,
    TestInstance,
    TestList,
    TestListInstance,
    UnitTestCollection,
)
from qatrack.service_log.models import ServiceEvent
from qatrack.units.models import Unit

for name, manager in [
    ("users", User.objects),
    ("units", Unit.objects),
    ("testlists", TestList.objects),
    ("tests", Test.objects),
    ("utcs", UnitTestCollection.objects),
    ("testlistinstances", TestListInstance.objects),
    ("testinstances", TestInstance.objects),
    ("serviceevents", ServiceEvent.objects),
    ("faults", Fault.objects),
]:
    print("%s=%d" % (name, manager.count()))
