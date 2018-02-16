from unittest import mock

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.db.models import ProtectedError, ObjectDoesNotExist
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django_comments.models import Comment

from qatrack.service_log import models as sl_models
from qatrack.units import models as u_models

from qatrack.qa.tests import utils as qa_utils
from qatrack.service_log.tests import utils as sl_utils


class TestUnitServiceArea(TestCase):

    def test_unique_together(self):

        u = qa_utils.create_unit()
        sa = sl_utils.create_service_area()

        sl_utils.create_unit_service_area(unit=u, service_area=sa)

        with self.assertRaises(IntegrityError):
            sl_models.UnitServiceArea.objects.create(unit=u, service_area=sa)


class TestServiceEventStatus(TestCase):

    def setUp(self):
        sl_utils.create_service_event_status()

    def test_name_unique(self):

        ses_01 = sl_models.ServiceEventStatus.objects.first()
        ses_01_name = ses_01.name

        with self.assertRaises(IntegrityError):
            sl_models.ServiceEventStatus.objects.create(name=ses_01_name)

    def test_default(self):

        ses_01 = sl_models.ServiceEventStatus.objects.get()
        ses_01.is_default = True
        ses_01.save()
        ses_01_name = ses_01.name

        self.assertEqual(ses_01_name, sl_models.ServiceEventStatus.get_default().name)

        ses_02 = sl_models.ServiceEventStatus.objects.create(is_default=True)

        self.assertEqual(ses_02.name, sl_models.ServiceEventStatus.get_default().name)
        self.assertFalse(sl_models.ServiceEventStatus.objects.get(name=ses_01_name).is_default)

    def test_colours(self):

        ses_01 = sl_utils.create_service_event_status(colour=settings.DEFAULT_COLOURS[1])
        ses_02 = sl_utils.create_service_event_status(colour=settings.DEFAULT_COLOURS[2])

        colours = sl_models.ServiceEventStatus.get_colour_dict()

        self.assertEqual(colours[ses_01.id], settings.DEFAULT_COLOURS[1])
        self.assertEqual(colours[ses_02.id], settings.DEFAULT_COLOURS[2])


class TestThirdParty(TestCase):

    def test_unique_together(self):

        v_01 = qa_utils.create_vendor()
        tp_01 = sl_utils.create_third_party(vendor=v_01)
        tp_01_first_name = tp_01.first_name
        tp_01_last_name = tp_01.last_name

        with self.assertRaises(IntegrityError):
            sl_models.ThirdParty.objects.create(vendor=v_01, first_name=tp_01_first_name, last_name=tp_01_last_name)


class TestServiceEventAndRelated(TransactionTestCase):

    def setUp(self):
        sl_utils.create_service_event()

    def test_third_party_and_hours(self):

        se = sl_models.ServiceEvent.objects.first()
        tp = sl_utils.create_third_party()

        h_01 = sl_utils.create_hours(service_event=se, third_party=tp)

        # Test unique together. Will not raise IntegrityError when using sqlite3
        with self.assertRaises(IntegrityError):
            sl_models.Hours.objects.create(service_event=se, third_party=tp, user=None, time=timezone.timedelta(hours=1))

        u_02 = qa_utils.create_user(is_superuser=False, uname='user_02')
        h_02 = sl_utils.create_hours(service_event=se, user=u_02)

        # Test user_or_third_party
        self.assertEqual((tp.__class__, tp.id), (h_01.user_or_thirdparty().__class__, h_01.user_or_thirdparty().id))
        self.assertEqual((u_02.__class__, u_02.id), (h_02.user_or_thirdparty().__class__, h_02.user_or_thirdparty().id))

    def test_group_linkers(self):

        se = sl_models.ServiceEvent.objects.first()
        g_01 = qa_utils.create_group()
        g_02 = qa_utils.create_group()

        gl_01 = sl_utils.create_group_linker(group=g_01)
        gl_01_name = gl_01.name

        with self.assertRaises(IntegrityError):
            sl_models.GroupLinker.objects.create(name=gl_01_name, group=g_01)

        gl_02 = sl_utils.create_group_linker(group=g_02)
        gli_01 = sl_utils.create_group_linker_instance(group_linker=gl_01, service_event=se)

        with self.assertRaises(IntegrityError):
            sl_models.GroupLinkerInstance.objects.create(group_linker=gl_01, service_event=se)

        gli_02 = sl_utils.create_group_linker_instance(group_linker=gl_02, service_event=se)

        self.assertEqual(2, len(se.grouplinkerinstance_set.all()))


