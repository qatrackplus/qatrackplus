import json

from django.contrib.admin.sites import AdminSite
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import constants, get_messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.forms import HiddenInput, inlineformset_factory, modelform_factory
from django.http import QueryDict
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse

from qatrack.accounts.tests.utils import create_group, create_user
from qatrack.qa import admin as qa_admin
from qatrack.qa import models as qa_models
from qatrack.qa.tests import utils as qa_utils
from qatrack.qa.utils import get_bool_tols, get_internal_user
from qatrack.service_log.tests import utils as sl_utils


class TestSetReferencesAndTolerancesForm(TransactionTestCase):

    def setUp(self):

        create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')

        self.url = reverse('qa_copy_refs_and_tols')

        self.tl_1 = qa_utils.create_test_list()
        self.tl_2 = qa_utils.create_test_list()
        self.tl_3 = qa_utils.create_test_list()
        self.tl_fc_1 = qa_utils.create_test_list(name='for_cycle_1')
        self.tl_fc_2 = qa_utils.create_test_list(name='for_cycle_2')
        self.tl_fc_3 = qa_utils.create_test_list(name='for_cycle_3')
        self.tlc_1 = qa_utils.create_cycle(test_lists=[self.tl_fc_1, self.tl_fc_2, self.tl_fc_3])
        self.tlc_2 = qa_utils.create_cycle(test_lists=[self.tl_fc_1, self.tl_fc_2])

        self.u_1 = qa_utils.create_unit()
        self.u_2 = qa_utils.create_unit()

        test = qa_utils.create_test()

        self.tlm_1 = qa_utils.create_test_list_membership(test_list=self.tl_1, test=test)
        self.tlm_2 = qa_utils.create_test_list_membership(test_list=self.tl_2, test=test)

        self.utc_1 = qa_utils.create_unit_test_collection(unit=self.u_1, test_collection=self.tl_1)
        self.utc_2 = qa_utils.create_unit_test_collection(unit=self.u_2, test_collection=self.tl_2)

        self.uti_1, _ = qa_models.UnitTestInfo.objects.get_or_create(unit=self.u_1, test=test)
        self.uti_1.reference = qa_utils.create_reference()
        self.uti_1.tolerance = qa_utils.create_tolerance()
        self.uti_1.save()

        self.uti_2, _ = qa_models.UnitTestInfo.objects.get_or_create(unit=self.u_2, test=test)

    def test_source_testlist_choices(self):

        response = self.client.get(self.url)

        choices = response.context['form'].fields['source_testlist'].choices

        for tl in qa_models.TestList.objects.all():
            self.assertTrue((tl.id, tl.name) in choices)
        for tlc in qa_models.TestListCycle.objects.all():
            self.assertTrue((tlc.id, tlc.name) in choices)

    def test_save(self):

        uti_source = self.uti_1
        uti_dest = self.uti_2

        data = {
            'content_type': 'testlist',
            'source_testlist': self.tl_1.id,
            'source_unit': self.u_1.id,
            'dest_unit': self.u_2.id,
            'confirm': 'Confirm',
            'stage': 2
        }

        response = self.client.post(self.url, data=data)
        hash_val = None
        for c in response.context[0]:
            if 'hash_value' in c:
                hash_val = c['hash_value']

        data['hash_field'] = 'hash'
        data['hash'] = hash_val
        self.client.post(self.url, data=data)
        uti_dest = qa_models.UnitTestInfo.objects.get(id=uti_dest.id)

        self.assertEqual(uti_source.reference, uti_dest.reference)
        self.assertEqual(uti_source.tolerance, uti_dest.tolerance)


class TestTestlistjson(TestCase):

    def setUp(self):

        create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')

        self.u = qa_utils.create_unit()

        tl1 = qa_utils.create_test_list()
        tl2 = qa_utils.create_test_list()
        tl3 = qa_utils.create_test_list()

        qa_utils.create_unit_test_collection(unit=self.u, test_collection=tl1)
        qa_utils.create_unit_test_collection(unit=self.u, test_collection=tl2)
        qa_utils.create_unit_test_collection(unit=self.u, test_collection=tl3)

        tlc1 = qa_utils.create_cycle(test_lists=[tl1, tl2, tl3])

        qa_utils.create_unit_test_collection(unit=self.u, test_collection=tlc1)

        self.url_tl = reverse(
            'qa_copy_refs_and_tols_testlist_json', kwargs={
                'source_unit': self.u.id, 'content_type': qa_models.TestList.__name__.lower()
            }
        )
        self.url_tlc = reverse(
            'qa_copy_refs_and_tols_testlist_json', kwargs={
                'source_unit': self.u.id, 'content_type': qa_models.TestListCycle.__name__.lower()
            })
        self.url_bad = reverse(
            'qa_copy_refs_and_tols_testlist_json', kwargs={
                'source_unit': self.u.id, 'content_type': qa_models.Test.__name__.lower()
            }
        )

        self.tl_ct = ContentType.objects.get(model='testlist')
        self.tlc_ct = ContentType.objects.get(model='testlistcycle')

    def test_test_list(self):

        utcs = qa_models.UnitTestCollection.objects.filter(
            unit=self.u, content_type=self.tl_ct
        ).values_list('object_id', flat=True)
        tl_to_find = list(qa_models.TestList.objects.filter(pk__in=utcs).values_list('pk', 'name'))

        response = self.client.get(self.url_tl)
        self.assertJSONEqual(
            json.dumps(tl_to_find),
            response.json()
        )

    def test_test_list_cycle(self):

        utcs = qa_models.UnitTestCollection.objects.filter(
            unit=self.u, content_type=self.tlc_ct
        ).values_list('object_id', flat=True)
        tlc_to_find = list(qa_models.TestListCycle.objects.filter(pk__in=utcs).values_list('pk', 'name'))

        response = self.client.get(self.url_tlc)
        self.assertJSONEqual(
            json.dumps(tlc_to_find),
            response.json()
        )

    def test_bad_ctype(self):

        with self.assertRaises(ValidationError):
            self.client.get(self.url_bad)


