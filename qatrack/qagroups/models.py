from django.db import models
from django.contrib.auth.models import Group
from django.utils.translation import ugettext as _

class GroupProfile(models.Model):
    group = models.OneToOneField(Group,unique=True)
    #note I used a CharField here so that you can use relative paths
    #for urls (e.g. /qa/daily/test_lists rather than http://localhost/qa/daily/test_lists)
    homepage = models.CharField(max_length=512,help_text=_("Link to where this user should be redirected after login"))

    #----------------------------------------------------------------------
    def __unicode__(self):
        return "<GroupProfile(%s)>"%(self.group.name)
