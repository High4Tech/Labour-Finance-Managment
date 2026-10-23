from frappe.model.document import Document
from plus_point.benefits import validate_recovery


class PPLoanRecovery(Document):
    def validate(self):
        validate_recovery(self)

    def on_cancel(self):
        from plus_point.benefits import cancel_recovery
        cancel_recovery(self)
