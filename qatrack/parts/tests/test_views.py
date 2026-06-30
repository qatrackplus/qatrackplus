from django.db.models import Q
from django.test import RequestFactory, TestCase
from django.urls import reverse

from qatrack.parts import models as p_models
from qatrack.parts import views as p_views
from qatrack.qa.tests import utils as qa_utils
from qatrack.service_log.tests import utils as sl_utils


class TestCreatePart(TestCase):

    def setUp(self):

        self.factory = RequestFactory()
        self.view = p_views.PartUpdateCreate.as_view()

        self.url = reverse('part_new')
        self.user = qa_utils.create_user(is_superuser=True)

        self.client.login(username='user', password='password')

        self.pc = sl_utils.create_part_category()
        self.sup = sl_utils.create_supplier()
        self.sto = sl_utils.create_storage()

        self.data = {
            'part_number': 'p001',
            'new_or_used': 'both',
            'cost': '1',
            'quantity_min': 0,
            'name': 'description',
            'alt_part_number': 'alt-num',
            'part_category': self.pc.id,
            'notes': 'This is a part',
            'is_obsolete': 0,
            'storage-MAX_NUM_FORMS': 1000,
            'storage-MIN_NUM_FORMS': 0,
            'storage-TOTAL_FORMS': 0,
            'storage-INITIAL_FORMS': 0,
            'supplier-MAX_NUM_FORMS': 1000,
            'supplier-MIN_NUM_FORMS': 0,
            'supplier-TOTAL_FORMS': 0,
            'supplier-INITIAL_FORMS': 0,
        }

    def test_initial_options(self):

        response = self.client.get(self.url)

        part_categories = p_models.PartCategory.objects.all()
        self.assertEqual(
            list(part_categories.values_list('id', 'name')),
            list(response.context_data['form'].fields['part_category'].queryset.values_list('id', 'name'))
        )

        suppliers = p_models.Supplier.objects.all()
        self.assertEqual(
            list(suppliers.values_list('id', 'name')),
            list(
                response.context_data['supplier_formset'].forms[0].fields['supplier'].queryset.values_list(
                    'id', 'name'
                ),
            )
        )

        room = p_models.Room.objects.all()
        self.assertEqual(
            list(room.values_list('id', 'name')),
            list(response.context_data['storage_formset'].forms[0].fields['room'].queryset.values_list('id', 'name'))
        )

    def test_submit_valid(self):

        data = self.data

        data['storage-TOTAL_FORMS'] = 1
        data['storage-0-room'] = self.sto.room.id
        data['storage-0-quantity'] = 1
        data['storage-0-part'] = ''
        data['storage-0-id'] = ''
        data['storage-0-storage_field'] = self.sto.id
        data['supplier-TOTAL_FORMS'] = 1
        data['supplier-0-part'] = ''
        data['supplier-0-part_number'] = 'sup_part000'
        data['supplier-0-supplier'] = self.sup.id
        data['supplier-0-id'] = ''

        count = p_models.Part.objects.count()
        self.client.post(self.url, data=data)
        self.assertEqual(count + 1, p_models.Part.objects.count())

    def test_required(self):

        data = self.data

        data['part_number'] = ''
        data['cost'] = ''
        data['quantity_min'] = ''
        data['name'] = ''

        data['storage-TOTAL_FORMS'] = 1
        data['storage-0-quantity'] = 1
        data['storage-0-storage_field'] = self.sto.id
        data['supplier-TOTAL_FORMS'] = 1
        data['supplier-0-part'] = ''
        data['supplier-0-part_number'] = 'sup_part000'
        data['supplier-0-id'] = ''

        response = self.client.post(self.url, data=data)

        for f in ['part_number', 'quantity_min', 'name']:
            self.assertTrue(f in response.context_data['form'].errors)

        self.assertTrue('supplier' in response.context_data['supplier_formset'].forms[0].errors)

    def test_incorrect_storage_combination(self):

        data = self.data
        data['storage-TOTAL_FORMS'] = 1
        data['storage-0-quantity'] = 1
        data['storage-0-storage_field'] = self.sto.id

        response = self.client.post(self.url, data=data)

        self.assertTrue('__all__' in response.context['storage_formset'].forms[0].errors)