class TestToleranceAdmin(TestCase):

    def setUp(self):

        self.user = create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')

        self.t = qa_utils.create_tolerance()

        self.url_add = reverse(
            'admin:%s_%s_add' % (qa_models.Tolerance._meta.app_label, qa_models.Tolerance._meta.model_name)
        )
        self.url_list = reverse(
            'admin:%s_%s_changelist' % (qa_models.Tolerance._meta.app_label, qa_models.Tolerance._meta.model_name)
        )

        self.data = {
            'mc_tol_choices': '',
            'act_low': '0',
            'tol_low': '1',
            'tol_high': '2',
            'act_high': '3',
            'type': 'absolute',
            'mc_pass_choices': ''
        }

    def test_add(self):

        self.client.post(self.url_add, data=self.data)
        t = qa_models.Tolerance.objects.order_by('id').last()

        self.assertEqual(self.user, t.created_by)

    def test_unique(self):
        self.client.post(self.url_add, data=self.data)
        form = modelform_factory(qa_models.Tolerance, form=qa_admin.ToleranceForm, fields='__all__')(data=self.data)
        self.assertFalse(form.is_valid())

    def test_list(self):
        qa_utils.create_tolerance(act_high=3)
        qa_utils.create_tolerance(act_high=4)
        self.client.get(self.url_list)


class TestTestInstanceAdmin(TestCase):

    def setUp(self):
        self.user = create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')
        qa_utils.create_test_instance()
        self.url = reverse(
            'admin:%s_%s_changelist' % (qa_models.TestInstance._meta.app_label, qa_models.TestInstance._meta.model_name)
        )

    def test_list_page(self):
        self.client.get(self.url)


class TestTestListInstanceAdmin(TestCase):

    def setUp(self):

        self.user = create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')

        self.tli = qa_utils.create_test_list_instance()
        self.usa = sl_utils.create_unit_service_area(unit=self.tli.unit_test_collection.unit)
        self.se = sl_utils.create_service_event(
            unit_service_area=self.usa, add_test_list_instance_initiated_by=self.tli
        )
        sl_utils.create_return_to_service_qa(add_test_list_instance=self.tli)

        self.url_list = reverse(
            'admin:%s_%s_changelist' % (
                qa_models.TestListInstance._meta.app_label, qa_models.TestListInstance._meta.model_name
            )
        )
        self.url_delete = reverse(
            'admin:%s_%s_delete' % (
                qa_models.TestListInstance._meta.app_label, qa_models.TestListInstance._meta.model_name
            ),
            args=[self.tli.id]
        )

    def test_list_page(self):
        self.client.get(self.url_list)

    def test_delete_form(self):

        response = self.client.get(self.url_delete)
        for a in response.context:
            for b in a:
                if 'se_rtsqa_qs' in b:
                    self.assertTrue(len(b['se_rtsqa_qs']) > 0)
                    self.assertTrue(len(b['se_ib_qs']) > 0)


