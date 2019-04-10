from django.test import TestCase
from django.utils import timezone

from qatrack.units import models


class TestUnits(TestCase):

    def test_auto_set_number(self):
        ut = models.UnitType.objects.create(name="UT")
        models.Unit.objects.create(name="U1", type=ut, number=1, date_acceptance=timezone.now())
        u2 = models.Unit.objects.create(name="U2", type=ut, date_acceptance=timezone.now())
        assert u2.number == 2