class TestEditPart(TestCase):

    def setUp(self):

        self.factory = RequestFactory()
        self.view = p_views.PartUpdateCreate.as_view()

        self.pc = sl_utils.create_part_category()
        self.p = sl_utils.create_part(part_category=self.pc)
        self.pc_2 = sl_utils.create_part_category()

        self.url = reverse('part_edit', kwargs={"pk": self.p.pk})
        self.user = qa_utils.create_user(is_superuser=True)

        self.client.login(username='user', password='password')

        self.sup = sl_utils.create_supplier()
        self.sto = sl_utils.create_storage()

        self.data = {
            'part_number': 'p001',
            'new_or_used': 'both',
            'cost': '1',
            'quantity_min': 0,
            'name': 'description',
            'alt_part_number': 'alt-num',
            'part_category': self.pc.id,
            'notes': 'This is a part',
            'is_obsolete': 0,
            'storage-MAX_NUM_FORMS': 1000,
            'storage-MIN_NUM_FORMS': 0,
            'storage-TOTAL_FORMS': 0,
            'storage-INITIAL_FORMS': 0,
            'supplier-MAX_NUM_FORMS': 1000,
            'supplier-MIN_NUM_FORMS': 0,
            'supplier-TOTAL_FORMS': 0,
            'supplier-INITIAL_FORMS': 0,
        }

    def test_submit_valid(self):

        data = self.data

        data['storage-0-quantity'] = 1
        data['storage-0-storage_field'] = self.sto.id
        data['storage-0-room'] = self.sto.room.id
        data['supplier-0-part'] = ''
        data['supplier-0-part_number'] = 'sup_part000'
        data['supplier-0-id'] = ''
        data['supplier-0-supplier'] = self.sup.id
        data['storage-TOTAL_FORMS'] = 1
        data['supplier-TOTAL_FORMS'] = 1

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

    def test_new_storage_location(self):

        data = self.data

        data['storage-TOTAL_FORMS'] = 1
        data['storage-0-quantity'] = 1
        data['storage-0-location'] = '__new__new_storage'
        data['storage-0-storage_field'] = '__new__new_storage'
        data['storage-0-room'] = self.sto.room.id

        count = p_models.PartStorageCollection.objects.filter(part=self.p, storage__location='new_storage').count()
        self.client.post(self.url, data=data)
        self.assertEqual(
            count + 1,
            p_models.PartStorageCollection.objects.filter(part=self.p, storage__location='new_storage').count()
        )


class TestPartViews(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.user = qa_utils.create_user(is_superuser=True)
        self.client.login(username='user', password='password')

        sl_utils.create_part(part_number='find_1', add_storage=True)
        sl_utils.create_part(part_number='find_2', add_storage=True)
        sl_utils.create_part(part_number='find_3', add_storage=True)
        sl_utils.create_part(name='a part to find', add_storage=True)
        sl_utils.create_part(name='a part to find', add_storage=True)

    def test_parts_searcher(self):

        parts_to_find = p_models.Part.objects.filter(Q(part_number__icontains='find') | Q(name__icontains='find'))
        data = {'q': 'find'}
        response = self.client.get(reverse('parts_searcher'), data=data)
        self.assertEqual(len(parts_to_find), len(response.json()['data']))

    def test_storage_searcher(self):

        part = p_models.Part.objects.first()

        p_models.PartStorageCollection.objects.create(quantity=1, part=part, storage=sl_utils.create_storage())

        storage_to_find = p_models.PartStorageCollection.objects.filter(part=part)

        data = {'p_id': part.id}

        response = self.client.get(reverse('parts_storage_searcher'), data=data)
        self.assertEqual(len(storage_to_find), len(response.json()['data']))

    def test_storage_searcher_clear(self):
        data = {'p_id': ''}
        response = self.client.get(reverse('parts_storage_searcher'), data=data)
        self.assertEqual('__clear__', response.json()['data'])

    def test_room_location_searcher(self):

        room = p_models.Room.objects.first()
        data = {'r_id': room.id}

        storage_to_find = p_models.Storage.objects.filter(room__id=room.id, location__isnull=False)

        response = self.client.get(reverse('room_location_searcher'), data=data)

        self.assertEqual(len(storage_to_find), len(response.json()['storage']))

    def test_room_location_searcher_clear(self):
        data = {'r_id': ''}
        response = self.client.get(reverse('room_location_searcher'), data=data)
        self.assertEqual('__clear__', response.json()['data'])

    def test_part_list(self):
        self.client.get(reverse('parts_list'))

    def test_parts_low_title(self):
        response = self.client.get(reverse('low_inventory_parts_list'))
        self.assertContains(response, 'Low Inventory Parts')
