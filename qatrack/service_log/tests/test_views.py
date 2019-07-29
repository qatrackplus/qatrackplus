import json

from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse
from django.db.models import Q
from django.test import RequestFactory, TestCase
from django.utils import timezone
from django.test.utils import override_settings

from qatrack.accounts.tests.utils import create_group, create_user
from qatrack.parts import models as p_models
from qatrack.qa import models as qa_models
from qatrack.qa.tests import utils as qa_utils
from qatrack.service_log import models, views
from qatrack.service_log.tests import utils as sl_utils


class TestURLS(TestCase):

    def setUp(self):
        u = create_user(is_superuser=True, uname='user', pwd='pwd')
        g = create_group()
        u.groups.add(g)
        u.save()
        self.client.login(username='user', password='pwd')

    def returns_code(self, url, method='get', code=200):
        return getattr(self.client, method)(url).status_code == code

    def test_qa_urls(self):

        sl_utils.create_service_event_status(is_default=True)
        qa_utils.create_status(is_default=True)
        se = sl_utils.create_service_event()
        u = qa_utils.create_unit()
        utc = qa_utils.create_unit_test_collection(unit=u)
        tli = qa_utils.create_test_list_instance(unit_test_collection=utc)

        url_names_200 = (

            ('sl_dash', {}, ''),
            ('sl_new', {}, ''),
            ('sl_edit', {'pk': se.id}, ''),
            ('sl_details', {'pk': se.id}, ''),
            ('sl_list_all', {}, ''),
            ('rtsqa_list_for_event', {'se_pk': se.id}, ''),
            ('se_searcher', {}, '?q=%d&unit_id=%d' % (se.id, u.id)),

            ('tli_select', {'pk': utc.id, 'form': 'a_form'}, ''),
            ('tli_statuses', {}, '?tli_id=%d' % tli.id),
            ('unit_sa_utc', {}, '?unit_id=%d' % u.id),
            ('err', {}, ''),
            ('sl_unit_new', {}, ''),
            ('sl_unit_view_se', {}, ''),
            ('se_down_time', {}, ''),
            ('handle_unit_down_time', {}, ''),
        )

        url_names_404 = (
            # Test urls that expect kwargs when not given any
            # (reverse should render url for use in templates, but return 404)
            ('sl_details', {}, ''),
            ('tli_select', {}, ''),
            ('se_searcher', {}, ''),
            ('tli_statuses', {}, ''),
            ('unit_sa_utc', {}, ''),
        )

        for url, kwargs, q in url_names_200:
            self.assertTrue(self.returns_code(reverse(url, kwargs=kwargs) + q))

        for url, kwargs, q in url_names_404:
            self.assertTrue(self.returns_code(reverse(url, kwargs=kwargs) + q, code=404))


class TestDashboard(TestCase):

    def create_objects(self):

        se_requires_review = sl_utils.create_service_event(is_review_required=True)
        ses_default = sl_utils.create_service_event_status(is_default=True)
        se_default_status = sl_utils.create_service_event(service_status=ses_default)
        sl_utils.create_return_to_service_qa(add_test_list_instance=True)  # qa_not_reviewed +1
        sl_utils.create_return_to_service_qa()  # qa_not_complete +1
        sl_utils.create_return_to_service_qa(
            service_event=se_requires_review
        )  # se_needing_review +1, qa_not_complete +1
        sl_utils.create_return_to_service_qa(service_event=se_default_status)  # se_default +1, qa_not_complete +1

        self.user = create_user(is_superuser=True, uname='person')

    def delete_objects(self):

        models.ServiceEvent.objects.all().delete()
        models.ReturnToServiceQA.objects.all().delete()
        User.objects.all().delete()

    def setUp(self):

        self.factory = RequestFactory()
        self.view = views.SLDashboard.as_view()
        self.url = reverse('sl_dash')

    def test_get_counts(self):

        self.create_objects()

        counts = views.SLDashboard().get_counts()

        self.assertEqual(counts['qa_not_reviewed'], 1)
        self.assertEqual(counts['qa_not_complete'], 3)
        self.assertEqual(counts['se_needing_review'], 1)
        self.assertEqual(counts['se_default']['count'], 1)

