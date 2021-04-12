from django.db.models import FileField
import rest_framework_filters as filters

from qatrack.attachments import models


class AttachmentFilter(filters.FilterSet):

    class Meta:
        model = models.Attachment
        fields = {
            "attachment": ['exact', 'icontains', 'contains', 'in'],
            "label": ['exact', 'icontains', 'contains', 'in'],
        }
        filter_overrides = {
            FileField: {
                 'filter_class': filters.CharFilter,
             },
        }
