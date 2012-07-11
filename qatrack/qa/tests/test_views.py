from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.client import Client
from django.test.utils import setup_test_environment
from django.utils import unittest,timezone

from django.contrib.auth.models import User, Group
from qatrack.qa import models
from qatrack.units.models import Unit, UnitType, Modality, ELECTRON, PHOTON
from qatrack import settings
import re

import utils

#====================================================================================
class TestURLS(TestCase):
    """just test urls to make sure at the very least they are valid and return 200"""

    #---------------------------------------------------------------------------
    def setUp(self):
        u = utils.create_user()
        self.client.login(username="user",password="password")
    #---------------------------------------------------------------------------        
    def returns_200(self,url,method="get"):
        return getattr(self.client,method)(url).status_code == 200    
        
    #---------------------------------------------------------------------------
    def test_home(self):
        self.assertTrue(self.returns_200("/"))
    #---------------------------------------------------------------------------
    def test_login(self):
        self.assertTrue(self.returns_200(settings.LOGIN_URL))
    #---------------------------------------------------------------------------
    def test_login_redirect(self):
        self.assertTrue(self.returns_200(settings.LOGIN_REDIRECT_URL))
    #---------------------------------------------------------------------------
    def test_composite(self):
        self.assertTrue(self.returns_200("/qa/composite/",method="post"))        
    #---------------------------------------------------------------------------
    def test_review(self):
        self.assertTrue(self.returns_200("/qa/review/"))        
    #---------------------------------------------------------------------------
    def test_charts(self):
        self.assertTrue(self.returns_200("/qa/charts/"))            
    #-----------------------------------------------------------        
    def test_charts_export(self):
        self.assertTrue(self.returns_200("/qa/charts/export/"))        
    #---------------------------------------------------------------------------
    def test_charts_control_chart(self):
        self.assertTrue(self.returns_200("/qa/charts/control_chart.png"))        
    #---------------------------------------------------------------------------
    def test_unit_group_frequency(self):
        self.assertTrue(self.returns_200("/qa/daily/"))        

    #---------------------------------------------------------------------------
    def test_perform(self):
        utils.create_status()
        utils.create_unit_test_collection()
        self.assertTrue(self.returns_200("/qa/1"))                
        self.assertTrue(404==self.client.get("/qa/2").status_code)
    #---------------------------------------------------------------------------
    def test_unit_frequency(self):
        self.assertTrue(self.returns_200("/qa/daily/unit/1/"))
        