#        self.delete_objects()

    def test_get_timeline(self):

        self.create_objects()

        request = self.factory.get(self.url)
        request.user = self.user
        response = self.view(request)

        objs = response.context_data['recent_logs']

        for o in objs:
            self.assertTrue(isinstance(o, models.ServiceLog))

#        self.delete_objects()


class TestCreateServiceEvent(TestCase):

    def setUp(self):

        self.factory = RequestFactory()
        self.view = views.CreateServiceEvent.as_view()

        self.default_ses = sl_utils.create_service_event_status(is_default=True)
        sl_utils.create_service_event_status()
        qa_utils.create_status(is_default=True)

        now = timezone.now()

        self.u_1 = qa_utils.create_unit(name='u_1')
        self.sa_1 = sl_utils.create_service_area(name='sa_1')
        self.usa_1 = sl_utils.create_unit_service_area(unit=self.u_1, service_area=self.sa_1)
        self.tl_1 = qa_utils.create_test_list(name='tl_1')
        self.tli_1_1 = qa_utils.create_test_list_instance(
            unit_test_collection=qa_utils.create_unit_test_collection(unit=self.u_1, test_collection=self.tl_1),
            test_list=self.tl_1,
            work_completed=now - timezone.timedelta(hours=1)
        )
        self.tli_1_2 = qa_utils.create_test_list_instance(
            unit_test_collection=qa_utils.create_unit_test_collection(unit=self.u_1, test_collection=self.tl_1),
            test_list=self.tl_1,
            work_completed=now
        )
        self.se_1 = sl_utils.create_service_event(unit_service_area=self.usa_1)

        self.u_2 = qa_utils.create_unit(name='u_2')
        self.sa_2 = sl_utils.create_service_area(name='sa_2')
        self.usa_2 = sl_utils.create_unit_service_area(unit=self.u_2, service_area=self.sa_2)
        self.tl_2 = qa_utils.create_test_list(name='tl_2')
        self.tli_2_1 = qa_utils.create_test_list_instance(
            unit_test_collection=qa_utils.create_unit_test_collection(unit=self.u_2, test_collection=self.tl_2),
            test_list=self.tl_2,
            work_completed=now - timezone.timedelta(hours=1)
        )
        self.tli_2_2 = qa_utils.create_test_list_instance(
            unit_test_collection=qa_utils.create_unit_test_collection(unit=self.u_2, test_collection=self.tl_2),
            test_list=self.tl_2,
            work_completed=now
        )
        self.se_2 = sl_utils.create_service_event(unit_service_area=self.usa_2)

        self.url = reverse('sl_new')
        self.url_delete = reverse('se_delete')
        self.user = create_user(is_superuser=True)

        self.client.login(username='user', password='password')

        perm = Permission.objects.get(codename='can_have_hours')
        user_can_hours = User.objects.get(username='user')
        user_can_hours.user_permissions.add(perm)
        user_group_has_hours = create_user(uname='in_group_with_hours')
        group_has_hours = create_group(name='can_have_hours')
        group_has_hours.permissions.add(perm)
        user_group_has_hours.groups.add(group_has_hours)

        sl_utils.create_third_party()

        group_linked = create_group(name='linked')
        user_group_linked = create_user(uname='user_in_group_linked')
        user_group_linked.groups.add(group_linked)
        self.gl_1 = sl_utils.create_group_linker(group=group_linked)
        self.part = sl_utils.create_part(add_storage=True)

        self.st = sl_utils.create_service_type()

        self.sto = sl_utils.create_storage(quantity=2)

    def test_initial_options(self):

        response = self.client.get(self.url)

        self.assertEqual(self.default_ses, response.context_data['form'].initial['service_status'])
        self.assertTrue(response.context_data['form'].fields['service_area_field'].widget.attrs['disabled'])
        self.assertTrue(response.context_data['form'].fields['service_event_related_field'].widget.attrs['disabled'])
        self.assertTrue(response.context_data['form'].fields['initiated_utc_field'].widget.attrs['disabled'])

        units = models.Unit.objects.all()

        self.assertEqual(
            list(units.values_list('id', 'name')),
            list(response.context_data['form'].fields['unit_field'].queryset.values_list('id', 'name'))
        )

        models.ServiceType.objects.create(name='st_inactive', is_active=False)
        service_types = models.ServiceType.objects.filter(is_active=True)

        self.assertEqual(
            list(service_types.values_list('id', 'name')),
            list(response.context_data['form'].fields['service_type'].queryset.values_list('id', 'name'))
        )

        perm = Permission.objects.get(codename='can_have_hours')
        user_with_hours = [('', '---------')]
        for u in User.objects.filter(
            Q(groups__permissions=perm, is_active=True) | Q(user_permissions=perm, is_active=True)
        ).distinct():
            name = u.username if not u.first_name or not u.last_name else u.last_name + ', ' + u.first_name
            user_with_hours.append(('user-' + str(u.id), name))
        for tp in models.ThirdParty.objects.all():
            user_with_hours.append(('tp-' + str(tp.id), tp.get_full_name()))
        self.assertEqual(
            set(user_with_hours),
            set(response.context_data['hours_formset'].forms[0].fields['user_or_thirdparty'].widget.choices)
        )

        gl = models.GroupLinker.objects.all().first()
        users_in_gl = User.objects.filter(groups=gl.group, is_active=True)
        self.assertEqual(
            list(users_in_gl), list(response.context_data['form'].fields['group_linker_%s' % gl.pk].queryset)
        )

        # Unit pre selected ----------------------------------------------------
        unit = qa_models.Unit.objects.all().first()
        response = self.client.get(self.url + '?u=%d' % unit.pk)

        service_areas = models.UnitServiceArea.objects.filter(unit_id=unit.pk
                                                              ).values_list('service_area_id', 'service_area__name')
        self.assertEqual(
            list(service_areas),
            list(response.context_data['form'].fields['service_area_field'].queryset.values_list('id', 'name'))
        )

        utc_initialed_by = qa_models.UnitTestCollection.objects.filter(unit_id=unit.pk, active=True)
        utc_ib_list = (('', '---------'),)
        for utc_ib in utc_initialed_by:
            utc_ib_list += ((utc_ib.id, '(%s) %s' % (utc_ib.frequency, utc_ib.name)),)
        self.assertEqual(
            set(utc_ib_list),
            set(response.context_data['form'].fields['initiated_utc_field'].widget.choices)
        )

        qa_utils.create_unit_test_collection(unit=unit, active=False)
        self.assertEqual(
            list(utc_initialed_by.values_list('id', 'name')),
            list(
                response.context_data['rtsqa_formset'].forms[0].fields['unit_test_collection'].queryset.values_list(
                    'id', 'name'
                )
            )
        )

        # Initiated by pre selected --------------------------------------------------
        tli_ib = qa_models.TestListInstance.objects.filter(unit_test_collection__unit=unit).first()
        response = self.client.get(self.url + '?ib=%s' % tli_ib.id)

        self.assertEqual(
            response.context_data['form'].initial['initiated_utc_field'],
            tli_ib.unit_test_collection
        )

        self.assertEqual(
            response.context_data['form'].initial['test_list_instance_initiated_by'].id,
            tli_ib.id
        )

        self.assertEqual(response.context_data['form'].initial['unit_field'], unit)

    def test_submit_valid(self):

        st = sl_utils.create_service_type()

        user = User.objects.filter(groups=self.gl_1.group).first()
        user.user_permissions.add(Permission.objects.get(codename='can_have_hours'))

        data = {
            'datetime_service': timezone.now().strftime(settings.INPUT_DATE_FORMATS[0]),
            'unit_field': self.u_1.id,
            'unit_field_fake': self.u_1.id,
            'service_area_field': self.usa_1.service_area.id,
            'service_type': st.id,
            'problem_description': 'uhhhhh ohhhh',
            'work_description': 'stuff was done',
            'safety_precautions': 'we were careful',
            'qafollowup_notes': 'comment',
            'service_event_related_field': [sl_utils.create_service_event(unit_service_area=self.usa_1).id],
            'service_status': models.ServiceEventStatus.get_default().id,
            'test_list_instance_initiated_by': self.tli_1_1.id,
            'duration_service_time': '4321',
            'duration_lost_time': '1234',
            'initiated_utc_field': self.tli_1_1.unit_test_collection.id,
            'group_linker_1': user.id,

            'hours-INITIAL_FORMS': 0,
            'hours-MAX_NUM_FORMS': 1000,
            'hours-TOTAL_FORMS': 1,
            'hours-MIN_NUM_FORMS': 0,
            'parts-INITIAL_FORMS': 0,
            'parts-MAX_NUM_FORMS': 1000,
            'parts-TOTAL_FORMS': 1,
            'parts-MIN_NUM_FORMS': 0,
            'rtsqa-INITIAL_FORMS': 0,
            'rtsqa-MAX_NUM_FORMS': 1000,
            'rtsqa-TOTAL_FORMS': 1,
            'rtsqa-MIN_NUM_FORMS': 0,

            'hours-0-time': '100',
            'hours-0-user_or_thirdparty': 'user-%s' % user.id,
            'rtsqa-0-all_reviewed': self.tli_1_2.all_reviewed,
            'rtsqa-0-unit_test_collection': self.tli_1_2.unit_test_collection.id,
            'rtsqa-0-test_list_instance': self.tli_1_2.id,
            'parts-0-quantity': 1,
            'parts-0-part': self.part.id,
            'parts-0-from_storage': self.part.storage.all().first().id
        }

        se_count = models.ServiceEvent.objects.count()
        response = self.client.post(self.url, data=data)

        se_id = models.ServiceEvent.objects.filter(problem_description='uhhhhh ohhhh').first().id

        self.assertEqual(se_count + 1, models.ServiceEvent.objects.count())
        self.assertEqual(1, p_models.PartUsed.objects.filter(service_event=se_id).count())
        self.assertEqual(1, models.ReturnToServiceQA.objects.filter(service_event=se_id).count())
        self.assertEqual(1, models.Hours.objects.filter(service_event=se_id).count())

        self.assertEqual(response.status_code, 302)

    @override_settings(SL_ALLOW_BLANK_SERVICE_AREA=False)
    def test_required_fields(self):

        data = {

            'datetime_service': '',
            'unit_field': '',
            'unit_field_fake': '',
            'service_area_field': '',
            'service_type': '',
            'problem_description': '',
            'service_status': '',

            'hours-INITIAL_FORMS': 0,
            'hours-MAX_NUM_FORMS': 1000,
            'hours-TOTAL_FORMS': 1,
            'hours-MIN_NUM_FORMS': 0,
            'parts-INITIAL_FORMS': 0,
            'parts-MAX_NUM_FORMS': 1000,
            'parts-TOTAL_FORMS': 1,
            'parts-MIN_NUM_FORMS': 0,
            'rtsqa-INITIAL_FORMS': 0,
            'rtsqa-MAX_NUM_FORMS': 1000,
            'rtsqa-TOTAL_FORMS': 1,
            'rtsqa-MIN_NUM_FORMS': 0,
        }

        response = self.client.post(self.url, data=data)

        self.assertFalse(response.context_data['form'].is_valid())

        for e in [
            'service_type', 'unit_field', 'service_area_field', 'datetime_service', 'problem_description',
            'service_status'
        ]:
            self.assertTrue(e in response.context_data['form'].errors)

    @override_settings(SL_ALLOW_BLANK_SERVICE_AREA=True)
    def test_blank_sa_ok(self):

        data = {

            'datetime_service': '',
            'unit_field': '',
            'unit_field_fake': '',
            'service_area_field': '',
            'service_type': '',
            'problem_description': '',
            'service_status': '',

            'hours-INITIAL_FORMS': 0,
            'hours-MAX_NUM_FORMS': 1000,
            'hours-TOTAL_FORMS': 1,
            'hours-MIN_NUM_FORMS': 0,
            'parts-INITIAL_FORMS': 0,
            'parts-MAX_NUM_FORMS': 1000,
            'parts-TOTAL_FORMS': 1,
            'parts-MIN_NUM_FORMS': 0,
            'rtsqa-INITIAL_FORMS': 0,
            'rtsqa-MAX_NUM_FORMS': 1000,
            'rtsqa-TOTAL_FORMS': 1,
            'rtsqa-MIN_NUM_FORMS': 0,
        }

        response = self.client.post(self.url, data=data)

        assert 'service_area_field' not in response.context_data['form'].errors

    def test_unreviewed_rtsqa(self):

        ses_approved = sl_utils.create_service_event_status(
            name='Approved', is_review_required=False, rts_qa_must_be_reviewed=True
        )

        test_status = qa_utils.create_status()
        tl = qa_utils.create_test_list()
        t = qa_utils.create_test()
        qa_utils.create_test_list_membership(tl, t)

        tli_unreviewed = qa_utils.create_test_list_instance(test_list=tl)
        qa_utils.create_test_instance(
            tli_unreviewed, unit_test_info=qa_utils.create_unit_test_info(unit=self.u_1), status=test_status
        )

        data = {
            'datetime_service': timezone.now().strftime(settings.INPUT_DATE_FORMATS[0]),
            'unit_field': self.u_1.id,
            'service_area_field': self.sa_1.id,
            'service_type': self.st.id,
            'problem_description': 'problem',
            'service_status': ses_approved.id,

            'hours-INITIAL_FORMS': 0,
            'hours-MAX_NUM_FORMS': 1000,
            'hours-TOTAL_FORMS': 0,
            'hours-MIN_NUM_FORMS': 0,
            'parts-INITIAL_FORMS': 0,
            'parts-MAX_NUM_FORMS': 1000,
            'parts-TOTAL_FORMS': 0,
            'parts-MIN_NUM_FORMS': 0,
            'rtsqa-INITIAL_FORMS': 0,
            'rtsqa-MAX_NUM_FORMS': 1000,
            'rtsqa-TOTAL_FORMS': 1,
            'rtsqa-MIN_NUM_FORMS': 0,

            'rtsqa-0-all_reviewed': tli_unreviewed.all_reviewed,
            'rtsqa-0-unit_test_collection': tli_unreviewed.unit_test_collection.id,
            'rtsqa-0-test_list_instance': tli_unreviewed.id,
            'rtsqa-0-id': '',
        }

        response = self.client.post(self.url, data=data)
        self.assertTrue('service_status' in response.context_data['form'].errors)

        data['rtsqa-0-all_reviewed'] = ''
        data['rtsqa-0-test_list_instance'] = ''

        response = self.client.post(self.url, data=data)
        self.assertTrue('service_status' in response.context_data['form'].errors)

    def test_formset_required_fields(self):

        data = {
            'datetime_service': timezone.now().strftime(settings.INPUT_DATE_FORMATS[0]),
            'unit_field': self.u_1.id,
            'service_area_field': self.sa_1.id,
            'service_type': self.st.id,
            'problem_description': 'problem',
            'service_status': self.default_ses.id,

            'hours-INITIAL_FORMS': 0,
            'hours-MAX_NUM_FORMS': 1000,
            'hours-TOTAL_FORMS': 1,
            'hours-MIN_NUM_FORMS': 0,
            'parts-INITIAL_FORMS': 0,
            'parts-MAX_NUM_FORMS': 1000,
            'parts-TOTAL_FORMS': 1,
            'parts-MIN_NUM_FORMS': 0,
            'rtsqa-INITIAL_FORMS': 0,
            'rtsqa-MAX_NUM_FORMS': 1000,
            'rtsqa-TOTAL_FORMS': 0,
            'rtsqa-MIN_NUM_FORMS': 0,

            'parts-0-part': self.part.id,
            'hours-0-user_or_thirdparty': 'user-%s' % self.user.id
        }

        response = self.client.post(self.url, data=data)
        self.assertTrue('quantity' in response.context_data['part_used_formset'].errors[0])
        self.assertTrue('time' in response.context_data['hours_formset'].errors[0])

        data['parts-0-part'] = ''
        data['parts-0-quantity'] = 1
        data['hours-0-user_or_thirdparty'] = ''
        data['hours-0-time'] = '0030'

        response = self.client.post(self.url, data=data)
        self.assertTrue('part' in response.context_data['part_used_formset'].errors[0])
        self.assertTrue('user_or_thirdparty' in response.context_data['hours_formset'].errors[0])

    def test_delete_service_event(self):

        psc = p_models.PartStorageCollection.objects.first()
        pu = p_models.PartUsed.objects.create(
            part=psc.part, from_storage=psc.storage, quantity=1, service_event=self.se_1
        )
        initial_quantity = pu.quantity

        self.se_1.set_inactive()
        psc.refresh_from_db()
        self.assertEqual(initial_quantity + 1, psc.quantity)

        self.se_1.set_active()
        psc.refresh_from_db()
        self.assertEqual(initial_quantity, psc.quantity)


