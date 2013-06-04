from django.db import models


#============================================================================
class Contact(models.Model):
    """basic contact number"""
    name = models.CharField(max_length=256)
    number = models.CharField(max_length=256)
    description = models.TextField()

    #----------------------------------------------------------------------
    def __unicode__(self):
        return "%s : %s " % (self.name, self.number)
