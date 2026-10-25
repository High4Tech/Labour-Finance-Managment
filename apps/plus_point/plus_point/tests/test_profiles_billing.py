"""Profile edits, automatic closure and recurring invoices against native records, rolled back."""
import json,unittest
from unittest.mock import patch
import frappe
from frappe.utils import today,add_days
from plus_point import operations as op,daily_billing as billing,drafts
from plus_point.agreement_lifecycle import apply_status,close_expired
from plus_point.tests import test_hierarchy as hierarchy
from plus_point.tests.test_operations import insert


class ProfileBillingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):hierarchy.HierarchyTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):hierarchy.HierarchyTests.tearDownClass.__func__(cls)
    setUp=hierarchy.HierarchyTests.setUp
    tearDown=hierarchy.HierarchyTests.tearDown
    agreement=hierarchy.HierarchyTests.agreement
    event=hierarchy.HierarchyTests.event

    def test_cadences_cover_agreement_without_gaps_or_overlap(self):
        for frequency,count in [('Weekly',5),('Biweekly',3),('Monthly',2),('Quarterly',1)]:
            rows=billing.periods('2028-01-31','2028-03-01',frequency,7,'schedule')
            self.assertEqual(len(rows),count)
            self.assertEqual(rows[0]['from_date'],'2028-01-31');self.assertEqual(rows[-1]['to_date'],'2028-03-01')
            for previous,current in zip(rows,rows[1:]):self.assertEqual(add_days(previous['to_date'],1),current['from_date'])
        monthly=billing.periods('2028-01-31','2028-04-30','Monthly')
        self.assertEqual([r['from_date'] for r in monthly],['2028-01-31','2028-02-29','2028-03-31','2028-04-30'])

    def test_schedule_limits_and_payment_terms(self):
        for args in [('2026-01-01','2026-01-02','Weekly',-1),('2026-01-01','2026-01-02','Weekly',1.5),('2026-01-01','2026-01-02','Yearly',0),('2026-01-02','2026-01-01','Weekly',0),('2026-01-01','2028-01-01','Daily',0)]:
            with self.assertRaises(frappe.ValidationError):billing.periods(*args)

    def test_status_is_derived_from_end_date_and_preserves_drafts(self):
        doc=frappe._dict(status='Active',effective_end=today());apply_status(doc);self.assertEqual(doc.status,'Active')
        doc.effective_end=add_days(today(),-1);apply_status(doc);self.assertEqual(doc.status,'Closed')
        doc.status='Draft';apply_status(doc);self.assertEqual(doc.status,'Draft')
        a=self.agreement()
        with patch('plus_point.agreement_lifecycle.today',return_value=add_days(today(),5)):close_expired()
        self.assertEqual(op.agreement(a['name'])['status'],'Closed')
        op.save_agreement({'agreement_title':'Extended agreement'},a['name'])
        self.assertEqual(op.agreement(a['name'])['status'],'Active')

    def test_popup_partial_edits_preserve_staffing_pricing_and_scope(self):
        a=self.agreement();before=op.agreement(a['name'])
        op.save_agreement(dict(agreement_title='Updated name',pp_conditions=json.dumps(['Wear safety equipment'])),a['name'])
        after=op.agreement(a['name']);self.assertEqual(after['scope'],before['scope']);self.assertEqual([{k:r[k] for k in ('site','designation','workers_required','client_rate','start_date','end_date')} for r in after['staffing']],[{k:r[k] for k in ('site','designation','workers_required','client_rate','start_date','end_date')} for r in before['staffing']])
        self.assertEqual(after['billing_model'],'Daily');self.assertEqual(json.loads(after['pp_conditions']),['Wear safety equipment'])

    def test_schedule_rebases_when_dates_change(self):
        a=self.agreement();rows=billing.periods(today(),add_days(today(),4),'Biweekly',3,'recurring')
        op.save_agreement(dict(pp_daily_checkpoints=json.dumps(rows)),a['name'])
        op.save_agreement(dict(effective_end=add_days(today(),20)),a['name'])
        saved=json.loads(op.agreement(a['name'])['pp_daily_checkpoints']);self.assertEqual(len(saved),2);self.assertEqual(saved[-1]['to_date'],add_days(today(),20))

    def test_draft_comments_move_to_created_agreement(self):
        d=drafts.save('Agreement',{'details':{'agreement_title':'Draft with comments'}},client_key='profile-comment')
        op.add_comment('PP Planning Draft',d['name'],'Check delivery access')
        self.assertEqual(len(op.activity('PP Planning Draft',d['name'])['comments']),1)
        a=self.agreement();drafts.finish(d['name'],a['name'])
        self.assertEqual(len(op.activity('PP Contract Terms',a['name'])['comments']),1)

    def test_recurring_invoices_closed_agreement_once_and_picks_up_late_approval(self):
        a=self.agreement();rows=billing.periods(today(),add_days(today(),4),'Weekly',0,'recurring')
        op.save_agreement({'pp_daily_checkpoints':json.dumps(rows)},a['name']);event=self.event(a);op.auto_assign(event)
        allocation=frappe.db.get_value('PP Assignment',{'project':a['project']},'name')
        work=insert('PP Work Entry',assignment=allocation,work_date=today(),units=1,status='Draft');work.status='Approved';work.save()
        frappe.db.set_value('PP Contract Terms',a['name'],'status','Closed')
        original=frappe.get_all
        def scoped(dt,*args,**kwargs):
            if dt=='PP Contract Terms' and kwargs.get('limit_page_length')==25:return [frappe._dict(name=a['name'],project=a['project'])]
            return original(dt,*args,**kwargs)
        with patch('plus_point.daily_billing.today',return_value=add_days(today(),5)),patch('plus_point.daily_billing.frappe.get_all',side_effect=scoped):
            billing.run_recurring();billing.run_recurring()
            self.assertEqual(frappe.db.count('Sales Invoice',{'project':a['project']}),1)
            worker=insert('Employee',first_name='Late Approval Worker',gender='Male',date_of_birth='1990-01-01',date_of_joining='2020-01-01',company=self.f.company.name,status='Active',designation=self.role)
            # Existing assignments can receive late attendance after automatic closure.
            frappe.db.set_value('PP Contract Terms',a['name'],'status','Active')
            assignment=insert('PP Assignment',employee=worker.name,site=frappe.get_doc('PP Event Plan',event).staffing[0].site,project=a['project'],contract_terms=a['name'],start_date=today(),end_date=add_days(today(),4),wage_rate=1000,client_rate=1500)
            frappe.db.set_value('PP Contract Terms',a['name'],'status','Closed')
            late=insert('PP Work Entry',assignment=assignment.name,work_date=today(),units=1,status='Draft');late.status='Approved';late.save()
            billing.run_recurring();billing.run_recurring()
        self.assertEqual(frappe.db.count('Sales Invoice',{'project':a['project']}),2)
        for invoice in frappe.get_all('Sales Invoice',filters={'project':a['project']},fields=['name','docstatus']):
            self.assertEqual(invoice.docstatus,0);self.assertFalse(frappe.db.exists('GL Entry',{'voucher_no':invoice.name}))
        saved=json.loads(op.agreement(a['name'])['pp_daily_checkpoints']);self.assertEqual(len(saved[0]['supplemental_invoices']),1)
        with self.assertRaises(frappe.ValidationError):op.save_agreement({'pp_daily_checkpoints':json.dumps([dict(saved[0],invoice='forged')])},a['name'])

    def test_event_popup_can_change_name_but_rejects_invalid_dates(self):
        event=self.event();doc=frappe.get_doc('PP Event Plan',event)
        op.save_project(event,{'event_name':'Updated event'})
        self.assertEqual(frappe.db.get_value('PP Event Plan',event,'event_name'),'Updated event')
        with self.assertRaises(frappe.ValidationError):op.save_project(event,{'end_date':add_days(doc.start_date,-1)})

    def test_completed_event_remains_editable_without_reopening_agreement(self):
        a=self.agreement();event=self.event(a)
        with patch('plus_point.agreement_lifecycle.today',return_value=add_days(today(),5)):close_expired()
        op.save_project(event,{'notes':'Final delivery reviewed'})
        self.assertEqual(frappe.db.get_value('PP Event Plan',event,'notes'),'Final delivery reviewed')
        self.assertEqual(frappe.db.get_value('PP Contract Terms',a['name'],'status'),'Closed')
