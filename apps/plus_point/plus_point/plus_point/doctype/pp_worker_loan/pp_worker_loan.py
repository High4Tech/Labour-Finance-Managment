from frappe.model.document import Document
from plus_point.benefits import validate_loan


class PPWorkerLoan(Document):
    def validate(self):
        validate_loan(self)

    def before_cancel(self):
        from plus_point.benefits import cancel_loan
        cancel_loan(self)
