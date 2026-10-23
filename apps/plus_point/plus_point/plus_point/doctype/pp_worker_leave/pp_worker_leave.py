from frappe.model.document import Document
from plus_point.benefits import validate_leave


class PPWorkerLeave(Document):
    def validate(self):
        validate_leave(self)
