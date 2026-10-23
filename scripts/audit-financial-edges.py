"""Observe exceptional correction/deletion paths in rollback-only QA fixtures."""
import json
import frappe
from frappe.utils import today
from plus_point import attendance, benefits, billing, operations, record_actions
from plus_point.api import project_summary
from plus_point.tests.test_full_workflow import FullWorkflowTests
from plus_point.tests.test_operations import insert


def main():
    frappe.init(site='qa.localhost');frappe.connect();frappe.flags.in_test=True
    if not frappe.conf.get('allow_tests'):raise RuntimeError('Local QA only')
    observations=[]
    case=FullWorkflowTests('test_resources_edits_deletion_and_availability_propagate')
    try:
        case.setUp()
        try:
            worker=case.worker(case.f.employee.name);a=case.agreement();plan=operations.create_plan(a['name'],'Paid correction edge')['name'];operations.auto_assign(plan)
            site=operations.agreement(a['name'])['venues'][0].name
            register=attendance.prepare(site,today(),a['project'])['name']
            marks=[dict(id=row['id'],status='Present') for row in attendance.detail(register)['rows']];attendance.save_marks(register,marks,approve=True)
            payment=case.payment(worker.name,200,case.f.company.default_payable_account,a['project'])
            insert('PP Wage Settlement',employee=worker.name,project=a['project'],payment_entry=payment.name).submit()
            before=project_summary(a['project'])
            correction=attendance.correct_marks(register,[dict(mark,status='Absent') for mark in marks],'Audit: attendance corrected after wages were paid')
            after=project_summary(a['project']);state=benefits.balances(worker.name)
            from plus_point.worker_profile import overview
            observations.append(dict(id='QA-02',area='Attendance correction after wage settlement',correction_accepted=True,before_outstanding=before['wages_outstanding'],after_outstanding=after['wages_outstanding'],wages_paid=after['wages_paid'],wages_earned=after['labour_cost'],monthly_outstanding=state['monthly_outstanding'],monthly_after_deduction=state['monthly_after_deduction'],profile_outstanding=overview(worker.name)['outstanding_after_loan'],payment_status=frappe.db.get_value('Payment Entry',payment.name,'docstatus'),correction=correction))
        finally:case.tearDown()
        case.setUp()
        try:
            case.worker(case.f.employee.name);a=case.agreement();plan=operations.create_plan(a['name'],'Draft invoice deletion edge')['name'];operations.auto_assign(plan)
            site=operations.agreement(a['name'])['venues'][0].name
            register=attendance.prepare(site,today(),a['project'])['name']
            marks=[dict(id=row['id'],status='Present') for row in attendance.detail(register)['rows']];attendance.save_marks(register,marks,approve=True)
            invoice=billing.create_invoice(a['name'])['name'];review=record_actions.review('Sales Invoice',invoice)
            source=frappe.db.get_value('PP Work Entry',{'project':a['project']},'name');before=project_summary(a['project'])
            record_actions.remove('Sales Invoice',invoice);after=project_summary(a['project'])
            observations.append(dict(id='QA-04',area='Draft invoice deletion preview',preview_blocked=review['blocked'],dependency=review['dependency'],actual_removal_succeeded=not bool(frappe.db.exists('Sales Invoice',invoice)),source_invoice_after_deletion=frappe.db.get_value('PP Work Entry',source,'sales_invoice'),earned_revenue_before=before['earned_revenue'],earned_revenue_after=after['earned_revenue']))
        finally:case.tearDown()
        case.setUp()
        try:
            case.worker(case.f.employee.name);a=case.agreement();plan=operations.create_plan(a['name'],'Draft deletion edge')['name'];operations.auto_assign(plan)
            site=operations.agreement(a['name'])['venues'][0].name
            register=attendance.prepare(site,today(),a['project'])['name'];record_actions.remove('PP Daily Register',register)
            first=attendance.ensure_today(case.f.company.name)
            replacement=frappe.db.get_value('PP Daily Register',{'site':site,'work_date':today(),'docstatus':0},'name')
            if replacement:record_actions.remove('PP Daily Register',replacement)
            operations.save_agreement(dict(status='Closed'),a['name']);second=attendance.ensure_today(case.f.company.name)
            observations.append(dict(id='QA-03',area='Today draft deletion regeneration',first_generation=first,old_record_deleted=not bool(frappe.db.exists('PP Daily Register',register)),replacement_created=bool(replacement),closed_agreement_generation=second,work_entries_created=frappe.db.count('PP Work Entry',{'project':a['project']})))
        finally:case.tearDown()
    finally:frappe.db.rollback();frappe.destroy()
    print('AUDIT_EDGES='+json.dumps(observations,default=str))


if __name__=='__main__':main()
