"""Bulk daily site register, implemented on native Frappe form + child table.

Submitted registers generate auditable PP Work Entries in one database transaction.
All records remain site-local because Frappe isolates each site's database.
"""
import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from plus_point.finance import day_units


class PPDailyRegister(Document):
    def before_cancel(self):
        frappe.throw("Posted registers cannot be cancelled without reversing their work entries")

    def validate(self):
        site = frappe.get_doc("PP Site", self.site)
        if not site.is_active:
            frappe.throw("Register site is inactive")
        if not self.entries:
            frappe.throw("Add at least one worker before submitting")
        self.project = site.project
        date = getdate(self.work_date)
        seen = set()
        for line in self.entries:
            if line.assignment in seen:
                frappe.throw("Duplicate assignment in the same register")
            seen.add(line.assignment)
            assignment = frappe.get_doc("PP Assignment", line.assignment)
            if assignment.site != self.site or assignment.project != self.project:
                frappe.throw("Every assignment must belong to the selected site and project")
            if date < getdate(assignment.start_date) or (
                assignment.end_date and date > getdate(assignment.end_date)
            ):
                frappe.throw("Assignment is not active on this register date")
            line.employee = assignment.employee
            try:
                day_units(line.units)
            except ValueError as error:
                frappe.throw(str(error))

    def before_submit(self):
        """Create draft then approve each work entry, preserving existing validation.

        Frappe rolls back all inserts if any row fails; never commit inside hooks.
        """
        from plus_point.budget import enforce
        enforce(self)
        # Consistent order avoids deadlocks when registers contain shared workers.
        for line in sorted(self.entries, key=lambda row: row.employee):
            if line.work_entry:
                frappe.throw("Register already contains a linked work entry")
            work = frappe.get_doc({
                "doctype": "PP Work Entry",
                "assignment": line.assignment,
                "work_date": self.work_date,
                "units": float(day_units(line.units)),
                "status": "Draft",
                "remarks": line.remarks,
            })
            work.insert()
            work.status = "Approved"
            work.save()
            line.work_entry = work.name
