class MultiSerializerMixin:

    action_serializers = {}

    def get_serializer_class(self):
        default = super(MultiSerializerMixin, self).get_serializer_class()
        return self.action_serializers.get(self.action, default)
