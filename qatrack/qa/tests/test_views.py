from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.client import Client, RequestFactory
from django.test.utils import setup_test_environment
from django.utils import unittest,timezone

from django.contrib.auth.models import User, Group
from qatrack.qa import models,views,forms
from qatrack.units.models import Unit, UnitType, Modality, ELECTRON, PHOTON
from qatrack import settings

import django.forms

import datetime
import json
import random
import re
import os
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



#============================================================================
class TestControlChartImage(TestCase):

    #----------------------------------------------------------------------
    def setUp(self):
        self.factory = RequestFactory()
        self.old_cc_available = views.CONTROL_CHART_AVAILABLE
        print views.CONTROL_CHART_AVAILABLE
        self.view = views.ControlChartImage.as_view()
        self.url = reverse("control_chart")
    #----------------------------------------------------------------------
    def tearDown(self):
        views.CONTROL_CHART_AVAILABLE = self.old_cc_available

    #----------------------------------------------------------------------
    def test_cc_not_available(self):
        views.CONTROL_CHART_AVAILABLE = False

        cc_not_available_image = open(os.path.join(settings.PROJECT_ROOT,"qa","static","img","control_charts_not_available.png"),"rb").read()

        request = self.factory.get(self.url)
        response =  self.view(request)

        self.assertEqual(response.content,cc_not_available_image)

    #----------------------------------------------------------------------
    def test_not_enough_data(self):
        request = self.factory.get(self.url)
        response =  self.view(request)
        self.assertTrue(response.get("content-type"),"image/png")
    #----------------------------------------------------------------------
    def test_baseline_subgroups(self):
        for n in [-1,0,1,2,"nonnumber"]:
            request = self.factory.get(self.url+"?n_base_subgroups=%s"%n)
            response =  self.view(request)
            self.assertTrue(response.get("content-type"),"image/png")
    #----------------------------------------------------------------------
    def test_baseline_subgroups(self):
        for n in [-1,0,1,2,200,"nonnumber"]:
            request = self.factory.get(self.url+"?subgroup_size=%s"%n)
            response =  self.view(request)
            self.assertTrue(response.get("content-type"),"image/png")
    #----------------------------------------------------------------------
    def test_include_fit(self):
        for f in ["true","false"]:
            request = self.factory.get(self.url+"?fit_data=%s"%f)
            response =  self.view(request)
            self.assertTrue(response.get("content-type"),"image/png")
    #----------------------------------------------------------------------
    def make_url(self,slug,unumber,from_date,to_date,sg_size=2,n_base=2,fit="true"):
        url = self.url+"?subgroup_size=%s&n_baseline_subgroups=%s&fit_data=%s" %(sg_size,n_base,fit)
        url+= "&slug=%s"%slug
        url+= "&unit=%s"%unumber
        url+= "&from_date=%s"%from_date.strftime(settings.SIMPLE_DATE_FORMAT)
        url+= "&to_date=%s"%to_date.strftime(settings.SIMPLE_DATE_FORMAT)
        return url
    #----------------------------------------------------------------------
    def test_valid(self):
        test = utils.create_test()
        unit = utils.create_unit()
        status = utils.create_status()
        yesterday = datetime.date.today()-datetime.timedelta(days=1)
        tomorrow = yesterday+datetime.timedelta(days=2)

        url = self.make_url(test.slug,unit.number,yesterday,yesterday)
        request = self.factory.get(url)
        response =  self.view(request)
        self.assertTrue(response.get("content-type"),"image/png")

        url = self.make_url(test.slug,unit.number,yesterday,tomorrow)

        for n in (1,1,8,90):
            for x in range(n):
                utils.create_test_instance(
                    value=random.gauss(1,1),
                    test=test,
                    unit=unit,
                    status=status
                )



            request = self.factory.get(url)
            response =  self.view(request)
            self.assertTrue(response.get("content-type"),"image/png")

    #----------------------------------------------------------------------
    def test_invalid(self):
        test = utils.create_test()
        unit = utils.create_unit()
        status = utils.create_status()
        yesterday = datetime.date.today()-datetime.timedelta(days=1)
        tomorrow = yesterday+datetime.timedelta(days=2)

        url = self.make_url(test.slug,unit.number,yesterday,yesterday)
        request = self.factory.get(url)
        response =  self.view(request)
        self.assertTrue(response.get("content-type"),"image/png")

        url = self.make_url(test.slug,unit.number,yesterday,tomorrow,fit="true")

        #generate some data that the control chart fit function won't be able to fit
        for x in range(10):
            utils.create_test_instance(
                value=x,
                test=test,
                unit=unit,
                status=status
            )

        request = self.factory.get(url)
        response =  self.view(request)
        self.assertTrue(response.get("content-type"),"image/png")

