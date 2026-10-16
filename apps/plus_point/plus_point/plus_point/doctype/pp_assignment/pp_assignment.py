import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from plus_point.finance import as_decimal


class PPAssignment(Document):
    def validate(self):
        old = self.get_doc_before_save()
        if old and frappe.db.exists("PP Work Entry", {"assignment": self.name}):
            for field in ("employee", "site", "project", "contract_terms", "start_date", "end_date", "wage_rate", "client_rate"):
                current, previous = self.get(field), old.get(field)
                if field in ('wage_rate', 'client_rate'):
                    current, previous = as_decimal(current), as_decimal(previous)
                elif field in ('start_date', 'end_date'):
                    current = getdate(current) if current else None
                    previous = getdate(previous) if previous else None
                if current != previous:
                    frappe.throw("Used assignments are immutable; create a new dated assignment for rate or deployment changes")
        site = frappe.get_doc("PP Site", self.site)
        terms = frappe.get_doc("PP Contract Terms", self.contract_terms)
        employee = frappe.get_doc("Employee", self.employee)
        project = frappe.get_doc("Project", self.project)
        if employee.status != "Active" or employee.company != project.company:
            frappe.throw("Worker must be active and belong to the project company")
        if not site.is_active:
            frappe.throw("Cannot assign to an inactive site")
        if site.project != self.project or terms.project != self.project:
            frappe.throw("Site and contract terms must belong to the assignment project")
        if terms.status != "Active":
            frappe.throw("Billing terms must be Active before assigning workers")
        if self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw("Assignment end date cannot precede start date")
        if as_decimal(self.wage_rate or 0) <= 0:
            frappe.throw("Daily worker wage must be positive")
        if as_decimal(self.client_rate or 0) < 0:
            frappe.throw("Client rate cannot be negative")
        if terms.billing_model == "Daily" and as_decimal(self.client_rate or 0) <= 0:
            frappe.throw("Daily-billing assignments require a client rate")
        if terms.billing_model == "Fixed" and as_decimal(self.client_rate or 0) != 0:
            frappe.throw("Fixed contracts must use zero worker-day client rates")
