"""Component boundary and exceptional-path regressions; all changes roll back."""
import unittest
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs
import frappe
from frappe.utils import today,add_days
from plus_point import attendance,benefits,billing,experience,operations,record_actions,signing
from plus_point.api import project_summary
from plus_point.tests import test_full_workflow as journey
from plus_point.tests.test_operations import insert


class ComponentValidationTests(unittest.TestCase):
    def setUp(self):
        self.case=journey.FullWorkflowTests('test_resources_edits_deletion_and_availability_propagate');self.case.setUp();self.f=self.case.f

    def tearDown(self):self.case.tearDown()

    def approved(self):
        self.worker=self.case.worker(self.f.employee.name);self.a=self.case.agreement();self.plan=operations.create_plan(self.a['name'],'Validation audit')['name'];operations.auto_assign(self.plan)
        self.site=operations.agreement(self.a['name'])['venues'][0].name
        self.register=attendance.prepare(self.site,today(),self.a['project'])['name']
        self.marks=[dict(id=r['id'],status='Present') for r in attendance.detail(self.register)['rows']]
        attendance.save_marks(self.register,self.marks,approve=True)

    def test_paid_attendance_cannot_reduce_below_settled_wages(self):
        self.approved();payment=self.case.payment(self.worker.name,200,self.f.company.default_payable_account,self.a['project'])
        settlement=insert('PP Wage Settlement',employee=self.worker.name,project=self.a['project'],payment_entry=payment.name);settlement.submit()
        for status in ['Absent','Half day']:
            with self.subTest(status=status),self.assertRaisesRegex(frappe.ValidationError,'already paid or recovered'):
                attendance.correct_marks(self.register,[dict(m,status=status) for m in self.marks],'Correct paid attendance')
            self.assertEqual(project_summary(self.a['project'])['wages_outstanding'],'0.00')
            self.assertEqual(attendance.detail(self.register)['rows'][0]['status'],'Present')
        settlement.cancel();payment.cancel()
        attendance.correct_marks(self.register,[dict(m,status='Absent') for m in self.marks],'Correct after actual reversal')
        self.assertEqual(project_summary(self.a['project'])['wages_outstanding'],'0.00')

    def test_recovered_loan_also_protects_earned_wages(self):
        self.approved();worker=frappe.get_doc('Employee',self.worker.name);worker.pp_loan_allowed=1;worker.pp_loan_wait_months=0;worker.save()
        payment=self.case.payment(worker.name,500,self.f.company.default_receivable_account)
        loan=benefits.grant_loan(worker.name,500,25,today(),'Validation audit',payment.name)
        benefits.apply_deduction(loan['name'],self.a['project'],today())
        with self.assertRaisesRegex(frappe.ValidationError,'already paid or recovered'):
            attendance.correct_marks(self.register,[dict(m,status='Absent') for m in self.marks],'Correction after loan recovery')
        self.assertEqual(project_summary(self.a['project'])['labour_cost'],'200.00')

    def test_draft_invoice_preview_and_deletion_agree(self):
        self.approved();invoice=billing.create_invoice(self.a['name'])['name']
        self.assertFalse(record_actions.review('Sales Invoice',invoice)['blocked'])
        record_actions.remove('Sales Invoice',invoice)
        self.assertFalse(frappe.db.exists('Sales Invoice',invoice));self.assertEqual(project_summary(self.a['project'])['earned_revenue'],'350.00')
        self.assertFalse(frappe.db.get_value('PP Work Entry',{'project':self.a['project']},'sales_invoice'))

    def test_unsigned_signing_links_clean_up_but_signed_evidence_stays(self):
        self.case.worker(self.f.employee.name);a=self.case.agreement();first=signing.create_link(a['name']);second=signing.create_link(a['name'])
        self.assertEqual(frappe.db.get_value('PP Agreement Share',first['name'],'status'),'Revoked')
        self.assertFalse(record_actions.review('PP Contract Terms',a['name'])['blocked'])
        record_actions.remove('PP Contract Terms',a['name'])
        for link in [first,second]:self.assertFalse(frappe.db.exists('PP Agreement Share',link['name']))
        a=self.case.agreement(title='Signed lifecycle');link=signing.create_link(a['name']);token=parse_qs(urlparse(link['url']).query)['token'][0]
        signing.accept(token,'QA Client','qa@example.invalid',1)
        self.assertTrue(record_actions.review('PP Contract Terms',a['name'])['blocked'])
        with self.assertRaises(frappe.ValidationError):record_actions.remove('PP Contract Terms',a['name'])
        self.assertEqual(frappe.db.get_value('PP Agreement Share',link['name'],'status'),'Signed')

    def test_closed_agreement_stops_new_attendance_and_preserves_history(self):
        self.approved()
        from plus_point.agreement_lifecycle import close_expired
        end=frappe.db.get_value('PP Contract Terms',self.a['name'],'effective_end')
        with patch('plus_point.agreement_lifecycle.today',return_value=add_days(end,1)):close_expired()
        self.assertEqual(attendance.ensure_today(self.f.company.name)['created'],0)
        self.assertEqual(attendance.detail(self.register)['rows'][0]['status'],'Present')
        with self.assertRaisesRegex(frappe.ValidationError,'closed or has no active agreement'):
            attendance.prepare(self.site,add_days(today(),-1),self.a['project'])

    def test_new_past_work_requires_explicit_historical_mode(self):
        self.case.worker(self.f.employee.name)
        values=dict(customer=self.f.customer.name,agreement_title='Past mode audit',scope='Historical work',billing_model='Daily',agreement_currency='PKR',effective_start=add_days(today(),-2),effective_end=today(),status='Active',staffing=[dict(site_name='Historical hall',designation='Event crew',phase='Event',start_date=add_days(today(),-2),end_date=today(),workers_required=1,wage_rate=200,client_rate=350)])
        before=frappe.db.count('Project',{'company':self.f.company.name})
        with self.assertRaisesRegex(frappe.ValidationError,'Allow dates in the past'):operations.save_agreement(values)
        self.assertEqual(frappe.db.count('Project',{'company':self.f.company.name}),before)
        a=operations.save_agreement(dict(values,allow_past_dates=1));self.assertTrue(a['name'])

    def test_reverse_dates_rejected_without_partial_mutation(self):
        self.case.worker(self.f.employee.name);a=self.case.agreement()
        with self.assertRaises(frappe.ValidationError):operations.save_agreement(dict(effective_end=add_days(today(),-5)),a['name'])
        self.assertEqual(str(frappe.db.get_value('PP Contract Terms',a['name'],'effective_end')),today())

    def test_server_rejects_invalid_phone_and_email(self):
        for values in [dict(cell_number='call me'),dict(cell_number='12'),dict(cell_number='+1234567890123456'),dict(personal_email='not-an-email')]:
            with self.subTest(values=values),self.assertRaises(frappe.ValidationError):experience.update_worker_contact(self.f.employee.name,values)
        experience.update_worker_contact(self.f.employee.name,dict(cell_number='+966 (50) 123-4567',personal_email='worker@example.invalid'))

    def test_salary_leave_and_percent_boundaries(self):
        for field,value in [('pp_salary_amount',-1),('pp_leaves_per_month',32),('pp_loan_wait_months',-1),('pp_loan_deduction_percent',101)]:
            worker=frappe.get_doc('Employee',self.f.employee.name);worker.set(field,value)
            with self.subTest(field=field),self.assertRaises(frappe.ValidationError):worker.save()

    def test_future_birth_date_rejected(self):
        worker=frappe.get_doc('Employee',self.f.employee.name);worker.date_of_birth=add_days(today(),1)
        with self.assertRaisesRegex(frappe.ValidationError,'Date of birth cannot be in the future'):worker.save()

    def test_worker_numeric_fields_reject_text_and_nonfinite_values(self):
        for field,value in [('pp_salary_amount','letters'),('pp_salary_amount','NaN'),('pp_loan_wait_months','1.5')]:
            worker=frappe.get_doc('Employee',self.f.employee.name);worker.set(field,value)
            with self.subTest(field=field,value=value),self.assertRaisesRegex(frappe.ValidationError,'finite'):
                worker.save()