class TestUnitTestCollectionAdmin(TestCase):

    def setUp(self):
        self.user = create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')

        self.u_1 = qa_utils.create_unit()
        self.u_2 = qa_utils.create_unit()
        self.f_1 = qa_utils.create_frequency()
        self.f_2 = qa_utils.create_frequency()
        self.tl_1 = qa_utils.create_test_list()
        self.tl_2 = qa_utils.create_test_list()
        self.t_1 = qa_utils.create_test()
        self.t_2 = qa_utils.create_test()
        qa_utils.create_test_list_membership(test_list=self.tl_1, test=self.t_1)
        qa_utils.create_test_list_membership(test_list=self.tl_1, test=self.t_2)

        self.g_1 = create_group()
        self.g_2 = create_group()

        self.tl_ct = ContentType.objects.get(model='testlist')
        self.tlc_ct = ContentType.objects.get(model='testlistcycle')
        self.utc_1 = qa_utils.create_unit_test_collection(
            unit=self.u_1, test_collection=self.tl_1, assigned_to=self.g_1, frequency=self.f_1
        )
        self.utc_2 = qa_utils.create_unit_test_collection(
            unit=self.u_2, active=False, assigned_to=self.g_2, frequency=self.f_2
        )

        self.url_list = reverse(
            'admin:%s_%s_changelist' % (
                qa_models.UnitTestCollection._meta.app_label, qa_models.UnitTestCollection._meta.model_name
            )
        )
        self.url_add = reverse(
            'admin:%s_%s_add' % (
                qa_models.UnitTestCollection._meta.app_label, qa_models.UnitTestCollection._meta.model_name
            )
        )
        self.url_change = reverse(
            'admin:%s_%s_change' % (
                qa_models.UnitTestCollection._meta.app_label, qa_models.UnitTestCollection._meta.model_name
            ),
            args=[self.utc_1.id]
        )

    def test_list_page(self):
        self.client.get(self.url_list)

    def test_add_form(self):

        data = {
            'frequency': self.f_1.id,
            'visible_to': [self.g_1.id],
            'unit': qa_utils.create_unit().id,
            'auto_schedule': 'on',
            'active': 'on',
            'assigned_to': self.g_1.id,
            'content_type': self.tl_ct.id,
            'object_id': self.tl_1.id
        }

        utc_before = qa_models.UnitTestCollection.objects.count()
        self.client.post(self.url_add, data=data)
        utc_after = qa_models.UnitTestCollection.objects.count()
        self.assertEqual(utc_before + 1, utc_after)

    def test_readonly_values(self):

        data = {
            'frequency': self.utc_1.frequency.id,
            'visible_to': [vt.id for vt in self.utc_1.visible_to.all()],
            'unit': self.u_2.id,
            'auto_schedule': 'on',
            'active': 'on',
            'assigned_to': self.utc_1.assigned_to.id,
            'content_type': self.tlc_ct.id,
            'object_id': self.tl_2.id
        }

        form = modelform_factory(
            qa_models.UnitTestCollection, form=qa_admin.UnitTestCollectionForm, fields='__all__'
        )(data=data, instance=self.utc_1)
        self.assertFalse(form.is_valid())
        self.assertTrue('object_id' in form.errors)
        self.assertTrue('content_type' in form.errors)
        self.assertTrue('unit' in form.errors)

    def test_active_filter(self):
        fylter = qa_admin.ActiveFilter(
            None, {'activefilter': 1}, qa_models.UnitTestCollection, qa_admin.UnitTestCollectionAdmin
        )
        filtered_1 = fylter.queryset(None, qa_models.UnitTestCollection.objects.all())
        filtered_2 = qa_models.UnitTestCollection.objects.filter(active=True)
        self.assertListEqual(list(filtered_2), list(filtered_1))

    def test_assigned_to_filter(self):
        fylter = qa_admin.AssignedToFilter(
            None, {'assignedtoname': self.g_1.id}, qa_models.UnitTestCollection, qa_admin.UnitTestCollectionAdmin
        )
        filtered_1 = fylter.queryset(None, qa_models.UnitTestCollection.objects.all())
        filtered_2 = qa_models.UnitTestCollection.objects.filter(assigned_to=self.g_1)
        self.assertListEqual(list(filtered_2), list(filtered_1))

    def test_frequency_filter(self):
        fylter = qa_admin.FrequencyFilter(
            None, {'freqfilter': self.f_1.id}, qa_models.UnitTestCollection, qa_admin.UnitTestCollectionAdmin
        )
        filtered_1 = fylter.queryset(None, qa_models.UnitTestCollection.objects.all())
        filtered_2 = qa_models.UnitTestCollection.objects.filter(frequency=self.f_1)
        self.assertListEqual(list(filtered_2), list(filtered_1))

    def test_unit_filter(self):
        fylter = qa_admin.UnitFilter(
            None, {'unitfilter': self.u_1.id}, qa_models.UnitTestCollection, qa_admin.UnitTestCollectionAdmin
        )
        filtered_1 = fylter.queryset(None, qa_models.UnitTestCollection.objects.all())
        filtered_2 = qa_models.UnitTestCollection.objects.filter(unit=self.u_1)
        self.assertListEqual(list(filtered_2), list(filtered_1))


