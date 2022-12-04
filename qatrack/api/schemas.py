from rest_framework.schemas.openapi import AutoSchema


class QATrackAutoSchema(AutoSchema):

    def get_operation_id(self, path, method):
        op_id = super().get_operation_id(path, method)
        if "/qc/" in path:
            op_id += "_qc"
        return op_id
