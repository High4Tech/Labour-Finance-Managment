import frappe
from frappe.model.document import Document


class PPImportRecord(Document):
    def autoname(self):
        from plus_point.imports import record_key
        self.name = record_key(self.company, self.kind, self.external_id)

    def validate(self):
        if not frappe.flags.pp_import_record:
            frappe.throw('Import receipts are managed by the reviewed import flow', frappe.PermissionError)

    def on_trash(self):
        frappe.throw('Keep import receipts to prevent duplicate financial postings', frappe.PermissionError)
