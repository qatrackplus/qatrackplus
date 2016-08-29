from django.test import TestCase
from django.core import mail
from qatrack.qa import models, signals
import qatrack.qa.tests.utils as utils
from .models import NotificationSubscription, TOLERANCE


#============================================================================
class TestEmailSent(TestCase):

    #----------------------------------------------------------------------
    def setUp(self):

        self.tests = []

        self.ref = models.Reference(type=models.NUMERICAL, value=100.)
        self.tol = models.Tolerance(type=models.PERCENT, act_low=-3, tol_low=-2, tol_high=2, act_high=3)
        self.ref.created_by = utils.create_user()
        self.tol.created_by = utils.create_user()
        self.ref.modified_by = utils.create_user()
        self.tol.modified_by = utils.create_user()
        self.values = [None, None, 96, 97, 100, 100]

        self.statuses = [utils.create_status(name="status%d" % x, slug="status%d" % x) for x in range(len(self.values))]

        self.test_list = utils.create_test_list()
        for i in range(6):
            test = utils.create_test(name="name%d" % i)
            self.tests.append(test)
            utils.create_test_list_membership(self.test_list, test)

        self.unit_test_collection = utils.create_unit_test_collection(test_collection=self.test_list)

        self.test_list_instance = self.create_test_list_instance()

        self.group = models.Group.objects.latest('pk')
        user = models.User.objects.latest('pk')
        user.groups.add(self.group)
        user.email = "example@example.com"
        user.save()
    #----------------------------------------------------------------------

    def create_test_list_instance(self):
        utc = self.unit_test_collection

        tli = utils.create_test_list_instance(unit_test_collection=utc)

        for i, (v, test, status) in enumerate(zip(self.values, self.tests, self.statuses)):
            uti = models.UnitTestInfo.objects.get(test=test, unit=utc.unit)
            ti = utils.create_test_instance(tli, unit_test_info=uti, value=v, status=status)
            ti.reference = self.ref
            ti.tolerance = self.tol
            if i == 0:
                ti.skipped = True
            if i == 1:
                ti.tolerance = None
                ti.reference = None
            else:
                ti.reference.save()
                ti.tolerance.save()

            ti.save()
        tli.save()
        return tli

    #----------------------------------------------------------------------
    def test_email_sent(self):

        notification = NotificationSubscription(group=self.group, warning_level=TOLERANCE)
        notification.save()
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        self.assertEqual(len(mail.outbox), 1)

    #----------------------------------------------------------------------
    def test_email_not_sent(self):
        #no failing tests so

        notification = NotificationSubscription(group=self.group, warning_level=TOLERANCE)
        notification.save()

        self.test_list_instance.testinstance_set.update(pass_fail=models.OK)
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        self.assertEqual(len(mail.outbox), 0)