class TestDeletions(TransactionTestCase):

    def test_delete_grouplinkerinstance_variables(self):

        # group_linker  > Protect
        # user          > Prtect
        # service_event > Cascade

        gli = sl_utils.create_group_linker_instance()
        u = gli.user
        gl = gli.group_linker
        se = gli.service_event
        gli_id = gli.id

        with self.assertRaises(ProtectedError):
            u.delete()

        with self.assertRaises(ProtectedError):
            gl.delete()

        se.delete()
        self.assertFalse(sl_models.GroupLinkerInstance.objects.filter(id=gli_id).exists())

    def test_delete_grouplinker_variables(self):

        # group > Cascade

        gl = sl_utils.create_group_linker()
        g = gl.group
        gl_id = gl.id

        g.delete()
        self.assertFalse(sl_models.GroupLinker.objects.filter(id=gl_id).exists())

    def test_delete_returntoserviceqa_variables(self):

        # unit_test_collection  > Cascade
        # test_list_instance    > Set Null
        # user_assigned_by      > Protect
        # service_event         > Cascade

        sl_utils.create_service_event_status(is_default=True)
        rtsqa = sl_utils.create_return_to_service_qa()
        utc = rtsqa.unit_test_collection
        rtsqa_id = rtsqa.id

        utc.delete()
        self.assertFalse(sl_models.ReturnToServiceQA.objects.filter(id=rtsqa_id).exists())

        rtsqa = sl_utils.create_return_to_service_qa(add_test_list_instance=True)
        tli = rtsqa.test_list_instance
        u = rtsqa.user_assigned_by
        se = rtsqa.service_event
        rtsqa_id = rtsqa.id

        with self.assertRaises(ProtectedError):
            u.delete()

        tli.delete()
        rtsqa = sl_models.ReturnToServiceQA.objects.get(id=rtsqa_id)
        self.assertEqual(None, rtsqa.test_list_instance)

        se.delete()
        self.assertFalse(sl_models.ReturnToServiceQA.objects.filter(id=rtsqa_id).exists())

    def test_delete_hours_variables(self):

        # service_event > Cascade
        # third_party   > Protect
        # user          > Protect

        tp = sl_utils.create_third_party()
        h = sl_utils.create_hours(third_party=tp)
        se = h.service_event
        h_id = h.id

        with self.assertRaises(ProtectedError):
            tp.delete()

        se.delete()
        self.assertFalse(sl_models.Hours.objects.filter(id=h_id).exists())

        u = qa_utils.create_user()
        h = sl_utils.create_hours(user=u)

        with self.assertRaises(ProtectedError):
            u.delete()

    def test_delete_thirdparty_variables(self):

        # vendor > Protect

        tp = sl_utils.create_third_party()
        v = tp.vendor

        with self.assertRaises(ProtectedError):
            v.delete()

    def test_delete_serviceevent_variables(self):

        # unit_service_area                 > Protect
        # service_type                      > Protect
        # service_status                    > Protect
        # user_status_changed_by            > Protect
        # user_created_by                   > Protect
        # user_modified_by                  > Protect
        # test_list_instance_initiated_by   > Set Null

        sl_utils.create_service_event_status(is_default=True)
        ses = sl_utils.create_service_event_status()
        se = sl_utils.create_service_event(add_test_list_instance_initiated_by=True, service_status=ses)
        se.user_status_changed_by = qa_utils.create_user()
        se.user_modified_by = qa_utils.create_user()
        se.save()
        se_id = se.id

        usa = se.unit_service_area
        st = se.service_type
        u_scb = se.user_status_changed_by
        u_cb = se.user_created_by
        u_mb = se.user_modified_by
        tli = se.test_list_instance_initiated_by

        with self.assertRaises(ProtectedError):
            usa.delete()

        with self.assertRaises(ProtectedError):
            st.delete()

        with self.assertRaises(ProtectedError):
            ses.delete()

        with self.assertRaises(ProtectedError):
            u_scb.delete()

        with self.assertRaises(ProtectedError):
            u_cb.delete()

        with self.assertRaises(ProtectedError):
            u_mb.delete()

        tli.delete()
        se = sl_models.ServiceEvent.objects.get(id=se_id)
        self.assertEqual(None, se.test_list_instance_initiated_by)

    def test_delete_unit_service_area_variables(self):

        # unit          > Cascade
        # service_area  > Cascade

        usa = sl_utils.create_unit_service_area()
        u = usa.unit
        usa_id = usa.id

        u.delete()
        self.assertFalse(sl_models.UnitServiceArea.objects.filter(id=usa_id).exists())

        usa = sl_utils.create_unit_service_area()
        sa = usa.service_area
        usa_id = usa.id

        sa.delete()
        self.assertFalse(sl_models.UnitServiceArea.objects.filter(id=usa_id).exists())