class TestTestAdmin(TestCase):

    def setUp(self):
        self.user = create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')

        self.c_1 = qa_utils.create_category()
        self.t_1 = qa_utils.create_test()
        self.tl_1 = qa_utils.create_test_list()
        qa_utils.create_test_list_membership(test=self.t_1, test_list=self.tl_1)
        self.tli_1 = qa_utils.create_test_list_instance(test_list=self.tl_1)
        self.ti_1 = qa_utils.create_test_instance(
            test_list_instance=self.tli_1, unit_test_info=qa_utils.create_unit_test_info(test=self.t_1), value=1
        )

        self.url_add = reverse(
            'admin:%s_%s_add' % (qa_models.Test._meta.app_label, qa_models.Test._meta.model_name)
        )
        self.url_list = reverse(
            'admin:%s_%s_changelist' % (qa_models.Test._meta.app_label, qa_models.Test._meta.model_name)
        )
        self.url_change = reverse(
            'admin:%s_%s_change' % (qa_models.Test._meta.app_label, qa_models.Test._meta.model_name),
            args=[self.t_1.id]
        )

        self.data = {
            'procedure': '',
            'category': self.c_1.id,
            'attachment_set-MIN_NUM_FORMS': 0,
            'attachment_set-INITIAL_FORMS': 0,
            'attachment_set-MAX_NUM_FORMS': 0,
            'attachment_set-TOTAL_FORMS': 0,
            'chart_visibility': 'on',
            'constant_value': '',
            'description': '',
            'slug': '',
            'type': 'simple',
            'calculation_procedure': '',
            'choices': '',
            'name': ''
        }

    def test_list(self):
        self.client.get(self.url_list)

    def test_pyplot_warning(self):

        data = self.data
        data['calculation_procedure'] = 'import pyplot\r\nresult = 1'
        data['slug'] = 'test_pyplot'
        data['type'] = 'composite'
        data['name'] = 'Test pyplot'

        response = self.client.post(self.url_add, data=data)
        messages = get_messages(response.wsgi_request)
        self.assertTrue(constants.WARNING in [m.level for m in messages])

    def test_http_warning(self):

        data = self.data
        data['procedure'] = 'not http'
        data['slug'] = 'test_http'
        data['name'] = 'Test http'

        response = self.client.post(self.url_add, data=data)
        messages = get_messages(response.wsgi_request)
        self.assertTrue(constants.WARNING in [m.level for m in messages])

    def test_testlistmembership_filter(self):
        qs = qa_models.Test.objects.annotate(tlcount=Count("testlistmembership"))
        fylter = qa_admin.TestListMembershipFilter(
            None,
            {'tlmembership': qa_admin.TestListMembershipFilter.HASMEMBERSHIPS},
            qa_models.Test,
            qa_admin.TestAdmin
        )
        filtered_1 = fylter.queryset(None, qa_models.Test.objects.all())
        filtered_2 = qs.filter(tlcount__gt=0)
        self.assertListEqual(list(filtered_2), list(filtered_1))

        fylter = qa_admin.TestListMembershipFilter(
            None,
            {'tlmembership': qa_admin.TestListMembershipFilter.NOMEMBERSHIPS},
            qa_models.Test,
            qa_admin.TestAdmin
        )
        filtered_1 = fylter.queryset(None, qa_models.Test.objects.all())
        filtered_2 = qs.filter(tlcount=0)
        self.assertListEqual(list(filtered_2), list(filtered_1))

    def test_change_type(self):

        data = self.data
        data['name'] = self.t_1.name
        data['slug'] = self.t_1.slug
        data['type'] = qa_models.BOOLEAN

        form = modelform_factory(
            qa_models.Test, form=qa_admin.TestForm, fields='__all__'
        )(data=data, instance=self.t_1)

        self.assertFalse(form.is_valid())
        self.assertTrue('type' in form.errors)


