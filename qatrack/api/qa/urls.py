from django.conf.urls import include, url
from rest_framework import routers

from qatrack.api.qa import views

router = routers.DefaultRouter()

router.register(r'frequencies', views.FrequencyViewSet)
router.register(r'testinstancestatus', views.TestInstanceStatusViewSet)
router.register(r'autoreviewrules', views.AutoReviewRuleViewSet)
router.register(r'autoreviewrulesets', views.AutoReviewRuleSetViewSet)
router.register(r'references', views.ReferenceViewSet)
router.register(r'tolerances', views.ToleranceViewSet)
router.register(r'categories', views.CategoryViewSet)
router.register(r'tests', views.TestViewSet)
router.register(r'unittestinfos', views.UnitTestInfoViewSet)
router.register(r'testlists', views.TestListViewSet)
router.register(r'testlistmemberships', views.TestListMembershipViewSet)
router.register(r'sublists', views.SublistViewSet)
router.register(r'unittestcollections', views.UnitTestCollectionViewSet)
router.register(r'testinstances', views.TestInstanceViewSet)
router.register(r'testlistinstances', views.TestListInstanceViewSet)
router.register(r'testlistcycles', views.TestListCycleViewSet)
router.register(r'testlistcyclememberships', views.TestListCycleMembershipViewSet)

urlpatterns = [
    # view for composite calculations via api
    url(r"^composite/$", views.CompositeCalculation.as_view(), name="api.composite"),

    # view for uploads via api
    url(r"^upload/$", views.Upload.as_view(), name="api.upload"),

    url(r'^', include(router.urls)),
]
