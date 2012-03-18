from tastypie.resources import ModelResource

import models

class TaskListItemInstanceResource(ModelResource):
    class Meta:
        queryset = models.TaskListItemInstance.objects.all()