class TestTestListAdmin(TestCase):

    def setUp(self):
        self.user = create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')

        self.t_1 = qa_utils.create_test()
        self.t_2 = qa_utils.create_test()
        self.u_1 = qa_utils.create_unit()
        self.f_1 = qa_utils.create_frequency()
        self.tl_1 = qa_utils.create_test_list()
        self.utc_1 = qa_utils.create_unit_test_collection(test_collection=self.tl_1, unit=self.u_1)
        self.utc_2 = qa_utils.create_unit_test_collection(test_collection=self.tl_1, frequency=self.f_1)

        qa_utils.create_test_list_membership(test_list=self.tl_1, test=self.t_2, order=0)

        self.sublist = qa_utils.create_sublist(parent_test_list=self.tl_1)

        self.url_add = reverse(
            'admin:%s_%s_add' % (qa_models.TestList._meta.app_label, qa_models.TestList._meta.model_name)
        )
        self.url_list = reverse(
            'admin:%s_%s_changelist' % (qa_models.TestList._meta.app_label, qa_models.TestList._meta.model_name)
        )
        self.url_change = reverse(
            'admin:%s_%s_change' % (qa_models.TestList._meta.app_label, qa_models.TestList._meta.model_name),
            args=[self.tl_1.id]
        )

        self.data = {
            'name': 'testing_sublists',
            'warning_message': 'erroR',
            'javascript': 'alert("subs!")',
            'slug': 'testing_sublists',
            'description': 'description',

            'attachment_set-MAX_NUM_FORMS': 10,
            'attachment_set-INITIAL_FORMS': 0,
            'attachment_set-MIN_NUM_FORMS': 0,
            'attachment_set-TOTAL_FORMS': 1,
            'attachment_set-0-testlist': '',
            'attachment_set-0-id': '',
            'attachment_set-0-comment': 'Testing',
            'attachment_set-0-attachment': '',

            'children-INITIAL_FORMS': 0,
            'children-MIN_NUM_FORMS': 0,
            'children-MAX_NUM_FORMS': 10,
            'children-TOTAL_FORMS': 1,
            'children-0-order': 1,
            'children-0-child': self.tl_1.id,
            'children-0-parent': '',
            'children-0-id': '',

            'testlistmembership_set-MIN_NUM_FORMS': 0,
            'testlistmembership_set-INITIAL_FORMS': 0,
            'testlistmembership_set-MAX_NUM_FORMS': 10,
            'testlistmembership_set-TOTAL_FORMS': 1,
            'testlistmembership_set-0-test_list': '',
            'testlistmembership_set-0-id': '',
            'testlistmembership_set-0-order': 0,
            'testlistmembership_set-0-test': self.t_1.id
        }

    def test_list(self):
        self.client.get(self.url_list)

    def test_frequency_test_list_filter(self):
        fylter = qa_admin.FrequencyTestListFilter(
            None, {'assignedbyfreq': self.f_1.id}, qa_models.TestList, qa_admin.TestListAdmin
        )
        filtered_1 = fylter.queryset(None, qa_models.TestList.objects.all())
        freq_tl_ids = qa_models.get_utc_tl_ids(frequencies=[self.f_1])
        filtered_2 = qa_models.TestList.objects.filter(id__in=freq_tl_ids)
        self.assertListEqual(list(filtered_2), list(filtered_1))

    def test_unit_test_list_filter(self):
        fylter = qa_admin.UnitTestListFilter(
            None, {'assignedtounit': self.u_1.id}, qa_models.TestList, qa_admin.TestListAdmin
        )
        filtered_1 = fylter.queryset(None, qa_models.TestList.objects.all())
        unit_tl_ids = qa_models.get_utc_tl_ids(units=[self.u_1])
        filtered_2 = qa_models.TestList.objects.filter(id__in=unit_tl_ids)
        self.assertListEqual(list(filtered_2), list(filtered_1))

    def test_active_test_list_filter(self):
        active_tl_ids = qa_models.get_utc_tl_ids(active=True)
        active_sub_tl_ids = list(qa_models.TestList.objects.filter(
            id__in=active_tl_ids, children__isnull=False
        ).values_list('children__child__id', flat=True).distinct())

        fylter = qa_admin.ActiveTestListFilter(
            None,
            {'activeutcs': qa_admin.ActiveTestListFilter.HASACTIVEUTCS},
            qa_models.TestList,
            qa_admin.TestListAdmin
        )
        filtered_1 = fylter.queryset(None, qa_models.TestList.objects.all())
        filtered_2 = qa_models.TestList.objects.filter(
            Q(id__in=active_tl_ids) |
            Q(id__in=active_sub_tl_ids)
        )
        self.assertListEqual(list(filtered_2), list(filtered_1))

        fylter = qa_admin.ActiveTestListFilter(
            None,
            {'activeutcs': qa_admin.ActiveTestListFilter.NOACTIVEUTCS},
            qa_models.TestList,
            qa_admin.TestListAdmin
        )
        filtered_1 = fylter.queryset(None, qa_models.TestList.objects.all())
        filtered_2 = qa_models.TestList.objects.exclude(
            Q(id__in=active_tl_ids) |
            Q(id__in=active_sub_tl_ids)
        )
        self.assertListEqual(list(filtered_2), list(filtered_1))

    def test_change_page(self):
        self.client.get(self.url_change)

    def test_form_valid(self):

        data = self.data
        form = modelform_factory(qa_models.TestList, form=qa_admin.TestListAdminForm, exclude=['tests'])(data=data)
        self.assertTrue(form.is_valid())

    def test_duplicate_macros(self):
        data = self.data
        data['testlistmembership_set-TOTAL_FORMS'] = 2
        data['testlistmembership_set-1-test_list'] = ''
        data['testlistmembership_set-1-id'] = ''
        data['testlistmembership_set-1-order'] = 3
        data['testlistmembership_set-1-test'] = self.t_2.id

        form = modelform_factory(qa_models.TestList, form=qa_admin.TestListAdminForm, exclude=['tests'])(data=data)
        self.assertFalse(form.is_valid())

    def test_clean_slug(self):
        data = self.data
        data['slug'] = self.tl_1.slug
        form = modelform_factory(qa_models.TestList, form=qa_admin.TestListAdminForm, exclude=['tests'])(data=data)
        self.assertFalse(form.is_valid())

    def test_sublist_formset_valid(self):

        data = self.data
        data['children-0-child'] = self.sublist.child.id

        formset = inlineformset_factory(
            qa_models.TestList, qa_models.Sublist, formset=qa_admin.SublistInlineFormSet, fk_name='parent',
            fields='__all__'
        )(data=data, queryset=qa_models.Sublist.objects.all(), instance=None)
        self.assertTrue(formset.is_valid())

    def test_sublist_formset_own_child(self):
        data = self.data
        formset = inlineformset_factory(
            qa_models.TestList, qa_models.Sublist, formset=qa_admin.SublistInlineFormSet, fk_name='parent',
            fields='__all__'
        )(data=data, queryset=qa_models.Sublist.objects.all(), instance=self.tl_1)
        self.assertFalse(formset.is_valid())

    def test_sublist_nesting_parent(self):
        """Shouldn't be able to add a sublist that has a sublist of its own"""
        tl = qa_utils.create_test_list(name="sub")
        qa_utils.create_sublist(parent_test_list=self.sublist.child, child_test_list=tl)
        data = self.data
        formset = inlineformset_factory(
            qa_models.TestList, qa_models.Sublist, formset=qa_admin.SublistInlineFormSet, fk_name='parent',
            fields='__all__'
        )(data=data, queryset=qa_models.Sublist.objects.all(), instance=None)
        assert not formset.is_valid()
        assert "Test Lists can not be nested more than 1 level" in formset.non_form_errors()[0]

    def test_sublist_nesting_child(self):
        """Shouldn't be able to add a sublist when you are a sublist"""
        tl = qa_utils.create_test_list(name="sub")
        data = self.data
        data['children-0-child'] = tl.id
        formset = inlineformset_factory(
            qa_models.TestList,
            qa_models.Sublist,
            formset=qa_admin.SublistInlineFormSet,
            fk_name='parent',
            fields='__all__'
        )(data=data, queryset=qa_models.Sublist.objects.all(), instance=self.sublist.child)
        assert not formset.is_valid()
        assert "This Test List is a Sublist" in formset.non_form_errors()[0]

    def test_sublist_duplicate(self):
        data = self.data

        data['children-TOTAL_FORMS'] = 2
        data['children-1-order'] = 2
        data['children-1-child'] = self.tl_1.id
        data['children-1-parent'] = ''
        data['children-1-id'] = ''

        formset = inlineformset_factory(
            qa_models.TestList, qa_models.Sublist, formset=qa_admin.SublistInlineFormSet, fk_name='parent',
            fields='__all__'
        )(data=data, queryset=qa_models.Sublist.objects.all(), instance=None)
        self.assertFalse(formset.is_valid())

    def test_test_valid(self):
        data = self.data
        formset = inlineformset_factory(
            qa_models.TestList, qa_models.TestListMembership, formset=qa_admin.TestListMembershipInlineFormSet,
            fields='__all__'
        )(data=data, queryset=qa_models.TestListMembership.objects.all(), instance=None)
        self.assertTrue(formset.is_valid())

    def test_test_duplicate(self):
        data = self.data

        data['testlistmembership_set-TOTAL_FORMS'] = 2
        data['testlistmembership_set-1-test_list'] = '',
        data['testlistmembership_set-1-id'] = '',
        data['testlistmembership_set-1-order'] = 2,
        data['testlistmembership_set-1-test'] = self.t_1.id

        formset = inlineformset_factory(
            qa_models.TestList, qa_models.TestListMembership, formset=qa_admin.TestListMembershipInlineFormSet,
            fields='__all__'
        )(data=data, queryset=qa_models.TestListMembership.objects.all(), instance=None)
        self.assertFalse(formset.is_valid())


