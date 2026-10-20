"""Actual native records; test transaction rolls back every imported fixture."""
import base64
import csv
import io
import json
import unittest
import uuid

import frappe
from frappe.utils import today

from plus_point import imports, setup_flow
from plus_point.api import project_summary
from plus_point.tests.test_operations import fixture, insert


class SetupImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user('Administrator')
        cls.original_override=frappe.flags.get('pp_test_entitlement')
        frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
        frappe.db.savepoint('pp_import_suite')
        cls.f = fixture('PP Import QA ' + uuid.uuid4().hex[:8])

    @classmethod
    def tearDownClass(cls):
        frappe.set_user('Administrator')
        frappe.db.rollback(save_point='pp_import_suite')
        frappe.flags.pp_test_entitlement=cls.original_override

    def setUp(self):
        frappe.set_user('Administrator')
        frappe.db.savepoint('pp_import_test')
        self.tokens = []

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback(save_point='pp_import_test')
        for token in self.tokens:
            frappe.cache.delete_value('pp-import:' + token)
        frappe.cache.delete_value('defaults:Administrator')

    def preview(self, kind, rows, company=None):
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=imports.SCHEMAS[kind])
        writer.writeheader()
        writer.writerows(rows)
        result = imports.preview(kind,company or self.f.company.name,'records.csv',
            base64.b64encode(stream.getvalue().encode()).decode())
        if result['token']:
            self.tokens.append(result['token'])
        return result

    def apply(self, kind, rows):
        preview = self.preview(kind, rows)
        self.assertTrue(preview['valid'], preview)
        return imports.apply(preview['token'])

    def employee(self, **overrides):
        return dict.fromkeys(imports.EMPLOYEE_OPTIONAL_COLUMNS,'') | dict(external_id='worker-001',employee='',first_name='Imported worker',last_name='',
            gender='Male',date_of_birth='1990-01-01',date_of_joining='2020-01-01',cell_number='+923001234567',status='Active',**overrides)

    def work(self):
        return dict(external_id='work-001',assignment=self.f.assignment.name,work_date=today(),units='1')

    def invoice(self):
        return dict(external_id='invoice-001',date=today(),project=self.f.project.name,customer=self.f.customer.name,
            item_code=self.f.item.name,amount='3000',source_type='PP Work Entry',source_name='import:work-001',description='Historical client charge')

    def test_employee_preview_create_update_and_replay(self):
        row = self.employee()
        count = frappe.db.count('Employee')
        preview = self.preview('employees',[row])
        self.assertEqual(frappe.db.count('Employee'),count)
        created = imports.apply(preview['token'])
        name = created['rows'][0]['document']
        self.assertEqual(created['created'],1)
        self.assertFalse(frappe.db.get_value('Employee',name,'user_id'))
        self.assertEqual(self.apply('employees',[row])['skipped'],1)
        row['first_name'] = 'Updated worker'
        result = self.apply('employees',[row])
        self.assertEqual(result['updated'],1)
        self.assertEqual(result['rows'][0]['document'],name)
        self.assertEqual(frappe.db.get_value('Employee',name,'first_name'),'Updated worker')
        self.assertEqual(frappe.db.count('Employee'),count+1)

    def test_existing_employee_update_requires_explicit_same_company_id(self):
        row=self.employee()
        row['employee']=self.f.employee.name
        self.assertEqual(self.apply('employees',[row])['updated'],1)
        other=fixture('PP Import other '+uuid.uuid4().hex[:6])
        row['employee']=other.employee.name
        self.assertFalse(self.preview('employees',[row])['valid'])

    def test_new_worker_names_in_employee_column_create_profiles_and_replay(self):
        rows=[]
        for number in range(15):
            row=self.employee();row.update(external_id=f'EMP{number+1:03}',employee=f'Imported Person {chr(65+number)}',
                first_name='Imported',last_name=f'Person {chr(65+number)}',personal_email=f'worker{number}@example.invalid',
                current_address='12 Exhibition Road, Riyadh',person_to_be_contacted='Ayesha Malik',emergency_phone_number='+966501234567')
            rows.append(row)
        preview=self.preview('employees',rows)
        self.assertTrue(preview['valid'],preview);self.assertTrue(all(r['action']=='Create' for r in preview['rows']))
        saved=imports.apply(preview['token']);self.assertEqual(saved['created'],15)
        doc=frappe.get_doc('Employee',saved['rows'][0]['document'])
        self.assertEqual(doc.personal_email,'worker0@example.invalid');self.assertIn('Riyadh',doc.current_address)
        self.assertEqual(doc.person_to_be_contacted,'Ayesha Malik');self.assertFalse(doc.user_id)
        self.assertEqual(self.apply('employees',rows)['skipped'],15)
        rows[0]['cell_number']='+966555555555'
        updated=self.apply('employees',rows);self.assertEqual(updated['updated'],1)
        self.assertEqual(updated['rows'][0]['document'],doc.name)

    def test_unique_existing_worker_name_matches_birthdate_and_refuses_ambiguity(self):
        row=self.employee();row.update(employee=self.f.employee.employee_name,date_of_birth=str(self.f.employee.date_of_birth))
        result=self.apply('employees',[row]);self.assertEqual(result['updated'],1)
        self.assertEqual(result['rows'][0]['document'],self.f.employee.name)
        row['external_id']='other';row['employee']='Imported worker';row['date_of_birth']='1989-01-01'
        self.assertFalse(self.preview('employees',[row])['valid'])

    def test_legacy_employee_template_preserves_new_profile_columns(self):
        row=self.employee();row['personal_email']='existing@example.invalid'
        saved=self.apply('employees',[row]);name=saved['rows'][0]['document']
        legacy={key:row[key] for key in imports.LEGACY_EMPLOYEE_COLUMNS};legacy['cell_number']='+966501111111'
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=imports.LEGACY_EMPLOYEE_COLUMNS)
        writer.writeheader();writer.writerow(legacy)
        preview=imports.preview('employees',self.f.company.name,'old.csv',base64.b64encode(stream.getvalue().encode()).decode())
        self.tokens.append(preview['token']);self.assertTrue(preview['valid'],preview)
        imports.apply(preview['token']);self.assertEqual(frappe.db.get_value('Employee',name,'personal_email'),'existing@example.invalid')

    def test_duplicate_new_person_with_different_external_ids_is_refused(self):
        row=self.employee();duplicate=dict(row,external_id='different')
        self.assertFalse(self.preview('employees',[row,duplicate])['valid'])

    def test_preview_lists_duplicate_missing_and_invalid_data_rows(self):
        row=self.employee()
        duplicate=dict(row)
        bad=dict(row,external_id='worker-002',date_of_birth='not a date')
        result=self.preview('employees',[row,duplicate,bad])
        self.assertFalse(result['valid'])
        self.assertEqual([r['row'] for r in result['rows'] if r.get('error')],[3,4])
        self.assertIsNone(result['token'])

    def test_xlsx_values_and_formula_rejection(self):
        from frappe.utils.xlsxutils import make_xlsx
        row=self.employee()
        data=[imports.SCHEMAS['employees'],[row[k] for k in imports.SCHEMAS['employees']]]
        content=base64.b64encode(make_xlsx(data,'Employees').getvalue()).decode()
        result=imports.preview('employees',self.f.company.name,'employees.xlsx',content)
        self.assertTrue(result['valid'],result)
        self.tokens.append(result['token'])
        # Native export escapes formulas. Put an actual formula into this
        # disposable test workbook to exercise the import rejection instead.
        from openpyxl import load_workbook
        book=load_workbook(io.BytesIO(base64.b64decode(content)))
        book.active['C2']='=1+1'
        stream=io.BytesIO()
        book.save(stream)
        book.close()
        content=base64.b64encode(stream.getvalue()).decode()
        with self.assertRaises(frappe.ValidationError):
            imports.preview('employees',self.f.company.name,'employees.xlsx',content)

    def test_approved_work_and_worker_payment_update_real_summaries(self):
        self.apply('work',[self.work()])
        company=frappe.get_doc('Company',self.f.company.name)
        row=dict(external_id='pay-001',date=today(),project=self.f.project.name,employee=self.f.employee.name,
            amount='1000',bank_account=company.default_cash_account)
        result=self.apply('worker_payments',[row])
        settlement=frappe.get_doc('PP Wage Settlement',result['rows'][0]['document'])
        self.assertEqual(settlement.docstatus,1)
        self.assertEqual(frappe.db.get_value('Payment Entry',settlement.payment_entry,'docstatus'),1)
        self.assertTrue(frappe.db.exists('GL Entry',{'voucher_no':settlement.payment_entry,'is_cancelled':0}))
        summary=project_summary(self.f.project.name)
        self.assertEqual(summary['labour_cost'],'2000.00')
        self.assertEqual(summary['wages_paid'],'1000.00')
        self.assertEqual(self.apply('worker_payments',[row])['skipped'],1)

    def test_linked_invoice_receipt_and_duplicate_protection(self):
        self.apply('work',[self.work()])
        invoice=self.invoice()
        result=self.apply('invoices',[invoice])
        name=result['rows'][0]['document']
        self.assertEqual(frappe.db.get_value('Sales Invoice',name,'docstatus'),1)
        self.assertEqual(self.apply('invoices',[invoice])['skipped'],1)
        company=frappe.get_doc('Company',self.f.company.name)
        receipt=dict(external_id='receipt-001',date=today(),invoice='import:invoice-001',amount='1250',bank_account=company.default_cash_account)
        self.apply('receipts',[receipt])
        summary=project_summary(self.f.project.name)
        self.assertEqual(summary['cash_collected_gross'],'1250.00')
        self.assertEqual(summary['client_outstanding_gross'],'1750.00')
        self.assertEqual(summary['earned_revenue'],'3000.00')
        self.assertEqual(self.apply('receipts',[receipt])['skipped'],1)
        invoice['amount']='3001'
        self.assertFalse(self.preview('invoices',[invoice])['valid'])

    def test_project_expense_posting_and_spending_limit(self):
        supplier=insert('Supplier',supplier_name='PP import supplier '+uuid.uuid4().hex[:6],supplier_group='All Supplier Groups',supplier_type='Company')
        row=dict(external_id='expense-001',date=today(),project=self.f.project.name,supplier=supplier.name,
            item_code=self.f.item.name,amount='500',description='Actual historical net expense')
        self.apply('expenses',[row])
        self.assertEqual(project_summary(self.f.project.name)['other_project_costs'],'500.00')
        project=frappe.get_doc('Project',self.f.project.name)
        project.update(dict(estimated_costing=600,pp_enforce_spending_budget=1))
        project.save()
        row['external_id']='expense-002'
        preview=self.preview('expenses',[row])
        self.assertFalse(preview['valid'])
        self.assertTrue(preview['budgets'][0]['blocked'])
        self.assertEqual(project_summary(self.f.project.name)['other_project_costs'],'500.00')

    def test_batch_failure_rolls_back_all_work_and_receipts(self):
        # Both rows pass individual preview, but together duplicate one worker-day.
        first=self.work()
        second=dict(first,external_id='work-002')
        preview=self.preview('work',[first,second])
        self.assertTrue(preview['valid'])
        with self.assertRaises(frappe.ValidationError):
            imports.apply(preview['token'])
        self.assertEqual(frappe.db.count('PP Work Entry',{'project':self.f.project.name}),0)
        self.assertFalse(frappe.db.exists('PP Import Record',imports.record_key(self.f.company.name,'work','work-001')))

    def test_stale_budget_and_suspended_subscription_stop_atomic_apply(self):
        preview=self.preview('work',[self.work()])
        project=frappe.get_doc('Project',self.f.project.name)
        project.update(dict(estimated_costing=1000,pp_enforce_spending_budget=1))
        project.save()
        with self.assertRaises(frappe.ValidationError):
            imports.apply(preview['token'])
        self.assertEqual(frappe.db.count('PP Work Entry',{'project':self.f.project.name}),0)
        preview=self.preview('employees',[self.employee()])
        original=frappe.flags.get('pp_test_entitlement')
        try:
            frappe.flags.pp_test_entitlement={'suspended':1,'valid_until':'2099-12-31'}
            with self.assertRaises(frappe.ValidationError):
                imports.apply(preview['token'])
            self.assertFalse(frappe.db.exists('PP Import Record',imports.record_key(self.f.company.name,'employees','worker-001')))
        finally:
            frappe.flags.pp_test_entitlement=original

    def test_fixed_milestone_import_and_contract_cap(self):
        contract=insert('Contract',party_type='Customer',party_name=self.f.customer.name,
            contract_terms='Actual fixed agreement',start_date=today())
        terms=insert('PP Contract Terms',contract=contract.name,project=self.f.project.name,
            billing_model='Fixed',fixed_amount=5000,currency='PKR',status='Active',effective_start=today())
        row=dict(external_id='milestone-001',contract_terms=terms.name,title='Completed historical work',date=today(),amount='3000')
        self.apply('milestones',[row])
        self.assertEqual(project_summary(self.f.project.name)['earned_revenue'],'3000.00')
        row['external_id']='milestone-002'
        with self.assertRaises(frappe.ValidationError):
            self.apply('milestones',[row])
        self.assertEqual(project_summary(self.f.project.name)['earned_revenue'],'3000.00')

    def test_import_token_ownership_guest_and_platform_denial(self):
        user=insert('User',email=f'pp-import-{uuid.uuid4().hex[:8]}@example.invalid',first_name='Import QA',send_welcome_email=0,
                    roles=[dict(role='System Manager')])
        preview=self.preview('employees',[self.employee()])
        self.assertIsNotNone(frappe.cache.get_value('pp-import:'+preview['token']))
        frappe.set_user(user.name)
        with self.assertRaises(frappe.ValidationError):
            imports.apply(preview['token'])
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            imports.preview('employees',self.f.company.name,'file.csv','')
        frappe.set_user('Administrator')
        original=frappe.conf.get('pp_control_plane')
        try:
            frappe.conf.pp_control_plane=1
            with self.assertRaises(frappe.PermissionError):
                setup_flow.status()
            with self.assertRaises(frappe.PermissionError):
                imports.apply(preview['token'])
        finally:
            frappe.conf.pp_control_plane=original

    def test_onboarding_resume_skip_and_real_assignment(self):
        old=setup_flow.state()
        try:
            setup_flow.save_state(dict(step='company',skipped=False))
            saved=setup_flow.advance('company',dict(company=self.f.company.name))
            self.assertEqual(saved['step'],'worker')
            setup_flow.control('skip')
            self.assertTrue(setup_flow.status()['state']['skipped'])
            self.assertFalse(setup_flow.status()['auto_start'])
            self.assertEqual(setup_flow.control('resume')['step'],'worker')
            worker=setup_flow.advance('worker',dict(first_name='Wizard worker',gender='Male',date_of_birth='1990-01-01',date_of_joining=today()))
            self.assertEqual(worker['step'],'site')
            site=setup_flow.advance('site',dict(site_name='Wizard site',project=self.f.project.name))
            self.assertEqual(site['step'],'terms')
            setup_flow.advance('terms',dict(contract_terms=self.f.terms.name))
            assigned=setup_flow.advance('assignment',dict(start_date=today(),wage_rate=2000,client_rate=3000))
            self.assertEqual(assigned['step'],'import')
            self.assertEqual(frappe.db.get_value('PP Assignment',assigned['assignment'],'employee'),worker['employee'])
            self.assertEqual(frappe.db.count('PP Work Entry',{'employee':worker['employee']}),0)
            self.assertEqual(setup_flow.advance('import',{})['step'],'done')
        finally:
            setup_flow.save_state(old)

    def test_onboarding_new_job_and_billing_terms(self):
        old=setup_flow.state()
        try:
            setup_flow.save_state(dict(step='site',company=self.f.company.name,employee=self.f.employee.name))
            saved=setup_flow.advance('site',dict(site_name='New job location',project_name='Wizard new job '+uuid.uuid4().hex[:6],customer=self.f.customer.name))
            self.assertEqual(frappe.db.get_value('Project',saved['project'],'customer'),self.f.customer.name)
            saved=setup_flow.advance('terms',dict(agreement='Actual daily labour agreement',billing_model='Daily',effective_start=today()))
            self.assertEqual(frappe.db.get_value('PP Contract Terms',saved['contract_terms'],'status'),'Active')
            with self.assertRaises(frappe.ValidationError):
                setup_flow.advance('worker',{})
        finally:
            setup_flow.save_state(old)
