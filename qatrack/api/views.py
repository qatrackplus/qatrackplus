from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse


def root_url(app, request, format=None):
    """I don't know how to properly reverse the apps api root :/"""
    root = reverse("user-list", request=request, format=format).replace("auth/users/", "")
    return root + app


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def all_api_roots(request, format=None):
    apps = ['auth', 'attachments', 'contenttypes', 'faults', 'units', 'qa', 'servicelog', 'schema']
    roots = {app: root_url(app, request, format=format) for app in apps}
    return Response(roots)