class TestUnitTestInfoAdmin(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')

        get_internal_user()
        get_bool_tols()  # hack to work around tolerances being deleted somewhere (in another test?)

        self.site = AdminSite()
        self.u_1 = qa_utils.create_unit()
        self.t_1 = qa_utils.create_test(test_type=qa_models.SIMPLE)
        self.t_2 = qa_utils.create_test(test_type=qa_models.BOOLEAN)
        self.t_3 = qa_utils.create_test(test_type=qa_models.MULTIPLE_CHOICE)
        self.t_4 = qa_utils.create_test(test_type=qa_models.SIMPLE)
        self.t_5 = qa_utils.create_test(test_type=qa_models.BOOLEAN)
        self.t_6 = qa_utils.create_test(test_type=qa_models.MULTIPLE_CHOICE)
        self.t_360 = qa_utils.create_test(test_type=qa_models.WRAPAROUND, wrap_low=0, wrap_high=360)
        self.tol_1 = qa_utils.create_tolerance()
        self.tol_2 = qa_utils.create_tolerance(act_low=-10, act_high=10)

        self.tol_3 = qa_models.Tolerance.objects.filter(type=qa_models.BOOLEAN).first()
        self.tol_4 = qa_utils.create_tolerance(
            tol_type=qa_models.MULTIPLE_CHOICE, mc_pass_choices='2,4,6', mc_tol_choices='1,3,5'
        )
        self.tol_5 = qa_utils.create_tolerance(tol_type=qa_models.PERCENT)
        self.r_1 = qa_utils.create_reference()
        self.r_2 = qa_utils.create_reference(value=1.61803)
        self.r_3 = qa_utils.create_reference(ref_type=qa_models.BOOLEAN)

        self.uti_1 = qa_utils.create_unit_test_info(unit=self.u_1, test=self.t_1, ref=self.r_1, tol=self.tol_1)
        self.uti_2 = qa_utils.create_unit_test_info(unit=self.u_1, test=self.t_2, ref=self.r_1, tol=self.tol_1)
        self.uti_3 = qa_utils.create_unit_test_info(unit=self.u_1, test=self.t_3)
        self.uti_4 = qa_utils.create_unit_test_info(unit=self.u_1, test=self.t_4)
        self.uti_5 = qa_utils.create_unit_test_info(unit=self.u_1, test=self.t_5, tol=self.tol_3)
        self.uti_6 = qa_utils.create_unit_test_info(unit=self.u_1, test=self.t_6, tol=self.tol_4)
        self.uti_360 = qa_utils.create_unit_test_info(unit=self.u_1, test=self.t_360, ref=self.r_1, tol=self.tol_1)

        self.url_list = reverse(
            'admin:%s_%s_changelist' % (qa_models.UnitTestInfo._meta.app_label, qa_models.UnitTestInfo._meta.model_name)
        )
        self.url_change = reverse(
            'admin:%s_%s_change' % (qa_models.UnitTestInfo._meta.app_label, qa_models.UnitTestInfo._meta.model_name),
            args=[self.uti_1.id]
        )

        self.data = {
            'unit': self.u_1.id,
            'test': self.t_1.id,
            'test_type': self.t_1.type,
            'reference_value': self.r_2.value,
            'tolerance': self.tol_1.id,
            'id': self.uti_1.id
        }

    def test_list(self):
        self.client.get(self.url_list)

    def test_form_valid(self):
        data = self.data
        form = modelform_factory(
            qa_models.UnitTestInfo, form=qa_admin.TestInfoForm, fields='__all__'
        )(instance=self.uti_1, data=data)
        self.assertTrue(form.is_valid())
        self.assertListEqual(
            list(form.fields['tolerance'].queryset),
            list(qa_models.Tolerance.objects.exclude(type=qa_models.MULTIPLE_CHOICE).exclude(type=qa_models.BOOLEAN))
        )

    def test_boolean(self):

        form = modelform_factory(
            qa_models.UnitTestInfo, form=qa_admin.TestInfoForm, fields='__all__'
        )(instance=self.uti_2)

        self.assertListEqual(
            form.fields['reference_value'].widget.choices,
            [("", "---"), (0, "No"), (1, "Yes")]
        )
        self.assertListEqual(
            list(form.fields['tolerance'].queryset),
            list(qa_models.Tolerance.objects.filter(type=qa_models.BOOLEAN))
        )

    def test_multi(self):
        form = modelform_factory(
            qa_models.UnitTestInfo, form=qa_admin.TestInfoForm, fields='__all__'
        )(instance=self.uti_3)

        self.assertIsInstance(form.fields['reference_value'].widget, HiddenInput)
        self.assertListEqual(
            list(form.fields['tolerance'].queryset),
            list(qa_models.Tolerance.objects.filter(type=qa_models.MULTIPLE_CHOICE))
        )

    def test_submit(self):

        data = self.data
        request = self.factory.get(self.url_change)
        request.user = self.user
        admin = qa_admin.UnitTestInfoAdmin(qa_models.UnitTestInfo, self.site)

        form = admin.get_form(request)(instance=self.uti_1, data=data)
        self.assertTrue(form.is_valid())
        admin.save_model(request, admin.save_form(request, form, True), form, True)
        self.assertEqual(self.uti_1.reference.value, self.r_2.value)

        data['reference_value'] = ''
        form = admin.get_form(request)(instance=self.uti_1, data=data)
        self.assertTrue(form.is_valid())
        admin.save_model(request, admin.save_form(request, form, True), form, True)
        self.assertEqual(self.uti_1.reference, None)

        data['reference_value'] = '3.14159'
        form = admin.get_form(request)(instance=self.uti_1, data=data)
        self.assertTrue(form.is_valid())
        admin.save_model(request, admin.save_form(request, form, True), form, True)
        self.assertEqual(self.uti_1.reference.value, '3.14159')

    def test_submit_360(self):

        data = {
            'unit': self.u_1.id,
            'test': self.t_360.id,
            'test_type': self.t_360.type,
            'reference_value': -1,
            'tolerance': self.tol_1.id,
            'id': self.uti_360.id
        }
        request = self.factory.get(self.url_change)
        request.user = self.user
        admin = qa_admin.UnitTestInfoAdmin(qa_models.UnitTestInfo, self.site)

        form = admin.get_form(request)(instance=self.uti_360, data=data)
        assert not form.is_valid()

        data['reference_value'] = 0
        form = admin.get_form(request)(instance=self.uti_360, data=data)
        assert form.is_valid()

    def test_save_multiple_simple(self):
        # request = self.factory.get(self.url_change)
        request = self.client.post(self.url_change).wsgi_request
        request.user = self.user
        admin = qa_admin.UnitTestInfoAdmin(qa_models.UnitTestInfo, self.site)
        data = {
            'tolerance': self.tol_2.id,
            'reference': self.r_2.value,
            'post': 'yes',
            'contenttype': '',
            'action': 'set_multiple_references_and_tolerances',
            '_selected_action': [self.uti_1.id, self.uti_4.id],
            'apply': 'Set tolerances and references'
        }
        request.POST = QueryDict('', mutable=True)
        request.POST.update(data)
        admin.set_multiple_references_and_tolerances(
            request, qa_models.UnitTestInfo.objects.filter(id__in=[self.uti_1.id, self.uti_4.id])
        )

        self.uti_1.refresh_from_db()
        self.uti_4.refresh_from_db()
        self.assertListEqual(
            [self.uti_1.reference.value, self.uti_4.reference.value],
            [self.r_2.value, self.r_2.value]
        )

    def test_save_multiple_boolean(self):
        request = self.client.post(self.url_change).wsgi_request
        request.user = self.user
        admin = qa_admin.UnitTestInfoAdmin(qa_models.UnitTestInfo, self.site)
        data = {
            'tolerance': self.tol_3.id,
            'reference': self.r_3.value,
            'post': 'yes',
            'contenttype': '',
            'action': 'set_multiple_references_and_tolerances',
            '_selected_action': [self.uti_2.id, self.uti_5.id],
            'apply': 'Set tolerances and references'
        }
        request.POST = QueryDict('', mutable=True)
        request.POST.update(data)
        admin.set_multiple_references_and_tolerances(
            request, qa_models.UnitTestInfo.objects.filter(id__in=[self.uti_2.id, self.uti_5.id])
        )

        self.uti_2.refresh_from_db()
        self.uti_5.refresh_from_db()
        self.assertListEqual(
            [self.uti_2.reference.value, self.uti_5.reference.value],
            [self.r_3.value, self.r_3.value]
        )

    def test_save_multiple_multiple(self):
        request = self.client.post(self.url_change).wsgi_request
        request.user = self.user
        admin = qa_admin.UnitTestInfoAdmin(qa_models.UnitTestInfo, self.site)
        data = {
            'tolerance': self.tol_4.id,
            'reference': '',
            'post': 'yes',
            'contenttype': '',
            'action': 'set_multiple_references_and_tolerances',
            '_selected_action': [self.uti_3.id, self.uti_6.id],
            'apply': 'Set tolerances and references'
        }
        request.POST = QueryDict('', mutable=True)
        request.POST.update(data)
        admin.set_multiple_references_and_tolerances(
            request, qa_models.UnitTestInfo.objects.filter(id__in=[self.uti_3.id, self.uti_6.id])
        )

        self.uti_3.refresh_from_db()
        self.uti_6.refresh_from_db()
        self.assertListEqual(
            [self.uti_3.reference, self.uti_6.reference],
            [None, None]
        )

    def test_save_multiple_new_ref(self):
        request = self.client.post(self.url_change).wsgi_request
        request.user = self.user
        admin = qa_admin.UnitTestInfoAdmin(qa_models.UnitTestInfo, self.site)
        data = {
            'tolerance': self.tol_2.id,
            'reference': '2.71828',
            'post': 'yes',
            'contenttype': '',
            'action': 'set_multiple_references_and_tolerances',
            '_selected_action': [self.uti_1.id, self.uti_4.id],
            'apply': 'Set tolerances and references'
        }
        request.POST = QueryDict('', mutable=True)
        request.POST.update(data)
        admin.set_multiple_references_and_tolerances(
            request, qa_models.UnitTestInfo.objects.filter(id__in=[self.uti_1.id, self.uti_4.id])
        )

        self.uti_1.refresh_from_db()
        self.uti_4.refresh_from_db()
        self.assertListEqual(
            [self.uti_1.reference.value, self.uti_4.reference.value],
            [2.71828, 2.71828]
        )

    def test_save_multiple_defferent_types(self):
        request = self.client.post(self.url_change).wsgi_request
        request.user = self.user
        admin = qa_admin.UnitTestInfoAdmin(qa_models.UnitTestInfo, self.site)
        admin.set_multiple_references_and_tolerances(
            request, qa_models.UnitTestInfo.objects.all()
        )
        messages = get_messages(request)
        self.assertTrue(constants.ERROR in [m.level for m in messages])

    def test_bad_multiple(self):
        form = modelform_factory(
            qa_models.UnitTestInfo, form=qa_admin.TestInfoForm, fields='__all__'
        )(
            instance=self.uti_3
        )
        data = form.initial
        data['tolerance'] = self.tol_1.id
        form = modelform_factory(
            qa_models.UnitTestInfo, form=qa_admin.TestInfoForm, fields='__all__'
        )(instance=self.uti_3, data=data)
        self.assertFalse(form.is_valid())

    def test_bad_percent_tol(self):
        form = modelform_factory(
            qa_models.UnitTestInfo, form=qa_admin.TestInfoForm, fields='__all__'
        )(instance=self.uti_4)
        data = form.initial
        data['tolerance'] = self.tol_5.id
        data['reference_value'] = 0
        form = modelform_factory(
            qa_models.UnitTestInfo, form=qa_admin.TestInfoForm, fields='__all__'
        )(instance=self.uti_4, data=data)
        self.assertFalse(form.is_valid())
