from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase
from django_q.models import Schedule

from qatrack.notifications.models import RecipientGroup
from qatrack.notifications.parts import admin
from qatrack.notifications.parts.models import PartCategoryGroup, PartNotice
from qatrack.service_log.tests import utils as sl_utils


class TestPartEmails(TestCase):

    def setUp(self):

        self.cat1 = sl_utils.create_part_category(name="cat 1")
        self.cat2 = sl_utils.create_part_category(name="cat 2")
        self.part1 = sl_utils.create_part(name="part 1", part_number="111", part_category=self.cat1, quantity_current=1)
        self.part2 = sl_utils.create_part(name="part 2", part_number="222", part_category=self.cat2, quantity_current=1)
        self.part3 = sl_utils.create_part(name="part 3", part_number="333", quantity_current=1)

        self.cat_group = PartCategoryGroup.objects.create(name="test group")
        self.cat_group.part_categories.add(self.cat1)

        self.group = Group.objects.create(name="group")
        self.user = User.objects.create_user(username="test", email="example@example.com", password="password")
        self.user.groups.add(self.group)
        self.user.save()

        self.recipients = RecipientGroup.objects.create(name="test group")
        self.recipients.groups.add(self.group)

        self.inactive_user = User.objects.create_user('inactive', 'inactive@user.com', 'password')
        self.inactive_user.groups.add(self.group)
        self.inactive_user.is_active = False
        self.inactive_user.save()

        self.notice = PartNotice.objects.create(
            recipients=self.recipients,
            notification_type=PartNotice.LOW_INVENTORY,
        )
        # delete defaults schedules to make counting easier
        Schedule.objects.all().delete()

        self.sa = sl_utils.create_service_area()

    def test_created(self):
        """Notice should not be sent out if part is just created"""
        sl_utils.create_part(name="foo", quantity_min=1, quantity_current=0)
        assert len(mail.outbox) == 0

    def test_edited_low(self):
        """Notice should not be sent out if part is edited directly"""
        p = sl_utils.create_part(name="foo", quantity_min=1, quantity_current=4)
        p.quantity_current = 0
        assert len(mail.outbox) == 0

    def test_storage_modified(self):
        """Notice should be sent out if part storage is modified and inventory
        falls below threshold."""
        p = sl_utils.create_part(name="foo", quantity_min=1)
        storagea = sl_utils.create_part_storage_collection(part=p, quantity=2)
        storageb = sl_utils.create_part_storage_collection(part=p, quantity=2)
        assert len(mail.outbox) == 0
        storagea.quantity = 0
        storagea.save()
        assert len(mail.outbox) == 0
        storageb.quantity = 0
        storageb.save()
        assert len(mail.outbox) == 1
        assert "Part %s" % p.name in mail.outbox[0].subject

    def test_created_no_recipients(self):
        self.recipients.groups.clear()
        p = sl_utils.create_part(name="foo", quantity_min=1)
        storage = sl_utils.create_part_storage_collection(part=p, quantity=2)
        storage.quantity = 0
        storage.save()
        assert len(mail.outbox) == 0


class TestPartNoticeAdmin(TestCase):

    def setUp(self):
        self.admin = admin.PartNoticeAdmin(model=PartNotice, admin_site=AdminSite())

    def test_get_notification_type_updated(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = PartNotice.objects.create(
            notification_type=PartNotice.LOW_INVENTORY,
            recipients=rg,
        )
        assert "Notify when inventory for a part falls" in self.admin.get_notification_type(n)

    def test_get_categories(self):
        pc = sl_utils.create_part_category("Test Cat")
        pcg = PartCategoryGroup.objects.create(name="PCG")
        pcg.part_categories.add(pc)
        rg = RecipientGroup.objects.create(name="RG")
        n = PartNotice.objects.create(
            notification_type=PartNotice.LOW_INVENTORY,
            part_categories=pcg,
            recipients=rg,
        )
        assert pcg.name in self.admin.get_categories(n)

    def test_get_recipients(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = PartNotice.objects.create(
            notification_type=PartNotice.LOW_INVENTORY,
            recipients=rg,
        )
        assert rg.name in self.admin.get_recipients(n)
