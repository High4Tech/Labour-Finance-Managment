from decimal import Decimal

import frappe
from frappe.model.document import Document
from plus_point.finance import money


class PPMilestone(Document):
    def on_trash(self):
        if self.status in {"Approved", "Invoiced"}:
            frappe.throw("Approved or invoiced milestones cannot be deleted")

    def validate(self):
        frappe.db.get_value("PP Contract Terms", self.contract_terms, "name", for_update=True)
        terms = frappe.get_doc("PP Contract Terms", self.contract_terms)
        if terms.billing_model != "Fixed":
            frappe.throw("Milestones are only available for fixed-price contracts")
        amount = money(self.amount)
        if amount <= 0:
            frappe.throw("Milestone amount must be positive")
        old = self.get_doc_before_save()
        if self.sales_invoice != (old.sales_invoice if old else None):
            frappe.throw("Invoice references are managed by the PLUS POINT billing action")
        if self.status == "Invoiced" and (not old or old.status != "Invoiced"):
            frappe.throw("Submit the linked ERPNext invoice to mark a milestone Invoiced")
        if old and old.status in {"Approved", "Invoiced"}:
            if old.amount != self.amount or old.contract_terms != self.contract_terms:
                frappe.throw("Approved milestone value and contract reference are immutable")
            if old.status == "Invoiced" and self.status != "Invoiced":
                frappe.throw("Invoiced milestones cannot be reverted")
            if old.status == "Approved" and self.status == "Planned":
                frappe.throw("Approved milestones cannot be reverted without an adjustment")
        if self.status in {"Approved", "Invoiced"} and "System Manager" not in frappe.get_roles():
            frappe.throw("Only System Manager can approve milestones", frappe.PermissionError)
        if self.status == "Invoiced" and not self.sales_invoice:
            frappe.throw("Link the actual ERPNext Sales Invoice before setting Invoiced")
        if self.sales_invoice:
            invoice = frappe.get_doc("Sales Invoice", self.sales_invoice)
            project = frappe.get_doc("Project", terms.project)
            if invoice.customer != project.customer:
                frappe.throw("Linked invoice must belong to project customer")
            if invoice.project != terms.project or invoice.company != project.company or invoice.docstatus not in (0,1):
                frappe.throw("Milestone invoice must match the project and company")
            if self.status=='Invoiced' and invoice.docstatus!=1:
                frappe.throw('Submit the invoice before marking the milestone Invoiced')
            if invoice.docstatus==0 and not any(row.get('pp_source_type')=='PP Milestone' and row.get('pp_source_name')==self.name for row in invoice.items):
                frappe.throw('A reserved draft invoice must include this milestone as its source')
            if invoice.currency!=terms.currency and not any(row.get('pp_source_type')=='PP Milestone' and row.get('pp_source_name')==self.name for row in invoice.items):
                frappe.throw('A foreign-currency milestone invoice must link this approved milestone as its source.')
        from plus_point.agreement_events import validate_milestone_group
        validate_milestone_group(self,terms)
        if self.status in {"Approved", "Invoiced"}:
            others = frappe.db.sql('''SELECT amount FROM `tabPP Milestone`
                WHERE contract_terms=%s AND status IN ('Approved', 'Invoiced')
                AND name!=%s FOR UPDATE''', (self.contract_terms, self.name or ''), as_dict=True)
            total = sum((money(m.amount) for m in others), Decimal(0)) + amount
            if total > money(terms.fixed_amount):
                frappe.throw("Approved milestones exceed the agreed fixed contract value")