class TestEditServiceEvent(TestCase):

    def setUp(self):

        self.factory = RequestFactory()
        self.view = views.UpdateServiceEvent.as_view()

        self.default_ses = sl_utils.create_service_event_status(is_default=True)
        self.approved_ses = sl_utils.create_service_event_status(
            is_review_required=False, rts_qa_must_be_reviewed=True
        )
        sl_utils.create_service_event_status()
        qa_utils.create_status(is_default=True)

        now = timezone.now()

        self.u_1 = qa_utils.create_unit(name='u_1')
        self.sa_1 = sl_utils.create_service_area(name='sa_1')
        self.usa_1 = sl_utils.create_unit_service_area(unit=self.u_1, service_area=self.sa_1)
        self.tl_1 = qa_utils.create_test_list(name='tl_1')
        self.tli_1_1 = qa_utils.create_test_list_instance(
            unit_test_collection=qa_utils.create_unit_test_collection(unit=self.u_1, test_collection=self.tl_1),
            test_list=self.tl_1,
            work_completed=now - timezone.timedelta(hours=1)
        )
        self.tli_1_2 = qa_utils.create_test_list_instance(
            unit_test_collection=qa_utils.create_unit_test_collection(unit=self.u_1, test_collection=self.tl_1),
            test_list=self.tl_1,
            work_completed=now
        )
        self.se_1 = sl_utils.create_service_event(unit_service_area=self.usa_1)

        self.u_2 = qa_utils.create_unit(name='u_2')
        self.sa_2 = sl_utils.create_service_area(name='sa_2')
        self.usa_2 = sl_utils.create_unit_service_area(unit=self.u_2, service_area=self.sa_2)
        self.tl_2 = qa_utils.create_test_list(name='tl_2')
        self.tli_2_1 = qa_utils.create_test_list_instance(
            unit_test_collection=qa_utils.create_unit_test_collection(unit=self.u_2, test_collection=self.tl_2),
            test_list=self.tl_2,
            work_completed=now - timezone.timedelta(hours=1)
        )
        self.tli_2_2 = qa_utils.create_test_list_instance(
            unit_test_collection=qa_utils.create_unit_test_collection(unit=self.u_2, test_collection=self.tl_2),
            test_list=self.tl_2,
            work_completed=now
        )
        self.se_2 = sl_utils.create_service_event(unit_service_area=self.usa_2)

        self.url = reverse('sl_new')
        self.user = create_user(is_superuser=True)

        self.client.login(username='user', password='password')

        perm = Permission.objects.get(codename='can_have_hours')
        user_can_hours = User.objects.get(username='user')
        user_can_hours.user_permissions.add(perm)
        user_group_has_hours = create_user(uname='in_group_with_hours')
        group_has_hours = create_group(name='can_have_hours')
        group_has_hours.permissions.add(perm)
        user_group_has_hours.groups.add(group_has_hours)

        sl_utils.create_third_party()

        group_linked = create_group(name='linked')
        user_group_linked = create_user(uname='user_in_group_linked')
        user_group_linked.groups.add(group_linked)
        self.gl_1 = sl_utils.create_group_linker(group=group_linked)
        self.part = sl_utils.create_part(add_storage=True)

        self.st = sl_utils.create_service_type()

        self.se = sl_utils.create_service_event(
            unit_service_area=self.usa_1,
            service_status=self.default_ses,
            service_type=self.st
        )

        self.url = reverse('sl_edit', kwargs={"pk": self.se.pk})

        self.data = {
            'datetime_service': timezone.now().strftime(settings.INPUT_DATE_FORMATS[0]),
            'service_status': self.default_ses.id,
            'service_type': self.st.id,
            'is_review_required': 0,
            'safety_precautions': 'safety_precautions',
            'problem_description': 'problem_description',
            'service_area_field': self.se.unit_service_area.service_area.id,
            'unit_field': self.se.unit_service_area.unit.id,
            'unit_field_fake': self.se.unit_service_area.unit.id,
            'qafollowup_notes': 'qafollowup_notes',
            'test_list_instance_initiated_by': self.tli_1_1.id,
            'duration_lost_time': '0100',
            'duration_service_time': '0100',

            'hours-INITIAL_FORMS': 0,
            'hours-MAX_NUM_FORMS': 1000,
            'hours-TOTAL_FORMS': 0,
            'hours-MIN_NUM_FORMS': 0,
            'parts-INITIAL_FORMS': 0,
            'parts-MAX_NUM_FORMS': 1000,
            'parts-TOTAL_FORMS': 0,
            'parts-MIN_NUM_FORMS': 0,
            'rtsqa-INITIAL_FORMS': 0,
            'rtsqa-MAX_NUM_FORMS': 1000,
            'rtsqa-TOTAL_FORMS': 0,
            'rtsqa-MIN_NUM_FORMS': 0,
        }

    def test_initial_unit(self):

        sl_utils.create_return_to_service_qa(
            service_event=self.se_1, unit_test_collection=self.tli_1_1.unit_test_collection,
            add_test_list_instance=self.tli_1_1
        )

    def test_edit_service_event_valid(self):

        response = self.client.get(self.url)

        data = self.data

        data['hours-TOTAL_FORMS'] = 1
        data['parts-TOTAL_FORMS'] = 1
        data['rtsqa-TOTAL_FORMS'] = 1
        data['parts-0-part'] = self.part.id
        data['parts-0-quantity'] = 1
        data['hours-0-user_or_thirdparty'] = 'user-%s' % self.user.id
        data['hours-0-time'] = '0030'
        data['rtsqa-0-all_reviewed'] = self.tli_1_2.all_reviewed
        data['rtsqa-0-unit_test_collection'] = self.tli_1_2.unit_test_collection.id
        data['rtsqa-0-test_list_instance'] = self.tli_1_2.id
        data['rtsqa-0-id'] = ''

        response = self.client.post(self.url, data=data)

        self.assertEqual(response.status_code, 302)

    def test_edit_status_invalid(self):

        data = self.data
        data['service_status'] = self.approved_ses.id
        data['hours-TOTAL_FORMS'] = 0
        data['parts-TOTAL_FORMS'] = 0
        data['rtsqa-TOTAL_FORMS'] = 0
        data['parts-0-part'] = self.part.id
        data['parts-0-quantity'] = 1
        data['hours-0-user_or_thirdparty'] = 'user-%s' % self.user.id
        data['hours-0-time'] = '0030'
        data['rtsqa-0-all_reviewed'] = self.tli_1_2.all_reviewed
        data['rtsqa-0-unit_test_collection'] = self.tli_1_2.unit_test_collection.id
        data['rtsqa-0-test_list_instance'] = self.tli_1_2.id
        data['rtsqa-0-id'] = ''

        response = self.client.post(self.url, data=data)
        self.assertTrue('service_status' in response.context_data['form'].errors)

        data['rtsqa-0-all_reviewed'] = ''
        data['rtsqa-0-unit_test_collection'] = ''

        response = self.client.post(self.url, data=data)
        self.assertTrue('service_status' in response.context_data['form'].errors)