#============================================================================
class TestComposite(TestCase):
    #----------------------------------------------------------------------
    def setUp(self):
        self.factory = RequestFactory()
        self.view = views.CompositeCalculation.as_view()
        self.url = reverse("composite")

        self.t1 = utils.create_test(name="test1")
        self.t2 = utils.create_test(name="test2")
        self.tc = utils.create_test(name="testc",test_type=models.COMPOSITE)
        self.tc.calculation_procedure = "result = test1 + test2"
        self.tc.save()

    #----------------------------------------------------------------------
    def test_composite(self):

        data =  {
            u'qavalues': [
                u'{"testc":{"name":"testc","current_value":""},"test1":{"name":"test1","current_value":1},"test2":{"name":"test2","current_value":2}}'
            ],
            u'composite_ids': [u'{"testc":"3"}']
        }


        request = self.factory.post(self.url,data=data)
        response = self.view(request)
        values = json.loads(response.content)
        expected = {
            "errors": [],
            "results": {
                "testc": {
                    "value": 3.0,
                    "error": None
                }
            },
            "success": True
        }
        self.assertDictEqual(values,expected)
    #----------------------------------------------------------------------
    def test_invalid_values(self):

        data =  {u'composite_ids': [u'{"testc":"3"}']}

        request = self.factory.post(self.url,data=data)
        response = self.view(request)
        values = json.loads(response.content)

        expected = {
            "errors": ['Invalid QA Values'],
            "success": False
        }
        self.assertDictEqual(values,expected)
    #----------------------------------------------------------------------
    def test_no_composite(self):

        data =  {
            u'qavalues': [
                u'{"testc":{"name":"testc","current_value":""},"test1":{"name":"test1","current_value":1},"test2":{"name":"test2","current_value":2}}'
            ],
        }

        request = self.factory.post(self.url,data=data)
        response = self.view(request)
        values = json.loads(response.content)

        expected = {
            "errors": ["No Valid Composite ID's"],
            "success": False
        }
        self.assertDictEqual(values,expected)

    #----------------------------------------------------------------------
    def test_invalid_json(self):

        data =  {
            u'qavalues': ['{"testc"'],
        }

        request = self.factory.post(self.url,data=data)
        response = self.view(request)
        values = json.loads(response.content)

        self.assertEqual(values["success"],False)
    #----------------------------------------------------------------------
    def test_invalid_test(self):

        self.tc.calculation_procedure = "foo"
        self.tc.save()

        data =  {
            u'qavalues': [
                u'{"testc":{"name":"testc","current_value":""},"test1":{"name":"test1","current_value":1},"test2":{"name":"test2","current_value":2}}'
            ],
            u'composite_ids': [u'{"testc":"3"}']
        }

        request = self.factory.post(self.url,data=data)
        response = self.view(request)
        values = json.loads(response.content)
        expected = {
            "errors": [],
            "results": {
                "testc": {
                    "value": None,
                    "error": "Invalid Test",
                }
            },
            "success": True
        }
        self.assertDictEqual(values,expected)


#============================================================================
class TestPerformQA(TestCase):

    #----------------------------------------------------------------------
    def setUp(self):
        self.factory = RequestFactory()
        self.view = views.PerformQAView.as_view()
        self.status = utils.create_status()

        self.test_list = utils.create_test_list()

        self.t_simple = utils.create_test(name="test_simple")

        self.t_const = utils.create_test(name="test_const",test_type=models.CONSTANT)
        self.t_const.constant_value = 1
        self.t_const.save()

        self.t_comp = utils.create_test(name="test_comp",test_type=models.COMPOSITE)
        self.t_comp.calculation_procedure = "result = test_simple + test_const"
        self.t_comp.save()

        self.t_mult = utils.create_test(name="test_mult",test_type=models.MULTIPLE_CHOICE)
        self.t_mult.choices = "c1,c2,c3"
        self.t_mult.save()

        self.t_bool = utils.create_test(name="test_bool",test_type=models.BOOLEAN)
        self.t_bool.save()

        self.tests = [self.t_simple, self.t_const, self.t_comp, self.t_mult, self.t_bool]

        for test in self.tests:
            utils.create_test_list_membership(self.test_list,test)

        self.unit_test_list = utils.create_unit_test_collection(
            test_collection=self.test_list
        )

        self.url = reverse("perform_qa",kwargs={"pk":self.unit_test_list.pk})
        self.client.login(username="user",password="password")

    #----------------------------------------------------------------------
    def test_test_forms_present(self):
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["formset"].forms),len(self.tests))
    #----------------------------------------------------------------------
    def test_test_initial_constant(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.context["formset"].forms[self.tests.index(self.t_const)].initial["value"],
            self.t_const.constant_value
        )
    #----------------------------------------------------------------------
    def test_readonly(self):
        response = self.client.get(self.url)
        readonly = [self.t_comp, self.t_const]

        idxs = [self.tests.index(t) for t in readonly]
        for idx in idxs:
            self.assertEqual(
                response.context["formset"].forms[idx].fields["value"].widget.attrs["readonly"],
                "readonly"
            )
    #----------------------------------------------------------------------
    def test_bool_widget(self):
        response = self.client.get(self.url)
        idx = self.tests.index(self.t_bool)
        widget = response.context["formset"].forms[idx].fields["value"].widget

        self.assertTrue( isinstance(widget,django.forms.RadioSelect))
        self.assertEqual(widget.choices,forms.BOOL_CHOICES )
    #----------------------------------------------------------------------
    def test_mult_choice_widget(self):
        response = self.client.get(self.url)
        idx = self.tests.index(self.t_mult)
        widget = response.context["formset"].forms[idx].fields["value"].widget

        self.assertTrue( isinstance(widget,django.forms.Select))
        self.assertEqual(widget.choices,[('',''),(0,'c1'),(1,'c2'),(2,'c3')])
    #---------------------------------------------------------------------------
    def test_perform(self):
        """"""
        #work_completed:11-07-2012 00:10
        #status:1
        #form-TOTAL_FORMS:5
        #form-INITIAL_FORMS:0
        #form-MAX_NUM_FORMS:
        #form-0-test:1
        #form-0-reference:8
        #form-0-tolerance:
        #form-0-value:1
        #form-0-comment:
        #form-1-test:2
        #form-1-reference:9
        #form-1-tolerance:
        #form-1-value:0
        #form-1-comment:
        #form-2-test:11
        #form-2-reference:10
        #form-2-tolerance:2
        #form-2-value:99
        #form-2-comment:
        #form-3-test:36
        #form-3-reference:
        #form-3-tolerance:
        #form-3-value:100.0
        #form-3-comment:
        #form-4-test:37
        #form-4-reference:
        #form-4-tolerance:
        #form-4-value:20
        #form-4-comment:        