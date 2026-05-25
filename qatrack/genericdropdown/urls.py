from django.urls import re_path as url

from .views import updateCombo

urlpatterns = [
    url(r'^updatecombo/(?P<id>\d+)?$', updateCombo, name='updatecombo'),
]
