from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from qatrack.parts.models import PartSupplierCollection, PartUsed
from qatrack.service_log.tests import utils as sl_utils


class BasePartsAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.client.force_authenticate(user=self.user)

class SupplierAPIViewSetTests(BasePartsAPITestCase):
    def setUp(self):
        super().setUp()
        self.supplier = sl_utils.create_supplier()

    def test_list(self):
        url = reverse('supplier-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve(self):
        url = reverse('supplier-detail', args=[self.supplier.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        url = reverse('supplier-list')
        data = {'name': 'New Supplier'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update(self):
        url = reverse('supplier-detail', args=[self.supplier.id])
        data = {'name': 'Updated Supplier'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        url = reverse('supplier-detail', args=[self.supplier.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class StorageAPIViewSetTests(BasePartsAPITestCase):
    def setUp(self):
        super().setUp()
        self.room = sl_utils.create_room()
        self.storage = sl_utils.create_storage(room=self.room, location='shelf 1')

    def test_list(self):
        url = reverse('storage-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve(self):
        url = reverse('storage-detail', args=[self.storage.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        url = reverse('storage-list')
        data = {
            'room': self.room.id,
            'location': 'New Location'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update(self):
        url = reverse('storage-detail', args=[self.storage.id])
        data = {'location': 'Updated Location'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        url = reverse('storage-detail', args=[self.storage.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class PartCategoryAPIViewSetTests(BasePartsAPITestCase):
    def setUp(self):
        super().setUp()
        self.category = sl_utils.create_part_category()

    def test_list(self):
        url = reverse('partcategory-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve(self):
        url = reverse('partcategory-detail', args=[self.category.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        url = reverse('partcategory-list')
        data = {'name': 'New Category'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update(self):
        url = reverse('partcategory-detail', args=[self.category.id])
        data = {'name': 'Updated Category'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        url = reverse('partcategory-detail', args=[self.category.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class PartAPIViewSetTests(BasePartsAPITestCase):
    def setUp(self):
        super().setUp()
        self.category = sl_utils.create_part_category()
        self.part = sl_utils.create_part(part_category=self.category, part_number='P1')

    def test_list(self):
        url = reverse('part-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve(self):
        url = reverse('part-detail', args=[self.part.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        url = reverse('part-list')
        data = {
            'part_category': reverse('partcategory-detail', args=[self.category.id]),
            'part_number': 'P2',
            'name': 'New Part',
            'quantity_current': 0,
            'quantity_min': 0,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update(self):
        url = reverse('part-detail', args=[self.part.id])
        data = {'name': 'Updated Part'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        url = reverse('part-detail', args=[self.part.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class PartStorageCollectionAPIViewSetTests(BasePartsAPITestCase):
    def setUp(self):
        super().setUp()
        self.part = sl_utils.create_part()
        self.storage = sl_utils.create_storage()
        self.psc = sl_utils.create_part_storage_collection(part=self.part, storage=self.storage)

    def test_list(self):
        url = reverse('partstoragecollection-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve(self):
        url = reverse('partstoragecollection-detail', args=[self.psc.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        new_storage = sl_utils.create_storage(location="shelf 2")
        url = reverse('partstoragecollection-list')
        data = {
            'part': reverse('part-detail', args=[self.part.id]),
            'storage': reverse('storage-detail', args=[new_storage.id]),
            'quantity': 5
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update(self):
        url = reverse('partstoragecollection-detail', args=[self.psc.id])
        data = {'quantity': 10}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        url = reverse('partstoragecollection-detail', args=[self.psc.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class PartSupplierCollectionAPIViewSetTests(BasePartsAPITestCase):
    def setUp(self):
        super().setUp()
        self.part = sl_utils.create_part()
        self.supplier = sl_utils.create_supplier()
        self.psc = PartSupplierCollection.objects.create(part=self.part, supplier=self.supplier, part_number='PS1')

    def test_list(self):
        url = reverse('partsuppliercollection-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve(self):
        url = reverse('partsuppliercollection-detail', args=[self.psc.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        new_supplier = sl_utils.create_supplier(name='New Supplier')
        url = reverse('partsuppliercollection-list')
        data = {
            'part': reverse('part-detail', args=[self.part.id]),
            'supplier': reverse('supplier-detail', args=[new_supplier.id]),
            'part_number': 'PS2'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update(self):
        url = reverse('partsuppliercollection-detail', args=[self.psc.id])
        data = {'part_number': 'PS3'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        url = reverse('partsuppliercollection-detail', args=[self.psc.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class PartUsedAPIViewSetTests(BasePartsAPITestCase):
    def setUp(self):
        super().setUp()
        self.part = sl_utils.create_part()
        self.site = sl_utils.create_site()
        self.room = sl_utils.create_room(site=self.site)
        self.storage = sl_utils.create_storage(room=self.room, location='shelf 1')
        self.se = sl_utils.create_service_event()
        
        self.psc = sl_utils.create_part_storage_collection(
            part=self.part, storage=self.storage, quantity=10
        )
        self.pu = PartUsed.objects.create(
            part=self.part, service_event=self.se, from_storage=self.storage, quantity=2
        )
        self.pu.remove_from_storage()

    def test_list(self):
        url = reverse('partused-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve(self):
        url = reverse('partused-detail', args=[self.pu.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_part_used(self):
        url = reverse('partused-list')
        data = {
            'part': reverse('part-detail', args=[self.part.id]),
            'service_event': reverse('serviceevent-detail', args=[self.se.id]),
            'from_storage': reverse('storage-detail', args=[self.storage.id]),
            'quantity': 2
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.psc.refresh_from_db()
        self.assertEqual(self.psc.quantity, 6)

    def test_update_part_used(self):
        url = reverse('partused-detail', args=[self.pu.id])
        data = {
            'part': reverse('part-detail', args=[self.part.id]),
            'service_event': reverse('serviceevent-detail', args=[self.se.id]),
            'from_storage': reverse('storage-detail', args=[self.storage.id]),
            'quantity': 5
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.psc.refresh_from_db()
        self.assertEqual(self.psc.quantity, 5)

    def test_update_part_used_change_storage(self):
        new_storage = sl_utils.create_storage(room=self.room, location='shelf 2')
        new_psc = sl_utils.create_part_storage_collection(
            part=self.part, storage=new_storage, quantity=5
        )

        url = reverse('partused-detail', args=[self.pu.id])
        data = {
            'part': reverse('part-detail', args=[self.part.id]),
            'service_event': reverse('serviceevent-detail', args=[self.se.id]),
            'from_storage': reverse('storage-detail', args=[new_storage.id]),
            'quantity': 3
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.psc.refresh_from_db()
        self.assertEqual(self.psc.quantity, 10)
        
        new_psc.refresh_from_db()
        self.assertEqual(new_psc.quantity, 2)

    def test_delete_part_used(self):
        url = reverse('partused-detail', args=[self.pu.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.psc.refresh_from_db()
        self.assertEqual(self.psc.quantity, 10)
