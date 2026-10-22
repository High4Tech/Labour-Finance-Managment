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
        from plus_point.budget import lock_project
        from plus_point.attendance import STATES,status_for
        site = frappe.get_doc("PP Site", self.site)
        site.check_permission('read')
        lock_project(site.project).check_permission('read')
        if not site.is_active:
            frappe.throw("Register site is inactive")
        if not self.entries and self.docstatus==1:
            frappe.throw("Add at least one worker before submitting")
        self.project = site.project
        date = getdate(self.work_date)
        if self.docstatus==1 and date>getdate(frappe.utils.today()):frappe.throw('Attendance cannot be approved before the work date.')
        duplicate=frappe.db.get_value('PP Daily Register',{'site':self.site,'work_date':date,'docstatus':['<',2],'name':['!=',self.name or '']},'name')
        if self.is_new() and duplicate:frappe.throw('An attendance register already exists for this site and date. Open the saved register instead.')
        seen = set()
        for line in self.entries:
            if line.assignment in seen:
                frappe.throw("Duplicate assignment in the same register")
            seen.add(line.assignment)
            assignment = frappe.get_doc("PP Assignment", line.assignment)
            assignment.check_permission('read')
            if assignment.site != self.site or assignment.project != self.project:
                frappe.throw("Every assignment must belong to the selected site and project")
            if date < getdate(assignment.start_date) or (
                assignment.end_date and date > getdate(assignment.end_date)
            ):
                frappe.throw("Assignment is not active on this register date")
            line.employee = assignment.employee
            state=line.attendance_status or status_for(line.units)
            if state not in STATES:frappe.throw('Choose Present, Absent or Half day for each worker.')
            line.attendance_status=state
            if state=='Not marked':
                line.units=''
                if self.docstatus==1:frappe.throw('Mark every worker before approving attendance. Unmarked workers are not treated as absent.')
            else:line.units=STATES[state]
            if line.work_entry:
                previous=frappe.get_doc('PP Work Entry',line.work_entry);previous.check_permission('read')
                if previous.assignment!=line.assignment or getdate(previous.work_date)!=date:
                    frappe.throw('The existing work entry must belong to this worker allocation and attendance date.')
                if previous.status=='Approved' and (state=='Not marked' or day_units(previous.units)!=day_units(line.units)):
                    frappe.throw('Approved attendance is locked. Use an audited correction to change recorded work.')
            try:
                if state!='Not marked':day_units(line.units)
            except ValueError as error:
                frappe.throw(str(error))
        if self.docstatus==1:
            from plus_point.attendance import roster,context
            context(self.site,date)
            active={row.name for row in roster(self.site,date)}
            if active-seen:frappe.throw('The crew list changed. Refresh the roster and mark every allocated worker before approval.')
            for line in self.entries:
                if line.assignment not in active and not (line.work_entry and frappe.db.get_value('PP Work Entry',line.work_entry,'status')=='Approved'):
                    frappe.throw('A listed worker is no longer active on this site/date. Review allocations and refresh the crew before approval.')

    def before_submit(self):
        """Create draft then approve each work entry, preserving existing validation.

        Frappe rolls back all inserts if any row fails; never commit inside hooks.
        """
        from plus_point.budget import enforce
        enforce(self)
        # Consistent order avoids deadlocks when registers contain shared workers.
        for line in sorted(self.entries, key=lambda row: row.employee):
            if line.work_entry:
                work=frappe.get_doc('PP Work Entry',line.work_entry)
                if work.status=='Approved':continue
                work.check_permission('write');work.units=float(day_units(line.units));work.status='Approved';work.save()
                continue
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