class TestServiceLogViews(TestCase):

    def setUp(self):

        self.factory = RequestFactory()

        self.user = create_user(is_superuser=True)
        self.client.login(username='user', password='password')

        self.u1 = qa_utils.create_unit()
        self.u2 = qa_utils.create_unit()
        self.u3 = qa_utils.create_unit()

        self.usa1 = sl_utils.create_unit_service_area(unit=self.u1)
        self.usa2 = sl_utils.create_unit_service_area(unit=self.u2)
        self.usa2 = sl_utils.create_unit_service_area(unit=self.u2)
        self.usa3 = sl_utils.create_unit_service_area(unit=self.u3)
        self.usa3 = sl_utils.create_unit_service_area(unit=self.u3)
        self.usa3 = sl_utils.create_unit_service_area(unit=self.u3)

        qa_utils.create_unit_test_collection(unit=self.u1)
        self.utc = qa_utils.create_unit_test_collection(unit=self.u2)
        qa_utils.create_unit_test_collection(unit=self.u2)
        qa_utils.create_unit_test_collection(unit=self.u3)
        qa_utils.create_unit_test_collection(unit=self.u3)
        qa_utils.create_unit_test_collection(unit=self.u3)

        st = sl_utils.create_service_type()

        sl_utils.create_service_event(
            unit_service_area=self.usa1, service_time=timezone.timedelta(minutes=60), service_type=st
        )
        sl_utils.create_service_event(
            unit_service_area=self.usa2, service_time=timezone.timedelta(minutes=60), service_type=st
        )
        sl_utils.create_service_event(
            unit_service_area=self.usa2, service_time=timezone.timedelta(minutes=60),
            problem_description='problem on unit 3 or 2', service_type=st
        )
        sl_utils.create_service_event(
            unit_service_area=self.usa3, service_time=timezone.timedelta(minutes=60), service_type=st
        )
        sl_utils.create_service_event(
            unit_service_area=self.usa3, problem_description='problem on unit 3 or 2',
            service_time=timezone.timedelta(minutes=60), service_type=st
        )
        sl_utils.create_service_event(
            unit_service_area=self.usa3, problem_description='problem on unit 3 or 2',
            service_time=timezone.timedelta(minutes=60), service_type=st
        )

    def test_unit_sa_utc(self):

        tl_to_find = models.UnitTestCollection.objects.filter(unit=self.u3)
        sa_to_find = models.ServiceArea.objects.filter(units=self.u3)

        data = {'unit_id': self.u3.id}
        response = self.client.get(reverse('unit_sa_utc'), data=data)

        self.assertEqual(len(tl_to_find), len(response.json()['utcs']))
        self.assertEqual(len(sa_to_find), len(response.json()['service_areas']))

    def test_se_searcher(self):

        q = models.ServiceEvent.objects.filter(unit_service_area=self.usa3).first().id
        se_to_find = models.ServiceEvent.objects.filter(id__icontains=q, unit_service_area__unit=self.usa3.unit)

        data = {'q': q, 'unit_id': self.usa3.unit.id}
        response = self.client.get(reverse('se_searcher'), data=data)

        self.assertEqual(len(se_to_find), len(response.json()['service_events']))

    def test_tli_statuses(self):

        tli = qa_utils.create_test_list_instance(unit_test_collection=self.utc)
        qa_utils.create_test_instance(test_list_instance=tli)
        qa_utils.create_test_instance(test_list_instance=tli)

        expected = json.loads(
            json.dumps(
                {
                    'pass_fail': tli.pass_fail_summary(),
                    'review': tli.review_summary(),
                    'datetime': timezone.localtime(tli.created).replace(microsecond=0),
                    'all_reviewed': int(tli.all_reviewed),
                    'work_completed': timezone.localtime(tli.work_completed).replace(microsecond=0),
                    'in_progress': tli.in_progress,
                },
                cls=DjangoJSONEncoder,
            )
        )

        data = {'tli_id': tli.id}

        response = self.client.get(reverse('tli_statuses'), data=data)

        self.assertDictEqual(
            expected,
            response.json()
        )

    def test_handle_unit_down_time(self):

        data = {
            'problem_description': 'problem on unit 3 or 2',
            'service_area': [self.usa3.service_area.name, self.usa2.service_area.name],
            'unit': [self.usa3.unit.name, self.usa2.unit.name],
            'unit__type': [self.u3.type.name, self.u2.type.name],
            'daterange': '%s - %s' % (
                (timezone.now() - timezone.timedelta(days=30)).strftime('%d %b %Y'),
                timezone.now().strftime('%d %b %Y')
            )
        }

        response = self.client.get(reverse('handle_unit_down_time'), data=data)
        csv = str(response.content)

        self.assertTrue('problem on unit 3 or 2' in csv)
        self.assertTrue(self.usa3.service_area.name in csv)
        self.assertTrue(self.usa2.service_area.name in csv)
        self.assertTrue('%s,%s,0,1,1.00,0.00,1.00,0.00,1' % (self.usa2.unit.name, self.usa2.unit.type.name) in csv)
        self.assertTrue('%s,%s,0,2,2.00,0.00,2.00,0.00,2' % (self.usa3.unit.name, self.usa3.unit.type.name) in csv)
        self.assertTrue('Totals:,0.0,3,3.00,0.00,3.00,0.00,3' in csv)
