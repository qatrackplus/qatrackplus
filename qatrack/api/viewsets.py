from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.pagination import LimitOffsetPagination


def limit_offset_pagination_factory(page_size=10):
    """Factory function for creating LimitOffsetPagination classes with custom page sizes"""

    class CustomPageSizePagination(LimitOffsetPagination):
        default_limit = page_size

    return CustomPageSizePagination


class CreateListRetrieveViewSet(mixins.CreateModelMixin,
                                mixins.ListModelMixin,
                                mixins.RetrieveModelMixin,
                                viewsets.GenericViewSet):
    """
    A viewset that provides `retrieve`, `create`, and `list` actions.

    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.
    """
    pass
