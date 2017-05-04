
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext as _

from qatrack.units import models as u_models
from qatrack.service_log import models as sl_models


class Supplier(models.Model):

    name = models.CharField(max_length=32, unique=True)
    notes = models.TextField(
        max_length=255, blank=True, null=True, help_text=_('Additional comments about this supplier')
    )

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class RoomManager(models.Manager):

    def get_queryset(self):
        return super(RoomManager, self).get_queryset().select_related('site')


class Room(models.Model):

    site = models.ForeignKey(u_models.Site, blank=True, null=True, help_text=_('Site this storage room is located'))
    name = models.CharField(max_length=32, help_text=_('Name of room or room number'))

    objects = RoomManager()

    class Meta:
        ordering = ['site', 'name']
        unique_together = ['site', 'name']

    def __str__(self):
        return '%s%s' % (self.name, ' (%s)' % self.site.name if self.site else '')


class StorageManager(models.Manager):

    def get_queryset(self):
        return super(StorageManager, self).get_queryset().select_related('room')


class Storage(models.Model):

    room = models.ForeignKey(Room, blank=True, null=True, help_text=_('Room for part storage'))

    location = models.CharField(max_length=32, blank=True, null=True)
    description = models.TextField(max_length=255, null=True, blank=True)

    objects = StorageManager()

    class Meta:
        verbose_name_plural = 'Storage'
        unique_together = ['room', 'location']

    def __str__(self):
        items = []
        if self.room:
            if self.room.site:
                items.append(self.room.site.name)
            items.append(self.room.name)
        if self.location:
            items.append(self.location)

        return ' - '.join(items)


class PartCategory(models.Model):

    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Part(models.Model):

    part_categories = models.ManyToManyField(
        PartCategory, blank=True, null=True, help_text=_('Categories for this part'), related_name='parts'
    )
    suppliers = models.ManyToManyField(
        Supplier, blank=True, null=True, help_text=_('Suppliers of this part'), related_name='parts',
        through='PartSupplierCollection'
    )
    storage = models.ManyToManyField(
        Storage, through='PartStorageCollection', related_name='parts', help_text=_('Storage locations for this part')
    )

    part_number = models.CharField(max_length=32, help_text=_('Part number'), unique=True)
    alt_part_number = models.CharField(
        max_length=32, help_text=_('Alternate part number'), blank=True, null=True
    )
    description = models.TextField(help_text=_('Brief description of this part'))
    quantity_min = models.PositiveIntegerField(
        default=0, help_text=_('Notify when the number parts falls below this number in storage'),
    )
    quantity_current = models.PositiveIntegerField(help_text=_('The number of parts in storage currently'), default=0, editable=False)
    cost = models.DecimalField(default=0, decimal_places=2, max_digits=10, help_text=_('Cost of this part'))
    notes = models.TextField(max_length=255, blank=True, null=True, help_text=_('Additional comments about this part'))
    is_obsolete = models.BooleanField(default=False, help_text=_('Is this part now obsolete'), verbose_name=_('Obsolete'))

    def __str__(self):
        return '%s%s - %s' % (self.part_number, ' (%s)' % self.alt_part_number if self.alt_part_number else '', self.description)

    def set_quantity_current(self):
        qs = PartStorageCollection.objects.filter(part=self, storage__isnull=False)
        if qs.exists():
            self.quantity_current = qs.aggregate(models.Sum('quantity'))['quantity__sum']
        else:
            self.quantity_current = 0
        self.quantity_current = self.quantity_current if self.quantity_current >= 0 else 0
        self.save()


class PartStorageCollectionManager(models.Manager):

    def get_queryset(self):
        return super(PartStorageCollectionManager, self).get_queryset().select_related('storage', 'part')


class PartStorageCollection(models.Model):

    part = models.ForeignKey(Part)
    storage = models.ForeignKey(Storage)

    quantity = models.IntegerField()

    objects = PartStorageCollectionManager()

    class Meta:
        unique_together = ('part', 'storage')

    def save(self, *args, **kwargs):
        # if self.quantity > 0:
        #     super(PartStorageCollection, self).save(*args, **kwargs)
        #     self.part.set_quantity_current()
        # elif self.id:
        #     part = self.part
        #     self.delete()
        #     part.set_quantity_current()
        self.quantity = self.quantity if self.quantity >= 0 else 0
        super(PartStorageCollection, self).save(*args, **kwargs)
        self.part.set_quantity_current()

    def __str__(self):
        locs = []
        if self.storage.room.site:
            locs.append(self.storage.room.site.name)
        locs.append(self.storage.room.name)
        if self.storage.location:
            locs.append(self.storage.location)
        locs.append('(%s)' % self.quantity)
        return ' - '.join(locs)


class PartSupplierCollection(models.Model):

    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    part_number = models.CharField(
        max_length=32, null=True, blank=True,
        help_text=_('Does this supplier have a different part number for this part')
    )

    class Meta:
        unique_together = ('part', 'supplier')


class PartUsed(models.Model):

    service_event = models.ForeignKey(sl_models.ServiceEvent, on_delete=models.CASCADE)
    part = models.ForeignKey(Part, help_text=_('Select the part used'), on_delete=models.CASCADE)
    from_storage = models.ForeignKey(Storage, null=True, blank=True, on_delete=models.SET_NULL)

    quantity = models.IntegerField()

