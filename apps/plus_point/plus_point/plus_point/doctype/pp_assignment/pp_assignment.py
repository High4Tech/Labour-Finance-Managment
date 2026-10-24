import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from plus_point.finance import as_decimal


class PPAssignment(Document):
    def validate(self):
        from plus_point.budget import lock_project
        lock_project(self.project)
        if self.get('pp_event_plan'):
            plan=frappe.get_doc('PP Event Plan',self.pp_event_plan)
            plan.check_permission('read')
            if plan.project!=self.project or plan.contract_terms!=self.contract_terms:
                frappe.throw('Generated crew must match its event plan project and billing terms')
            if getdate(self.start_date)<getdate(plan.start_date) or not self.end_date or getdate(self.end_date)>getdate(plan.end_date):
                frappe.throw('Generated crew dates must remain inside the event plan')
        if not self.is_new() and frappe.db.get_value('PP Assignment',self.name,'pp_event_plan')!=self.get('pp_event_plan'):
            frappe.throw('An assignment’s source event plan cannot change')
        # Work posting locks the assignment before its employee. Keep the same
        # order while closing an assignment or checking concurrent allocations.
        old = frappe.db.get_value('PP Assignment', self.name,
            ['employee', 'site', 'project', 'contract_terms', 'start_date', 'end_date', 'wage_rate', 'client_rate'],
            as_dict=True, for_update=True) if not self.is_new() else None
        frappe.db.get_value('Employee', self.employee, 'name', for_update=True)
        if old and frappe.db.exists("PP Work Entry", {"assignment": self.name}):
            for field in ("employee", "site", "project", "contract_terms", "start_date", "wage_rate", "client_rate"):
                current, previous = self.get(field), old.get(field)
                if field in ('wage_rate', 'client_rate'):
                    current, previous = as_decimal(current), as_decimal(previous)
                elif field in ('start_date', 'end_date'):
                    current = getdate(current) if current else None
                    previous = getdate(previous) if previous else None
                if current != previous:
                    frappe.throw("Used assignments are immutable; create a new dated assignment for rate or deployment changes")
            previous_end = getdate(old.end_date) if old.end_date else None
            new_end = getdate(self.end_date) if self.end_date else None
            if new_end != previous_end:
                if not new_end or (previous_end and new_end > previous_end):
                    frappe.throw('A used assignment can be closed earlier, but cannot be reopened or extended')
                if frappe.db.exists('PP Work Entry', {'assignment': self.name, 'work_date': ['>', new_end]}):
                    frappe.throw('End date cannot exclude an existing work entry, including a draft')
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
        overlaps = frappe.db.sql('''SELECT name FROM `tabPP Assignment`
            WHERE employee=%s AND site=%s AND name!=%s
              AND start_date<=%s AND (end_date IS NULL OR end_date>=%s)
            LIMIT 1''', (self.employee, self.site, self.name or '',
                                    self.end_date or '9999-12-31', self.start_date))
        if overlaps:
            frappe.throw('This worker already has an overlapping assignment at this site. Close it before adding a new dated rate or assignment.')
        from plus_point.planning import validate_assignment
        validate_assignment(self,terms)
