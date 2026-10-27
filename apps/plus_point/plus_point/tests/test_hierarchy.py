"""Native agreement/category/transfer/invoice tests with complete rollback."""
import unittest,uuid
from unittest.mock import patch
import frappe
from frappe.utils import today,add_days
from plus_point.tests.test_operations import fixture,insert
from plus_point import operations as op


class HierarchyTests(unittest.TestCase):
    def test_sites_without_crew_are_saved_and_unused_removed_sites_can_be_deleted(self):
        a=self.agreement()
        saved=op.agreement(a['name']);rows=[dict(r) for r in saved['staffing']]
        op.save_agreement(dict(staffing=rows,sites=['Main venue','Side entrance']),a['name'])
        self.assertEqual({r.site_name for r in op.agreement(a['name'])['venues']},{'Main venue','Side entrance'})
        op.save_agreement(dict(staffing=rows,sites=['Main venue']),a['name'])
        self.assertEqual(len(op.agreement(a['name'])['venues']),1)

    def test_worker_activation_salary_and_fixed_payroll(self):
        from plus_point import benefits as b
        worker=frappe.get_doc('Employee',self.worker.name);worker.status='Inactive';worker.pp_salary_basis='Monthly';worker.pp_salary_amount=30000;worker.save()
        self.assertEqual(str(b.wage(worker)),'1000.00');b.activate(worker.name)
        a=self.agreement(fixed=True);doc=frappe.get_doc('PP Contract Terms',a['name']);doc.staffing[0].wage_rate=0;doc.save()
        name=self.event(a);op.auto_assign(name)
        self.assertEqual(frappe.db.get_value('PP Assignment',{'project':a['project']},'wage_rate'),1000)

    def test_worker_leave_allowance_half_day_and_attendance(self):
        from plus_point import benefits as b
        worker=frappe.get_doc('Employee',self.worker.name);worker.pp_leaves_per_month=1;worker.save()
        name=self.event();op.auto_assign(name)
        b.grant_leave(worker.name,today(),'Half day','Family appointment')
        with self.assertRaises(frappe.ValidationError):b.grant_leave(worker.name,today(),'Full day','Duplicate')
        assignment=frappe.db.get_value('PP Assignment',{'project':frappe.get_doc('PP Event Plan',name).project},'name')
        with self.assertRaises(frappe.ValidationError):insert('PP Work Entry',assignment=assignment,work_date=today(),units=1,status='Draft')
        work=insert('PP Work Entry',assignment=assignment,work_date=today(),units=.5,status='Draft');work.status='Approved';work.save()
        with self.assertRaises(frappe.ValidationError):b.grant_leave(worker.name,add_days(today(),1),'Full day','Above allowance')
        self.assertEqual(b.balances(worker.name)['leaves'][0].units,.5)

    def test_worker_loan_waiting_period_and_unpaid_draft(self):
        from plus_point import benefits as b
        worker=frappe.get_doc('Employee',self.worker.name)
        with self.assertRaises(frappe.ValidationError):b.grant_loan(worker.name,500,10,today(),'Transport')
        worker.pp_loan_allowed=1;worker.pp_loan_wait_months=2;worker.date_of_joining=today();worker.save()
        self.assertFalse(b.eligibility(worker)['eligible'])
        worker.date_of_joining='2020-01-01';worker.save()
        result=b.grant_loan(worker.name,500,10,today(),'Transport')
        self.assertFalse(result['disbursed']);self.assertEqual(b.balances(worker.name)['loan_outstanding'],'0.00')
        with self.assertRaises(frappe.ValidationError):frappe.get_doc('PP Worker Loan',result['name']).submit()

    def test_finance_hub_keeps_drafts_out_of_money_and_scopes_loan_details(self):
        from plus_point import benefits as b, finance_hub as hub
        worker=frappe.get_doc('Employee',self.worker.name);worker.pp_loan_allowed=1;worker.save()
        name=b.grant_loan(worker.name,500,10,today(),'Unpaid draft')['name']
        summary=hub.summary(self.f.company.name)
        self.assertEqual(summary['drafts'],'500.00')
        self.assertEqual(summary['advanced'],'0')
        self.assertEqual(summary['outstanding'],'0')
        row=hub.loan_states([name])[0]
        self.assertEqual(row.loan_status,'Draft · unpaid');self.assertEqual(row.outstanding,'0')
        self.assertEqual(row.worker_name,worker.employee_name)
        self.assertEqual(hub.loan_detail(name)['worker']['name'],worker.name)
        with self.assertRaises(frappe.ValidationError):hub.loan_states([name]*201)
        with self.assertRaises(frappe.PermissionError):hub.summary('Not this business')
        with patch('plus_point.finance_hub.company_scope',return_value=frappe._dict(name='Other business')):
            self.assertEqual(hub.loan_states([name]),[])
            with self.assertRaises(frappe.ValidationError):hub.loan_detail(name)

    def test_finance_navigation_keeps_reports_and_removes_setup(self):
        from plus_point.navigation import product_navigation
        nav=product_navigation(False);labels=[r['label'] for r in nav['items']]
        self.assertNotIn('Accounts',labels);self.assertNotIn('Business setup',labels)
        self.assertIn('Reports and analytics',labels);self.assertIn('Job and event finances',labels);self.assertIn('Worker statement',labels)
        self.assertNotIn('Expense claims',labels);self.assertNotIn('Wages earned',labels)
        self.assertIn('Worker loans and advances',labels);self.assertIn('Expenses',labels)
        self.assertIn('Account',nav['doctypes']);self.assertIn('Expense Claim',nav['doctypes'])
        self.assertIn('PLUS POINT Worker Statement',nav['reports'])

    def test_worker_loan_recovery_posts_native_ledger_and_prevents_double_recovery(self):
        from plus_point import benefits as b
        worker=frappe.get_doc('Employee',self.worker.name);worker.pp_loan_allowed=1;worker.save()
        a=self.agreement();name=self.event(a);op.auto_assign(name)
        assignment=frappe.db.get_value('PP Assignment',{'project':a['project'],'employee':worker.name},'name')
        work=insert('PP Work Entry',assignment=assignment,work_date=today(),units=1,status='Draft');work.status='Approved';work.save()
        company=frappe.get_doc('Company',worker.company)
        payment=insert('Payment Entry',payment_type='Pay',company=worker.company,party_type='Employee',party=worker.name,paid_from=company.default_cash_account,paid_to=company.default_receivable_account,paid_amount=500,received_amount=500,source_exchange_rate=1,target_exchange_rate=1,reference_no='Worker loan QA',reference_date=today());payment.submit()
        loan=b.grant_loan(worker.name,500,10,today(),'Transport advance',payment.name)
        self.assertTrue(loan['disbursed']);self.assertEqual(b.balances(worker.name)['proposed_deduction'],'100.00')
        from plus_point import finance_hub as hub
        self.assertEqual(hub.summary(self.f.company.name)['advanced'],'500.00')
        recovery=b.apply_deduction(loan['name'],a['project'],today())
        self.assertEqual(recovery['amount'],'100.00');self.assertEqual(b.balances(worker.name)['loan_outstanding'],'400.00')
        self.assertEqual(hub.summary(self.f.company.name)['recovered'],'100.00')
        self.assertEqual(hub.summary(self.f.company.name)['outstanding'],'400.00')
        self.assertEqual(hub.loan_states([loan['name']])[0].outstanding,'400.00')
        self.assertTrue(frappe.db.exists('GL Entry',{'voucher_no':recovery['journal'],'is_cancelled':0}))
        from plus_point.worker_profile import overview
        state=overview(worker.name);self.assertEqual(state['outstanding'],'1000.00');self.assertEqual(state['outstanding_after_loan'],'900.00')
        from plus_point.api import project_summary
        self.assertEqual(project_summary(a['project'])['wages_outstanding'],'900.00')
        from plus_point.reporting import worker_statement_report
        report=worker_statement_report(dict(company=worker.company,employee=worker.name,project=a['project']))
        self.assertEqual(str(report[1][-1]['balance']),'900.00')
        self.assertEqual(str(report[1][-1]['loan_recovery']),'100.00')
        with self.assertRaises(frappe.ValidationError):b.apply_deduction(loan['name'],a['project'],today())
        with self.assertRaises(frappe.ValidationError):payment.cancel()
        with self.assertRaises(frappe.ValidationError):frappe.get_doc('Journal Entry',recovery['journal']).cancel()
        with self.assertRaises(frappe.ValidationError):frappe.get_doc('PP Worker Loan',loan['name']).cancel()
        frappe.get_doc('PP Loan Recovery',recovery['name']).cancel()
        self.assertEqual(frappe.db.get_value('Journal Entry',recovery['journal'],'docstatus'),2)
        self.assertEqual(b.balances(worker.name)['loan_outstanding'],'500.00')
        self.assertEqual(b.apply_deduction(loan['name'],a['project'],today())['amount'],'100.00')

    def test_worker_event_assignment_requires_explicit_extra_and_preserves_agreement(self):
        from plus_point import benefits as b
        a=self.agreement();name=self.event(a)
        options=b.event_positions(self.worker.name,name);self.assertEqual(len(options['positions']),1)
        b.assign_event(self.worker.name,name,position=options['positions'][0]['name'])
        with self.assertRaises(frappe.ValidationError):b.assign_event(self.worker.name,name,position=options['positions'][0]['name'])
        other=insert('Employee',first_name='Extra Manager',gender='Male',date_of_birth='1990-01-01',date_of_joining='2020-01-01',company=self.f.company.name,status='Active',designation=self.role)
        self.assertEqual(b.event_positions(other.name,name)['positions'],[])
        with self.assertRaises(frappe.ValidationError):b.assign_event(other.name,name)
        site=options['sites'][0]['name'];b.assign_event(other.name,name,extra=True,site=site,wage_rate=900,client_rate=1400)
        self.assertEqual(frappe.get_doc('PP Contract Terms',a['name']).staffing[0].workers_required,1)
        self.assertEqual(frappe.get_doc('PP Event Plan',name).staffing[0].workers_required,2)

    def test_used_agreement_revisions_update_plan_keep_pay_history_and_conditions(self):
        a=self.agreement();name=self.event(a);op.auto_assign(name)
        allocation=frappe.get_doc('PP Assignment',{'project':a['project'],'employee':self.worker.name})
        work=insert('PP Work Entry',assignment=allocation.name,work_date=today(),units=1,status='Draft');work.status='Approved';work.save()
        doc=op.agreement(a['name']);rows=[dict(r,site_name='Main venue') for r in doc['staffing']];rows[0]['workers_required']=2;rows[0]['wage_rate']=1200
        op.save_agreement(dict(staffing=rows,pp_conditions='["Stage access by 08:00", "Client provides power"]'),a['name'])
        self.assertEqual(frappe.get_doc('PP Event Plan',name).staffing[0].workers_required,2)
        self.assertEqual(frappe.get_doc('PP Assignment',allocation.name).wage_rate,1000)
        self.assertEqual(frappe.get_doc('PP Work Entry',work.name).wage_amount,1000)
        from plus_point.signing import snapshot
        self.assertIn('Client provides power',snapshot(a['name']))
        rows.append(dict(site_name='Second stage',designation=self.role,start_date=today(),end_date=add_days(today(),4),workers_required=1,wage_rate=1000,client_rate=1500,phase='Event'))
        op.save_agreement(dict(staffing=rows,pp_future_crew_count=1),a['name'])
        op.save_agreement(dict(staffing=rows[1:]),a['name'])
        self.assertEqual(len(frappe.get_doc('PP Contract Terms',a['name']).staffing),1)
        self.assertEqual(len(frappe.get_doc('PP Event Plan',name).staffing),2)

    @classmethod
    def setUpClass(cls):
        frappe.set_user('Administrator');cls.previous=frappe.flags.get('pp_test_entitlement');frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
        frappe.db.savepoint('pp_hierarchy_suite');cls.f=fixture('Hierarchy QA '+uuid.uuid4().hex[:7])
        cls.role='Event manager QA '+uuid.uuid4().hex[:6];insert('Designation',designation_name=cls.role)
        cls.worker=insert('Employee',first_name='Ayesha Event Manager',gender='Female',date_of_birth='1990-01-01',date_of_joining='2020-01-01',company=cls.f.company.name,status='Active',designation=cls.role)
    @classmethod
    def tearDownClass(cls):
        frappe.set_user('Administrator');frappe.db.rollback(save_point='pp_hierarchy_suite');frappe.flags.pp_test_entitlement=cls.previous
    def setUp(self):
        frappe.set_user('Administrator');frappe.db.savepoint('pp_hierarchy_case');self.case_files=set(frappe.get_all('File',pluck='name'))
        self.scope=patch('plus_point.event_setup.companies',return_value=[self.f.company]);self.scope.start()
    def tearDown(self):
        frappe.set_user('Administrator')
        for name in set(frappe.get_all('File',pluck='name'))-self.case_files:frappe.delete_doc('File',name,force=1)
        self.scope.stop();frappe.db.rollback(save_point='pp_hierarchy_case')
    def agreement(self,title='Event agreement',fixed=False):
        return op.save_agreement(dict(customer=self.f.customer.name,agreement_title=title,scope='Full event agreement',billing_model='Fixed' if fixed else 'Daily',fixed_amount=10000 if fixed else 0,status='Active',effective_start=today(),effective_end=add_days(today(),4),billing_item=self.f.item.name,auto_invoice=int(fixed),staffing=[dict(site_name='Main venue',designation=self.role,phase='Event',start_date=today(),end_date=add_days(today(),4),workers_required=1,wage_rate=1000,client_rate=0 if fixed else 1500)]))
    def event(self,agreement=None):
        a=agreement or self.agreement();return op.create_plan(a['name'],'Event deployment')['name']
    def test_agreement_first_copies_client_venues_categories_rates_and_dates(self):
        a=self.agreement();name=self.event(a);doc=frappe.get_doc('PP Event Plan',name)
        self.assertEqual(doc.project,a['project']);self.assertEqual(doc.staffing[0].designation,self.role)
        self.assertEqual(doc.staffing[0].wage_rate,1000);self.assertEqual(doc.staffing[0].workers_required,1)
        self.assertEqual(op.create_plan(a['name'],'Again')['name'],name)
        self.assertEqual(frappe.db.count('PP Work Entry',{'project':doc.project}),0)
    def test_auto_assignment_matches_category_and_is_idempotent(self):
        name=self.event();result=op.auto_assign(name);self.assertEqual(result['created'],1);self.assertEqual(op.auto_assign(name)['created'],0)
        plan=op.plan(name);self.assertEqual(plan['allocations'][0]['employee'],self.worker.name)
        self.assertTrue(all(row['missing']==0 and row['extra']==0 for row in plan['coverage']))
        self.assertEqual(op.worker_states()[self.worker.name],'Assigned')
    def test_assigned_workers_remain_checked_and_reselection_is_idempotent(self):
        name=self.event();op.auto_assign(name);doc=frappe.get_doc('PP Event Plan',name)
        roster=op.available_crew(name,doc.staffing[0].name)
        person=next(r for r in roster['rows'] if r['name']==self.worker.name)
        self.assertTrue(person['assigned']);self.assertTrue(person['assignment'])
        op.assign_crew(name,doc.staffing[0].name,[self.worker.name])
        self.assertEqual(frappe.db.count('PP Assignment',{'project':doc.project}),1)
    def test_partial_phase_allocations_stay_selected_without_extending_them(self):
        name=self.event();op.auto_assign(name);doc=frappe.get_doc('PP Event Plan',name)
        assignment=frappe.get_doc('PP Assignment',{'project':doc.project,'employee':self.worker.name})
        assignment.end_date=today();assignment.save()
        person=next(r for r in op.available_crew(name,doc.staffing[0].name)['rows'] if r['name']==self.worker.name)
        self.assertTrue(person['assigned'])
        op.assign_crew(name,doc.staffing[0].name,[self.worker.name])
        self.assertEqual(str(frappe.db.get_value('PP Assignment',assignment.name,'end_date')),today())
    def test_billing_provisions_a_service_for_legacy_agreements_without_items(self):
        a=self.agreement(fixed=True)
        frappe.db.set_value('PP Contract Terms',a['name'],'billing_item',None)
        prepared=op.prepare_billing(a['name']);item=frappe.get_doc('Item',prepared['item'])
        self.assertEqual(item.is_stock_item,0);self.assertFalse(item.disabled)
        self.assertEqual(op.prepare_billing(a['name'])['item'],item.name)
        saved=op.save_milestone(a['name'],dict(milestone_title='Stage setup',due_date=today(),amount=2000,status='Approved'))
        self.assertTrue(saved['sales_invoice']);self.assertEqual(frappe.db.get_value('Sales Invoice',saved['sales_invoice'],'grand_total'),2000)
    def test_default_categories_are_event_specific_and_custom_categories_stay_available(self):
        roles=op.catalogue()['designations']
        self.assertIn('Stagehand',roles);self.assertIn('Electrician',roles)
        self.assertNotIn('Software Engineer',roles);self.assertNotIn('Accountant',roles)
        title='Festival steward QA '+uuid.uuid4().hex[:6]
        op.create_category(title);self.assertIn(title,op.catalogue()['designations'])
    def test_invoice_creation_without_internal_service_selection(self):
        a=self.agreement(fixed=True)
        frappe.db.set_value('PP Contract Terms',a['name'],'auto_invoice',0)
        op.save_milestone(a['name'],dict(milestone_title='Setup complete',due_date=today(),amount=1500,status='Approved'))
        from plus_point.billing import create_invoice
        result=create_invoice(a['name'])
        self.assertEqual(frappe.db.get_value('Sales Invoice',result['name'],'grand_total'),1500)
    def test_archived_samples_keep_receipts_and_attendance_out_of_active_views(self):
        a=self.agreement();name=self.event(a);op.auto_assign(name)
        assignment=frappe.db.get_value('PP Assignment',{'project':a['project'],'employee':self.worker.name},'name')
        work=insert('PP Work Entry',assignment=assignment,work_date=today(),units=1,status='Draft');work.status='Approved';work.save()
        project=frappe.get_doc('Project',a['project']);project.pp_archived=1;project.save()
        self.assertNotIn(a['name'],[r.name for r in op.catalogue()['agreements']])
        self.assertNotIn(name,[r.name for r in op.catalogue()['plans']])
        self.assertTrue(op.plan(name)['archived'])
        self.assertTrue(op.agreement(a['name'])['archived'])
        self.assertTrue(frappe.db.exists('PP Work Entry',work.name))
        from plus_point.worker_profile import overview
        self.assertEqual(overview(self.worker.name)['earned'],'0.00')
    def test_shortage_rolls_back_all_categories(self):
        name=self.event();doc=frappe.get_doc('PP Event Plan',name);doc.staffing[0].workers_required=2;doc.save()
        with self.assertRaises(frappe.ValidationError):op.auto_assign(name)
        self.assertEqual(frappe.db.count('PP Assignment',{'project':doc.project}),0)
    def test_manual_selection_refuses_wrong_category_and_labels_extra(self):
        name=self.event();doc=frappe.get_doc('PP Event Plan',name);row=doc.staffing[0]
        frappe.db.set_value('Employee',self.f.employee.name,'designation','Electrician')
        with self.assertRaises(frappe.ValidationError):op.assign_crew(name,row.name,[self.f.employee.name])
        other=insert('Employee',first_name='Bilal Event Manager',gender='Male',date_of_birth='1990-01-01',date_of_joining='2020-01-01',company=self.f.company.name,status='Active',designation=self.role)
        op.assign_crew(name,row.name,[self.worker.name,other.name])
        self.assertTrue(all(r['extra']==1 for r in op.coverage(doc)))
    def test_transfer_same_project_and_between_events_preserves_prior_wages(self):
        name=self.event();op.auto_assign(name);plan=frappe.get_doc('PP Event Plan',name)
        old=frappe.get_doc('PP Assignment',{'project':plan.project,'employee':self.worker.name})
        work=insert('PP Work Entry',assignment=old.name,work_date=today(),units=1,status='Draft');work.status='Approved';work.save()
        target=self.event(self.agreement('Destination event'));target_doc=frappe.get_doc('PP Event Plan',target)
        moved=op.move_worker(old.name,add_days(today(),1),target,target_doc.staffing[0].site,add_days(today(),4))
        self.assertTrue(moved['transferred']);self.assertEqual(str(frappe.db.get_value('PP Assignment',old.name,'end_date')),today())
        self.assertEqual(frappe.db.get_value('PP Work Entry',work.name,'wage_amount'),1000)
        self.assertEqual(frappe.db.get_value('PP Work Entry',work.name,'project'),plan.project)
        self.assertEqual(frappe.db.get_value('PP Assignment',moved['name'],'project'),target_doc.project)
    def test_recorded_day_cannot_be_moved(self):
        name=self.event();op.auto_assign(name);doc=frappe.get_doc('PP Event Plan',name)
        assignment=frappe.db.get_value('PP Assignment',{'project':doc.project,'employee':self.worker.name},'name')
        work=insert('PP Work Entry',assignment=assignment,work_date=today(),units=1,status='Draft')
        with self.assertRaises(frappe.ValidationError):op.move_worker(assignment,today())
        self.assertTrue(frappe.db.exists('PP Assignment',assignment))
    def test_unassign_unmarked_draft_and_photo_optional(self):
        name=self.event();op.auto_assign(name);doc=frappe.get_doc('PP Event Plan',name)
        assignment=frappe.db.get_value('PP Assignment',{'project':doc.project,'employee':self.worker.name},'name')
        op.move_worker(assignment,today());self.assertFalse(frappe.db.exists('PP Assignment',assignment))
        self.assertNotIn(self.worker.name,op.worker_states());op.set_photo(self.worker.name,None)
        with self.assertRaises(frappe.ValidationError):op.set_photo(self.worker.name,'https://example.invalid/avatar.png')
    def test_approved_milestone_creates_one_draft_no_posting(self):
        a=self.agreement(fixed=True)
        r=op.save_milestone(a['name'],dict(milestone_title='Setup complete',due_date=today(),amount=2000,status='Planned'))
        self.assertFalse(r['sales_invoice'])
        r=op.save_milestone(a['name'],dict(milestone_title='Setup complete',due_date=today(),amount=2000,status='Approved'),r['name'])
        self.assertTrue(r['sales_invoice']);invoice=frappe.get_doc('Sales Invoice',r['sales_invoice'])
        self.assertEqual(invoice.docstatus,0);self.assertEqual(invoice.grand_total,2000);self.assertEqual(len(invoice.items),1)
        doc=frappe.get_doc('PP Milestone',r['name']);doc.save()
        self.assertEqual(frappe.db.count('Sales Invoice',{'project':a['project']}),1)
        self.assertFalse(frappe.db.exists('GL Entry',{'voucher_no':invoice.name}))
        op.save_milestone(a['name'],dict(milestone_title='Pack down',due_date=add_days(today(),4),amount=1000,status='Planned'))
        self.assertEqual(frappe.db.count('PP Milestone',{'contract_terms':a['name']}),2)
    def test_extra_invoice_edit_uses_native_draft_rules(self):
        a=self.agreement();r=op.extra_invoice(a['name'],self.f.item.name,'Extra equipment setup',700)
        doc=frappe.get_doc('Sales Invoice',r['name']);op.update_invoice(doc.name,dict(remarks='Reviewed',items=[dict(name=doc.items[0].name,rate=800,description='Reviewed extra charge')]))
        self.assertEqual(frappe.db.get_value('Sales Invoice',doc.name,'grand_total'),800)
        self.assertEqual(len(op.billing(a['name'])['invoices']),1)
    def test_project_headcount_override_keeps_agreement_and_allocations(self):
        name=self.event();op.auto_assign(name);doc=frappe.get_doc('PP Event Plan',name)
        op.update_headcount(name,doc.staffing[0].name,2)
        self.assertEqual(frappe.get_doc('PP Contract Terms',doc.contract_terms).staffing[0].workers_required,1)
        rows=op.plan(name)['coverage'];self.assertTrue(all(r['planned']==2 and r['planned_extra']==1 and r['assigned']==1 and r['missing']==1 for r in rows))
        self.assertEqual(frappe.db.count('PP Assignment',{'project':doc.project}),1)
    def test_same_event_site_transfer_closes_old_allocation(self):
        a=self.agreement();name=self.event(a);op.auto_assign(name);doc=frappe.get_doc('PP Event Plan',name)
        venue=insert('PP Site',project=doc.project,site_name='Second event venue',is_active=1)
        op.add_requirement(name,dict(site=venue.name,designation=self.role,phase='Event',start_date=today(),end_date=add_days(today(),4),workers_required=1,wage_rate=800,client_rate=1200))
        old=frappe.db.get_value('PP Assignment',{'project':doc.project,'employee':self.worker.name},'name')
        moved=op.move_worker(old,add_days(today(),1),name,venue.name,add_days(today(),4))
        self.assertEqual(frappe.db.get_value('PP Assignment',moved['name'],'wage_rate'),1000)
        self.assertEqual(frappe.db.get_value('PP Assignment',moved['name'],'site'),venue.name)
    def test_email_is_explicit_and_uses_generated_pdf(self):
        a=self.agreement();r=op.extra_invoice(a['name'],self.f.item.name,'Email test charge',500)
        with patch.object(op,'email_options',return_value=dict(configured=True)),patch('frappe.sendmail') as send:
            op.email_invoice(r['name'],'client@example.invalid','Event invoice','Please review your invoice.')
            self.assertTrue(send.call_args.kwargs['attachments'][0]['fcontent'].startswith(b'%PDF'))
        self.assertFalse(frappe.db.exists('GL Entry',{'voucher_no':r['name']}))
    def test_draft_currency_change_converts_milestone_without_rewriting_earnings(self):
        a=self.agreement(fixed=True);r=op.save_milestone(a['name'],dict(milestone_title='Foreign invoice',due_date=today(),amount=2800,status='Approved'))
        op.update_invoice(r['sales_invoice'],dict(currency='USD',exchange_rate=280))
        invoice=frappe.get_doc('Sales Invoice',r['sales_invoice'])
        self.assertEqual(invoice.currency,'USD');self.assertEqual(invoice.grand_total,10)
        self.assertEqual(invoice.base_grand_total,2800)
        self.assertEqual(frappe.db.get_value('PP Milestone',r['name'],'amount'),2800)
    def test_existing_client_edits_are_saved_with_new_agreement(self):
        a=self.agreement()
        self.assertEqual(frappe.db.get_value('Project',a['project'],'customer'),self.f.customer.name)
        values=dict(customer=self.f.customer.name,agreement_title='Second client agreement',scope='Second scope',billing_model='Daily',fixed_amount=0,status='Active',effective_start=today(),effective_end=add_days(today(),4),billing_item=self.f.item.name,auto_invoice=0,
            client=dict(customer_name=self.f.customer.customer_name,customer_type='Company',contact_name='Ayesha Malik',email='client@example.invalid',country='Pakistan',city='Karachi',address_line1='12 Event Road'),
            staffing=[dict(site_name='Updated venue',designation=self.role,start_date=today(),end_date=add_days(today(),4),workers_required=1,wage_rate=1000,client_rate=1500,phase='Event')])
        op.save_agreement(values)
        from plus_point.clients import details
        self.assertEqual(details(self.f.customer.name)['email'],'client@example.invalid')
    def test_real_invoice_pdf_uses_local_assets(self):
        a=self.agreement();created=op.extra_invoice(a['name'],self.f.item.name,'Printed event charge',500)
        pdf=op.invoice_pdf_content(frappe.get_doc('Sales Invoice',created['name']))
        self.assertTrue(pdf.startswith(b'%PDF'));self.assertGreater(len(pdf),1000)
    def test_comments_keep_agreement_scope(self):
        a=self.agreement();op.add_comment('PP Contract Terms',a['name'],'Venue briefing complete')
        self.assertEqual(len(op.activity('PP Contract Terms',a['name'])['comments']),1)
        with self.assertRaises(frappe.ValidationError):op.activity('User','Administrator')
    def test_navigation_has_four_client_billing_links_and_no_separate_entities(self):
        from plus_point.navigation import product_navigation
        nav=product_navigation(False);labels=[r['label'] for r in nav['items']]
        self.assertIn('Agreements',labels);self.assertIn('Billing and invoices',labels)
        for title in ('Event projects','Event sites','Assign workers','Client invoices','Fixed milestones','Your company'):self.assertNotIn(title,labels)
    def test_guest_cannot_use_hierarchy(self):
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):op.catalogue()

    def test_new_worker_and_venue_are_created_in_the_event_workspace(self):
        from plus_point import experience
        name=self.event();doc=frappe.get_doc('PP Event Plan',name)
        worker=experience.add_worker(name,dict(first_name='Sana',last_name='Malik',gender='Female',date_of_birth='1991-01-01',date_of_joining=today(),designation=self.role))
        self.assertEqual(frappe.db.get_value('Employee',worker['name'],'company'),self.f.company.name)
        self.assertFalse(frappe.db.get_value('Employee',worker['name'],'user_id'))
        venue=experience.save_venue(name,dict(site_name='Second stage',country='Pakistan',city='Karachi',address_line1='12 Stage Road',designation=self.role,workers_required=1,wage_rate=900,client_rate=1400))
        self.assertEqual(frappe.db.get_value('PP Site',venue['site'],'project'),doc.project)
        self.assertEqual(len(frappe.get_doc('PP Event Plan',name).staffing),2)

    def test_blank_worker_category_is_visible_and_can_be_assigned_atomically(self):
        name=self.event();doc=frappe.get_doc('PP Event Plan',name)
        employee=insert('Employee',first_name='Uncategorised Crew',gender='Female',date_of_birth='1991-01-01',date_of_joining='2020-01-01',company=self.f.company.name,status='Active')
        person=next(r for r in op.available_crew(name,doc.staffing[0].name)['rows'] if r['name']==employee.name)
        self.assertTrue(person['eligible'])
        with self.assertRaises(frappe.ValidationError):op.assign_crew(name,doc.staffing[0].name,[employee.name,'missing-worker'])
        self.assertFalse(frappe.db.get_value('Employee',employee.name,'designation'))
        op.assign_crew(name,doc.staffing[0].name,[employee.name])
        self.assertEqual(frappe.db.get_value('Employee',employee.name,'designation'),self.role)

    def test_all_document_date_ranges_are_rejected_before_save(self):
        from plus_point.input_rules import validate_document
        project=frappe.get_doc('Project',self.f.project.name);project.expected_start_date=today();project.expected_end_date=add_days(today(),-1)
        with self.assertRaises(frappe.ValidationError):validate_document(project)
        doc=frappe.get_doc('PP Event Plan',self.event());doc.staffing[0].end_date=add_days(today(),-1)
        with self.assertRaises(frappe.ValidationError):validate_document(doc)

    def test_branded_invoice_preview_pdf_and_branding_are_company_scoped(self):
        from plus_point import experience
        a=self.agreement(fixed=True);saved=op.save_milestone(a['name'],dict(milestone_title='Accepted stage',due_date=today(),amount=1000,status='Approved'));name=saved['sales_invoice']
        experience.save_branding(dict(email='events@example.invalid',phone='+923001234567',address='12 Festival Road',tax_id='EVENT-123'))
        html=experience.invoice_preview(name)['html'];self.assertIn(self.f.company.name,html);self.assertIn('12 Festival Road',html);self.assertIn('Accepted stage',html)
        import base64
        self.assertTrue(base64.b64decode(experience.pdf_data(name)['content']).startswith(b'%PDF'))
        frappe.set_user('Guest')
        for call in (lambda:experience.invoice_preview(name),lambda:experience.pdf_data(name),lambda:experience.save_branding(dict(email='other@example.invalid'))):
            with self.assertRaises(frappe.PermissionError):call()

    def test_allocated_agreement_can_append_site_without_rewriting_existing_crew(self):
        a=self.agreement();name=self.event(a);op.auto_assign(name);before=op.plan(name)
        values=dict(staffing=[dict(r.as_dict(),site_name=next(v.site_name for v in op.agreement(a['name'])['venues'] if v.name==r.site)) for r in frappe.get_doc('PP Contract Terms',a['name']).staffing])
        values['staffing'].append(dict(site_name='Garden stage',designation=self.role,phase='Event',start_date=today(),end_date=add_days(today(),4),workers_required=2,wage_rate=900,client_rate=1300))
        values['pp_future_crew_count']=1
        op.save_agreement(values,a['name']);after=op.plan(name)
        self.assertEqual(len(after['staffing']),2);self.assertEqual(after['allocations'],before['allocations'])
        self.assertEqual(frappe.db.count('PP Site',{'project':a['project']}),2)

    def test_agreement_currency_converts_storage_and_new_milestones_atomically(self):
        values=dict(customer=self.f.customer.name,agreement_title='USD fixed agreement',scope='Stage setup',billing_model='Fixed',agreement_currency='USD',agreement_rate=280,fixed_amount=100,status='Active',effective_start=today(),effective_end=add_days(today(),4),auto_invoice=1,staffing=[dict(site_name='Main USD stage',designation=self.role,phase='Event',start_date=today(),end_date=add_days(today(),4),workers_required=1,wage_rate=5,client_rate=0)],milestones=[dict(milestone_title='Deposit',amount=20,status='Planned',due_date=today())])
        a=op.save_agreement(values);saved=op.agreement(a['name'])
        self.assertEqual(saved['currency'],'PKR');self.assertEqual(saved['agreement_currency'],'USD');self.assertEqual(saved['fixed_amount'],28000)
        self.assertEqual(saved['staffing'][0].wage_rate,1400);self.assertEqual(saved['milestones'][0].amount,5600)
        self.assertEqual(values['staffing'][0]['wage_rate'],5)
        saved_milestone=saved['milestones'][0];op.save_milestone(a['name'],dict(milestone_title=saved_milestone.milestone_title,amount=5600,due_date=today(),status='Approved'),saved_milestone.name)
        from plus_point.billing import create_invoice
        invoice=frappe.get_doc('Sales Invoice',frappe.db.get_value('PP Milestone',saved_milestone.name,'sales_invoice'))
        self.assertEqual(invoice.currency,'USD');self.assertEqual(invoice.grand_total,20)
        with self.assertRaises(frappe.ValidationError):op.save_agreement(dict(agreement_currency='EUR',agreement_rate=300),a['name'])
        self.assertEqual(op.agreement(a['name'])['agreement_currency'],'USD')
        self.assertEqual(frappe.db.get_value('Sales Invoice',invoice.name,'currency'),'USD')
        self.assertEqual(frappe.db.get_value('PP Contract Terms',a['name'],'fixed_amount'),28000)

    def test_agreement_prices_need_no_manual_rate_and_keep_selected_currency_units(self):
        values=dict(customer=self.f.customer.name,agreement_title='Automatic currency agreement',scope='Stage setup',billing_model='Fixed',agreement_currency='USD',fixed_amount=100,status='Active',effective_start=today(),effective_end=add_days(today(),4),auto_invoice=0,staffing=[dict(site_name='Currency stage',designation=self.role,phase='Event',start_date=today(),end_date=add_days(today(),4),workers_required=1,wage_rate=5,client_rate=0)],milestones=[dict(milestone_title='Deposit',amount=20,status='Planned',due_date=today())])
        with patch('plus_point.billing.quote',return_value=dict(rate='280')) as quote:
            a=op.save_agreement(values);quote.assert_called_once_with(self.f.company.name,'USD')
        saved=op.agreement(a['name']);self.assertEqual(saved['fixed_amount']/saved['agreement_rate'],100)
        self.assertEqual(saved['staffing'][0].wage_rate/saved['agreement_rate'],5)
        with patch('plus_point.billing.quote',side_effect=AssertionError('Existing agreements must reuse their saved rate')):
            op.save_agreement(dict(agreement_currency='USD',fixed_amount=100),a['name'])
        with patch('plus_point.billing.quote',return_value=dict(rate='300')):
            op.save_agreement(dict(agreement_currency='EUR',fixed_amount=100,staffing=values['staffing']),a['name'])
        saved=op.agreement(a['name']);self.assertEqual(saved['agreement_currency'],'EUR')
        self.assertEqual(saved['fixed_amount']/saved['agreement_rate'],100)
        self.assertEqual(saved['staffing'][0].wage_rate/saved['agreement_rate'],5)
        self.assertEqual(saved['milestones'][0].amount/saved['agreement_rate'],20)
        self.assertEqual(values['staffing'][0]['wage_rate'],5)

    def test_automatic_agreement_currency_failure_does_not_save_or_assume_one_to_one(self):
        a=self.agreement();before=op.agreement(a['name'])
        with patch('plus_point.billing.quote',side_effect=frappe.ValidationError('Unavailable')):
            with self.assertRaises(frappe.ValidationError):op.save_agreement(dict(agreement_currency='USD',fixed_amount=100),a['name'])
        after=op.agreement(a['name']);self.assertEqual(after['agreement_currency'],before['agreement_currency'])
        self.assertEqual(after['fixed_amount'],before['fixed_amount'])
        with patch('plus_point.billing.quote',side_effect=AssertionError('Same currency needs no exchange service')):
            op.save_agreement(dict(agreement_currency='PKR'),a['name'])

    def test_references_are_readable_stable_and_not_user_supplied_keys(self):
        a=self.agreement();doc=frappe.get_doc('PP Contract Terms',a['name']);self.assertRegex(doc.pp_reference,r'^AGR-20[0-9]{2}-[0-9]{5}$')
        reference=doc.pp_reference;doc.agreement_title='Named agreement';doc.save();self.assertEqual(doc.pp_reference,reference)
        doc.pp_reference='AGR-FAKE'
        with self.assertRaises(frappe.ValidationError):doc.save()
        plan=frappe.get_doc('PP Event Plan',self.event(a));self.assertTrue(plan.pp_reference.startswith('EVT-'))

    def test_optional_vehicle_quantities_persist_before_allocating_real_vehicles(self):
        a=self.agreement();row=dict(vehicle_type='Crew van',quantity=3,site_name='Main venue',start_date=today(),end_date=add_days(today(),2))
        op.save_agreement(dict(transport_requirements=[row]),a['name'])
        saved=op.agreement(a['name']);requirements=frappe.parse_json(saved['pp_transport_requirements'])
        self.assertEqual(requirements[0]['quantity'],3)
        plan=op.plan(self.event(a));self.assertEqual(frappe.parse_json(plan['agreement']['pp_transport_requirements'])[0]['vehicle_type'],'Crew van')
        self.assertFalse(frappe.db.exists('PP Vehicle Booking',{'project':a['project']}))
        from plus_point.signing import snapshot
        self.assertIn('3 × Crew van',snapshot(a['name']))
        for bad in [dict(row,quantity=-1),dict(row,quantity=1.5),dict(row,end_date=add_days(today(),20)),dict(row,site_name='Different agreement')]:
            with self.assertRaises(frappe.ValidationError):op.save_agreement(dict(transport_requirements=[bad]),a['name'])
        self.assertEqual(frappe.parse_json(op.agreement(a['name'])['pp_transport_requirements']),requirements)

    def test_country_is_inherited_and_unused_additional_hiring_is_cleared(self):
        a=self.agreement();saved=op.agreement(a['name'])
        self.assertEqual(saved['venues'][0].country,self.f.company.country)
        op.save_agreement(dict(pp_future_crew_count=50),a['name'])
        self.assertEqual(op.agreement(a['name'])['pp_future_crew_count'],0)

    def test_signing_link_expiration_revocation_and_guest_acceptance(self):
        from plus_point import signing
        a=self.agreement(fixed=True);link=signing.create_link(a['name'])
        from urllib.parse import urlparse,parse_qs
        token=parse_qs(urlparse(link['url']).query)['token'][0]
        second=signing.create_link(a['name']);second_token=parse_qs(urlparse(second['url']).query)['token'][0]
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):signing.review(token)
        html=signing.review(second_token)['html'];self.assertIn('Full event agreement',html);self.assertNotIn('Daily wage',html);self.assertNotIn('1000.00',html)
        with self.assertRaises(frappe.ValidationError):signing.accept(second_token,'Ayesha Malik','client@example.invalid',0)
        result=signing.accept(second_token,'Ayesha Malik','client@example.invalid',1)
        self.assertTrue(result['signed']);self.assertEqual(signing.review(second_token)['status'],'Signed')
        with self.assertRaises(frappe.ValidationError):signing.accept(second_token,'Ayesha Malik','client@example.invalid',1)
        frappe.set_user('Administrator');self.assertTrue(frappe.db.get_value('Contract',a['contract'] if 'contract' in a else frappe.db.get_value('PP Contract Terms',a['name'],'contract'),'is_signed'))
        self.assertTrue(frappe.db.exists('Notification Log',{'document_type':'PP Contract Terms','document_name':a['name']}))
        with self.assertRaises(frappe.ValidationError):frappe.delete_doc('PP Agreement Share',result['reference'])

    def test_changed_agreement_revokes_unsigned_link_and_expired_link_is_denied(self):
        from plus_point import signing
        from urllib.parse import urlparse,parse_qs
        a=self.agreement();link=signing.create_link(a['name']);token=parse_qs(urlparse(link['url']).query)['token'][0]
        __import__('plus_point.agreement_updates',fromlist=['propose']).propose(a['name'],dict(scope='Updated client scope'),'Scope confirmed',method='Company attested')
        with self.assertRaises(frappe.PermissionError):signing.review(token)
        link=signing.create_link(a['name']);token=parse_qs(urlparse(link['url']).query)['token'][0]
        frappe.db.set_value('PP Agreement Share',link['name'],'expires',add_days(today(),-1))
        with self.assertRaises(frappe.PermissionError):signing.review(token)

    def test_app_reporting_currency_changes_aggregate_report_only(self):
        from plus_point.workflows import display_currency
        from plus_point.reporting import project_finances
        a=self.agreement(fixed=True);op.save_milestone(a['name'],dict(milestone_title='Accepted',due_date=today(),amount=2800,status='Approved'))
        display_currency('USD')
        with patch('plus_point.billing.quote',return_value=dict(rate='280')):
            report=project_finances(dict(company=self.f.company.name));row=next(r for r in report[1] if r['project']==a['project']);self.assertEqual(row['currency'],'USD');self.assertEqual(row['earned_revenue'],'10.00')
        project=project_finances(dict(company=self.f.company.name,project=a['project']));self.assertEqual(project[1][0]['currency'],'PKR')

    def test_extra_charge_uses_explicit_agreement_invoice_currency(self):
        a=self.agreement();created=op.extra_invoice(a['name'],self.f.item.name,'Additional stage setup',10,invoice_currency='USD',exchange_rate=280)
        doc=frappe.get_doc('Sales Invoice',created['name'])
        self.assertEqual(doc.currency,'USD');self.assertEqual(doc.grand_total,10);self.assertEqual(doc.base_grand_total,2800)

    def test_crew_capacity_counts_booked_people_but_requires_explicit_future_workers(self):
        from plus_point.people import capacity
        a=self.agreement();name=self.event(a);op.auto_assign(name)
        cap=capacity(today(),add_days(today(),4),[dict(start_date=today(),end_date=add_days(today(),4),workers_required=1)])
        self.assertGreater(cap['total'],cap['available'])
        terms=frappe.get_doc('PP Contract Terms',a['name']);rows=[r.as_dict() for r in terms.staffing]
        rows.append(dict(site_name='Other stage',designation=self.role,phase='Event',start_date=today(),end_date=add_days(today(),4),workers_required=cap['total']+1,wage_rate=1000,client_rate=1500))
        with self.assertRaises(frappe.ValidationError):op.save_agreement(dict(staffing=rows),a['name'])
        self.assertEqual(len(frappe.get_doc('PP Contract Terms',a['name']).staffing),1)
        op.save_agreement(dict(staffing=rows,pp_future_crew_count=2),a['name'])
        self.assertEqual(frappe.db.get_value('PP Contract Terms',a['name'],'pp_future_crew_count'),2)

    def test_worker_department_roles_and_senior_reporting_are_validated(self):
        from plus_point.people import work_options
        options=work_options(self.worker.name);technical=next(r['value'] for r in options['departments'] if r['label']=='Technical production')
        self.assertIn('Electrician',options['roles'][technical]);self.assertNotIn('Event manager',options['roles'][technical])
        self.assertNotIn(self.worker.name,[r['value'] for r in options['managers']])
        person=frappe.get_doc('Employee',frappe.db.get_value('Employee',{'company':self.f.company.name,'name':['!=',self.worker.name]},'name'));person.reports_to=self.worker.name;person.save()
        person.department=technical;person.designation='Event manager'
        with self.assertRaises(frappe.ValidationError):person.save()
        person.department=None;person.designation=None;person.reports_to=person.name
        with self.assertRaises(frappe.ValidationError):person.save()
