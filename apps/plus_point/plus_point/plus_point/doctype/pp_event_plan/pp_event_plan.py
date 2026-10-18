from frappe.model.document import Document
from plus_point.events import validate_plan


class PPEventPlan(Document):
    def validate(self):
        validate_plan(self)
