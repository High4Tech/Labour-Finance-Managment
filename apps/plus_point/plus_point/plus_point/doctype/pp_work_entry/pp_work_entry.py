from decimal import Decimal

import frappe
from frappe.model.document import Document
from frappe.utils import getdate

from plus_point.finance import daily_amounts, day_units, as_decimal


class PPWorkEntry(Document):
    def on_trash(self):
        if self.status == "Approved":
            frappe.throw("Approved work entries cannot be deleted; use an audited adjustment")

    def before_insert(self):
        if self.status != "Draft":
            frappe.throw("Work entries must be created as Draft and reviewed before approval")
        self._copy_assignment_snapshot()

    def _copy_assignment_snapshot(self):
        assignment = frappe.get_doc("PP Assignment", self.assignment, for_update=True)
        self.employee = assignment.employee
        self.site = assignment.site
        self.project = assignment.project
        self.contract_terms = assignment.contract_terms
        self.wage_rate = assignment.wage_rate
        terms = frappe.get_doc("PP Contract Terms", assignment.contract_terms)
        self.client_rate = assignment.client_rate if terms.billing_model == "Daily" else 0

    def validate(self):
        # Serialize all postings for an employee, including postings on different sites.
        # A query-only duplicate check races under concurrent HTTP submissions.
        frappe.db.get_value("Employee", self.employee, "name", for_update=True)
        old = self.get_doc_before_save()
        if old and old.status == "Approved":
            frappe.throw("Approved work entries are immutable; post an audited correction instead")
        if self.status not in {"Draft", "Approved"}:
            frappe.throw("Invalid work entry status")
        if self.status == "Approved" and "System Manager" not in frappe.get_roles():
            frappe.throw("Only System Manager can approve work entries", frappe.PermissionError)
        if old and old.assignment != self.assignment:
            frappe.throw("Assignment cannot change after a work entry is created")
        if not old:
            # The before_insert hook created the immutable rate snapshot.
            assignment = frappe.get_doc("PP Assignment", self.assignment)
        else:
            assignment = frappe.get_doc("PP Assignment", old.assignment)
            for name in ("employee", "site", "project", "contract_terms", "wage_rate", "client_rate"):
                current, previous = self.get(name), old.get(name)
                if name in ("wage_rate", "client_rate"):
                    current, previous = as_decimal(current), as_decimal(previous)
                if current != previous:
                    frappe.throw(f"{name} is a locked historical snapshot")
        day = getdate(self.work_date)
        if day < getdate(assignment.start_date) or (assignment.end_date and day > getdate(assignment.end_date)):
            frappe.throw("Work date must be within the worker assignment period")
        terms = frappe.get_doc("PP Contract Terms", self.contract_terms, for_update=True)
        if terms.status != "Active" or not frappe.db.get_value("PP Site", self.site, "is_active"):
            frappe.throw("Work requires active contract terms and an active site")
        if day < getdate(terms.effective_start) or (terms.effective_end and day > getdate(terms.effective_end)):
            frappe.throw("Work date is outside contract term dates")
        if terms.billing_model == "Fixed" and Decimal(str(self.client_rate or 0)) != 0:
            frappe.throw("Fixed contracts cannot bill individual worker-days")
        units = day_units(self.units)
        existing = frappe.db.sql('''SELECT site, units FROM `tabPP Work Entry`
            WHERE employee=%s AND work_date=%s AND name!=%s FOR UPDATE''',
            (self.employee, self.work_date, self.name or ''), as_dict=True)
        if any(e.site == self.site for e in existing):
            frappe.throw("This worker already has a daily register entry for this site and date")
        if sum((day_units(e.units) for e in existing), Decimal(0)) + units > Decimal("1"):
            frappe.throw("Worker cannot have more than one total working day across sites")
        self.wage_amount, self.billable_amount = map(float, daily_amounts(self.wage_rate, self.client_rate, units))
