from frappe.model.document import Document
from plus_point.support import validate_request, enqueue_request


class PPSupportRequest(Document):
    def validate(self):
        validate_request(self)

    def after_insert(self):
        enqueue_request(self)
