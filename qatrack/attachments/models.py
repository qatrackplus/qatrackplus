import os
import os.path

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

import qatrack.qa.models as qam
from qatrack.units.models import Unit

def get_upload_path(instance, filename):
    return settings.TMP_UPLOAD_ROOT


class Attachment(models.Model):

    attachment = models.FileField(verbose_name=_("Attachment"), upload_to=get_upload_path)
    comment = models.TextField(verbose_name=_("Comment"), blank=True)

    test = models.ForeignKey(qam.Test, null=True)
    testlist = models.ForeignKey(qam.TestList, null=True)
    testlistcycle = models.ForeignKey(qam.TestListCycle, null=True)
    testinstance = models.ForeignKey(qam.TestInstance, null=True)
    testlistinstance = models.ForeignKey(qam.TestListInstance, null=True)
    unit = models.ForeignKey(Unit, null=True)
    unittestcollection = models.ForeignKey(qam.UnitTestCollection, null=True)

    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, editable=False)

    @property
    def _possible_owners(self):

        return  [
            self.test,
            self.testlist,
            self.testlistcycle,
            self.testinstance,
            self.testlistinstance,
            self.unit,
            self.unittestcollection,
        ]

    @property
    def owner(self):
        """Foreign key object that owns this attachment"""
        try:
            return next(o for o in self._possible_owners if o)
        except StopIteration:
            return None

    @property
    def type(self):
        """Model type of foreign owner e.g. 'testlist' or 'unittestcollection'"""
        return self.owner._meta.model_name

    def move_tmp_file(self, save=True):
        """Move from temp location to permanent location"""

        if self.finalized:
            return

        start_path = self.attachment.path
        name_parts = [
            self.type,
            str(self.owner.pk),
            self.attachment.name
        ]
        new_name = '/'.join(name_parts)
        new_path = os.path.join(settings.UPLOAD_ROOT, *name_parts)

        if not os.path.exists(os.path.dirname(new_path)):
            os.makedirs(os.path.dirname(new_path))

        os.rename(start_path, new_path)

        self.attachment.name = new_name

        if save:
            self.save()

    @property
    def has_owner(self):
        """Return bool indicating whether this attachment is owned or not"""
        return bool(self.owner and self.owner.pk)

    @property
    def is_in_tmp(self):
        """Return bool indicating whether this attachment is currently in staging area"""
        return settings.TMP_UPLOAD_ROOT in self.attachment.path

    @property
    def finalized(self):
        """Return bool indicating whether this has been finalized yet"""
        return self.has_owner and not self.is_in_tmp

    @property
    def can_finalize(self):
        """Return bool indicating whether this file is ready to be finalized"""
        return self.has_owner and self.is_in_tmp

    def save(self, *args, **kwargs):
        """Save model and move it to final location if possible"""

        super(Attachment, self).save(*args, **kwargs)

        if self.can_finalize:
            self.move_tmp_file()

    def __str__(self):
        return "Attachment(%s, %s)" % (self.owner or _("No Owner"), self.attachment.name)




