"""Client plan reuse, event payroll and agreement replacement; rollback only."""
import unittest
from decimal import Decimal
from unittest.mock import patch
import frappe
from frappe.utils import today,add_days
from plus_point import operations as op,planning
from plus_point.tests import test_hierarchy as hierarchy
from plus_point.tests.test_operations import insert


class PlanningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):hierarchy.HierarchyTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):hierarchy.HierarchyTests.tearDownClass.__func__(cls)
    setUp=hierarchy.HierarchyTests.setUp
    tearDown=hierarchy.HierarchyTests.tearDown
    agreement=hierarchy.HierarchyTests.agreement
    event=hierarchy.HierarchyTests.event

    def clean_agreement(self,**changes):
        a=self.agreement();terms=frappe.get_doc('PP Contract Terms',a['name'])
        rows=[r.as_dict() for r in terms.staffing]
        rows[0].update(wage_rate=0,client_rate=150)
        op.save_agreement(dict(staffing=rows,**changes),a['name'])
        return a

    def assign(self,event,basis,amount,confirm=0):
        plan=frappe.get_doc('PP Event Plan',event)
        return op.assign_crew(event,plan.staffing[0].name,[self.worker.name],
            {self.worker.name:dict(basis=basis,amount=amount)},confirm)

    def test_agreement_contains_client_price_and_event_controls_pay(self):
        a=self.clean_agreement();event=self.event(a)
        self.assertEqual(frappe.get_doc('PP Event Plan',event).wage_rate,0)
        created=self.assign(event,'Daily',100)
        assignment=frappe.get_doc('PP Assignment',created['assignments'][0])
        self.assertEqual((assignment.wage_rate,assignment.client_rate),(100,150))
        work=insert('PP Work Entry',assignment=assignment.name,work_date=today(),units=1,status='Draft');work.status='Approved';work.save()
        self.assertEqual((work.wage_amount,work.billable_amount),(100,150))

    def test_monthly_is_independent_and_loss_requires_confirmation(self):
        worker=frappe.get_doc('Employee',self.worker.name);worker.pp_daily_rate=100;worker.pp_monthly_rate=6000;worker.save()
        a=self.clean_agreement();event=self.event(a)
        with self.assertRaisesRegex(frappe.ValidationError,'exceeds the client rate'):self.assign(event,'Monthly',6000)
        self.assertFalse(frappe.db.exists('PP Assignment',{'project':a['project']}))
        created=self.assign(event,'Monthly',6000,1);assignment=frappe.get_doc('PP Assignment',created['assignments'][0])
        self.assertEqual((assignment.pp_pay_basis,assignment.pp_pay_amount,assignment.wage_rate),('Monthly',6000,200))
        work=insert('PP Work Entry',assignment=assignment.name,work_date=today(),units=.5,status='Draft');work.status='Approved';work.save()
        self.assertEqual((work.wage_amount,work.billable_amount),(100,75))
        assignment.pp_pay_basis='Daily';assignment.pp_pay_amount=200
        with self.assertRaisesRegex(frappe.ValidationError,'locks.*pay basis'):assignment.save()
        self.assertEqual(planning.worker_rates(frappe.get_doc('Employee',worker.name)),dict(daily='100.00',monthly='6000.00'))

    def test_fixed_cost_warning_counts_other_workers_and_all_dates(self):
        a=self.agreement(fixed=True);op.save_agreement(dict(fixed_amount=1200),a['name']);event=self.event(a)
        preview=planning.pay_preview(event,frappe.get_doc('PP Event Plan',event).staffing[0].name,[self.worker.name],{self.worker.name:dict(basis='Daily',amount=300)})
        self.assertIn('1500.00',preview['warning'])
        with self.assertRaisesRegex(frappe.ValidationError,'fixed client price'):self.assign(event,'Daily',300)
        self.assign(event,'Daily',300,1)
        second=insert('Employee',first_name='Another Crew Member',gender='Male',date_of_birth='1990-01-01',date_of_joining='2020-01-01',company=self.f.company.name,status='Active',designation=self.role)
        plan=frappe.get_doc('PP Event Plan',event)
        preview=planning.pay_preview(event,plan.staffing[0].name,[second.name],{second.name:dict(basis='Daily',amount=100)})
        self.assertIn('2000.00',preview['warning'])

    def test_fixed_warning_uses_agreement_currency(self):
        terms=frappe._dict(name=self.f.terms.name,billing_model='Fixed',fixed_amount=250,currency='AED',pp_agreement_currency='SAR',pp_agreement_rate=.5,effective_end=today())
        with patch('frappe.db.sql',return_value=[]):
            warning=planning.cost_warning(terms,[dict(start_date=today(),end_date=today(),wage_rate=300,client_rate=0)])
        self.assertIn('600.00 SAR',warning);self.assertIn('500.00 SAR',warning);self.assertNotIn('AED',warning)

    def test_native_assignment_and_pay_edit_cannot_bypass_confirmation(self):
        a=self.clean_agreement();event=self.event(a);created=self.assign(event,'Daily',100)
        with self.assertRaisesRegex(frappe.ValidationError,'exceeds the client rate'):planning.save_pay(created['assignments'][0],'Daily',200)
        planning.save_pay(created['assignments'][0],'Daily',200,1)
        self.assertEqual(frappe.db.get_value('PP Assignment',created['assignments'][0],'wage_rate'),200)
        assignment=frappe.get_doc('PP Assignment',created['assignments'][0]);assignment.pp_pay_amount=300
        with self.assertRaisesRegex(frappe.ValidationError,'must match'):assignment.save()

    def test_changing_default_basis_preserves_both_independent_rates(self):
        worker=frappe.get_doc('Employee',self.worker.name);worker.pp_salary_basis='Monthly';worker.pp_salary_amount=30000;worker.pp_daily_rate=100;worker.pp_monthly_rate=30000;worker.save()
        worker.pp_salary_basis='Daily';worker.save()
        self.assertEqual(planning.worker_rates(worker),dict(daily='100.00',monthly='30000.00'))
        worker.pp_daily_rate=0;worker.save()
        self.assertEqual(planning.worker_rates(worker)['daily'],'0.00')

    def test_worker_profile_assignment_accepts_custom_pay_without_salary_default(self):
        from plus_point import benefits
        a=self.clean_agreement();event=self.event(a);row=frappe.get_doc('PP Event Plan',event).staffing[0]
        result=benefits.assign_event(self.worker.name,event,position=row.name,basis='Daily',amount=120)
        self.assertEqual(result['created'],1)
        self.assertEqual(frappe.db.get_value('PP Assignment',{'project':a['project']},'wage_rate'),120)

    def test_revising_client_rates_does_not_rewrite_worker_pay(self):
        a=self.clean_agreement();event=self.event(a);created=self.assign(event,'Daily',100)
        terms=frappe.get_doc('PP Contract Terms',a['name']);rows=[r.as_dict() for r in terms.staffing];rows[0].update(client_rate=175,wage_rate=999)
        op.save_agreement(dict(staffing=rows),a['name'])
        assignment=frappe.get_doc('PP Assignment',created['assignments'][0])
        self.assertEqual((assignment.wage_rate,assignment.client_rate),(100,175))

    def test_recent_sites_are_client_scoped_and_newest_first(self):
        a=self.clean_agreement();b=self.agreement(title='Latest client agreement')
        frappe.db.set_value('PP Contract Terms',a['name'],'modified','2025-01-01 00:00:00',update_modified=False)
        rows=planning.recent_sites(self.f.customer.name)
        self.assertEqual(rows[0]['agreement'],b['name'])
        source=frappe.get_doc('PP Contract Terms',b['name']);start=add_days(today(),10);end=add_days(today(),14)
        copied=planning.copy_site(self.f.customer.name,b['name'],source.staffing[0].site,start,end,'PKR')
        self.assertEqual((copied['rows'][0]['start_date'],copied['rows'][0]['end_date']),(start,end))
        self.assertEqual(copied['rows'][0]['wage_rate'],0);self.assertNotIn('site',copied['rows'][0])
        other=insert('Customer',customer_name=self.f.company.name+' Other',customer_type='Company',customer_group='Commercial',territory='All Territories')
        self.assertEqual(planning.recent_sites(other.name),[])
        with self.assertRaises(frappe.ValidationError):planning.copy_site(other.name,b['name'],source.staffing[0].site,start,end,'PKR')
        with self.assertRaisesRegex(frappe.ValidationError,'longer'):planning.copy_site(self.f.customer.name,b['name'],source.staffing[0].site,start,start,'PKR')

    def test_unused_event_can_detach_delete_and_choose_replacement(self):
        from plus_point.record_actions import review,remove
        from plus_point.reporting import project_finances
        a=self.clean_agreement();event=self.event(a)
        planning.change_event_agreement(event)
        self.assertTrue(op.plan(event)['unlinked'])
        self.assertIn('comments',op.activity('PP Event Plan',event))
        self.assertNotIn(a['project'],[r['project'] for r in project_finances(dict(company=self.f.company.name))[1]])
        self.assertFalse(review('PP Contract Terms',a['name'])['blocked'])
        remove('PP Contract Terms',a['name'])
        replacement=self.agreement(title='Replacement')
        self.assertIn(replacement['name'],[r.name for r in planning.event_agreements(event)['rows']])
        planning.change_event_agreement(event,replacement['name'])
        linked=op.plan(event);self.assertEqual(linked['contract_terms'],replacement['name'])
        self.assertEqual(linked['project'],replacement['project'])
        self.assertIn(replacement['project'],[r['project'] for r in project_finances(dict(company=self.f.company.name))[1]])

    def test_used_event_cannot_lose_its_financial_link(self):
        a=self.clean_agreement();event=self.event(a);self.assign(event,'Daily',100)
        with self.assertRaisesRegex(frappe.ValidationError,'preserve history'):planning.change_event_agreement(event)
        doc=frappe.get_doc('PP Event Plan',event);doc.contract_terms=None
        with self.assertRaisesRegex(frappe.ValidationError,'preserve history'):doc.save()

    def test_detached_event_stays_paused_until_replaced(self):
        from plus_point import attendance,benefits,events
        a=self.clean_agreement();event=self.event(a);site=frappe.get_doc('PP Event Plan',event).staffing[0].site
        planning.change_event_agreement(event)
        self.assertNotIn(event,[r.name for r in benefits.event_options(self.worker.name)])
        attendance.ensure_today(self.f.company.name)
        self.assertFalse(frappe.db.exists('PP Daily Register',{'project':a['project']}))
        with self.assertRaisesRegex(frappe.ValidationError,'replacement agreement'):attendance.prepare(site,today())
        with self.assertRaisesRegex(frappe.ValidationError,'replacement agreement'):
            events.context(frappe._dict(project=a['project'],site=site,start_date=today(),end_date=add_days(today(),1)))

    def test_draft_agreement_can_be_saved_before_crew_is_added(self):
        created=op.save_agreement(dict(customer=self.f.customer.name,agreement_title='Draft planning',scope='',billing_model='Fixed',fixed_amount=0,status='Draft',effective_start=today(),effective_end=add_days(today(),4),staffing=[]))
        self.assertEqual(frappe.get_doc('PP Contract Terms',created['name']).status,'Draft')
        self.assertFalse(frappe.db.exists('PP Event Plan',{'project':created['project']}))

    def test_agreement_and_employee_import_templates_match_current_model(self):
        from plus_point import imports,event_imports
        from plus_point.import_links import normalize
        import csv,io,base64
        self.assertNotIn('wage_rate',imports.SCHEMAS['events'])
        self.assertNotIn('default_currency',imports.SCHEMAS['clients']);self.assertNotIn('client_default_currency',imports.SCHEMAS['events'])
        self.assertIn('pp_daily_rate',imports.SCHEMAS['employees']);self.assertIn('pp_monthly_rate',imports.SCHEMAS['employees'])
        row=dict(external_id='agreement-test',agreement_title='Imported client agreement',customer=self.f.customer.name,start_date=today(),end_date=add_days(today(),4),status='Active',billing_model='Daily',agreement_currency='PKR',fixed_amount='',scope='Imported scope',conditions='First | Second',site_name='Imported site',designation=self.role,workers_per_day='1',client_rate='150')
        out=io.StringIO();writer=csv.writer(out);writer.writerow(imports.SCHEMAS['agreements']);writer.writerow([row[k] for k in imports.SCHEMAS['agreements']])
        preview=imports.preview('agreements',self.f.company.name,'agreements.csv',base64.b64encode(out.getvalue().encode()).decode())
        self.assertTrue(preview['valid'],preview['rows'])
        result=imports.apply(preview['token']);self.assertTrue(result)
        doc=frappe.get_doc('PP Contract Terms',{'agreement_title':row['agreement_title']})
        self.assertEqual((doc.staffing[0].wage_rate,doc.staffing[0].client_rate),(0,150))
        self.assertEqual(frappe.parse_json(doc.pp_conditions),['First','Second'])

    def test_warehouse_and_count_templates_use_ownership_and_automatic_values(self):
        from plus_point import imports,event_imports
        from plus_point.import_links import normalize
        warehouse=frappe.db.get_value('Warehouse',{'company':self.f.company.name,'is_group':0},'name')
        item=insert('Item',item_code=self.f.company.name+' Stock',item_name='QA Stage equipment',item_group='Products',stock_uom='Nos',is_stock_item=1)
        row,notes=normalize('stock_balances',self.f.company.name,dict(external_id='stock-test',item_code=item.name,warehouse=warehouse,quantity='2'))
        self.assertEqual(row['date'],today());self.assertTrue(row['_automatic_count']);self.assertEqual(row['valuation_rate'],'0')
        event_imports.validate('stock_balances',self.f.company.name,row)
        self.assertNotIn('valuation_rate',imports.SCHEMAS['stock_balances']);self.assertNotIn('date',imports.SCHEMAS['stock_balances'])
        row,_=normalize('warehouses',self.f.company.name,dict(external_id='warehouse-test',warehouse_name='Rented stage equipment',warehouse_type='rented',status='active'))
        doc=event_imports.save('warehouses',self.f.company.name,row)
        self.assertEqual((doc.warehouse_type,doc.disabled),('Rented',0))

    def test_employee_template_imports_two_rates_and_benefits(self):
        from plus_point import imports
        from plus_point.import_links import normalize
        row=dict(external_id='worker-pay-template',employee='',first_name='Imported Worker',last_name='Crew',gender='Male',date_of_birth='1990-01-01',date_of_joining='2020-01-01',status='Active',pp_salary_basis='monthly',pp_daily_rate='150',pp_monthly_rate='3000',pp_leaves_per_month='2',pp_loan_allowed='1',pp_loan_wait_months='3',pp_loan_deduction_percent='10')
        row,_=normalize('employees',self.f.company.name,row)
        imports.validate_row('employees',self.f.company.name,row)
        self.assertEqual(row['pp_salary_basis'],'Monthly')
        row['pp_daily_rate']='-1'
        with self.assertRaises(frappe.ValidationError):imports.validate_row('employees',self.f.company.name,row)
