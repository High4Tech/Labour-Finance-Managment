"""Native agreement/category/transfer/invoice tests with complete rollback."""
import unittest,uuid
from unittest.mock import patch
import frappe
from frappe.utils import today,add_days
from plus_point.tests.test_operations import fixture,insert
from plus_point import operations as op


class HierarchyTests(unittest.TestCase):
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
        frappe.set_user('Administrator');frappe.db.savepoint('pp_hierarchy_case')
        self.scope=patch('plus_point.event_setup.companies',return_value=[self.f.company]);self.scope.start()
    def tearDown(self):
        frappe.set_user('Administrator');self.scope.stop();frappe.db.rollback(save_point='pp_hierarchy_case')
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
    def test_shortage_rolls_back_all_categories(self):
        name=self.event();doc=frappe.get_doc('PP Event Plan',name);doc.staffing[0].workers_required=2;doc.save()
        with self.assertRaises(frappe.ValidationError):op.auto_assign(name)
        self.assertEqual(frappe.db.count('PP Assignment',{'project':doc.project}),0)
    def test_manual_selection_refuses_wrong_category_and_labels_extra(self):
        name=self.event();doc=frappe.get_doc('PP Event Plan',name);row=doc.staffing[0]
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
        self.assertEqual(frappe.db.get_value('PP Assignment',moved['name'],'wage_rate'),800)
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
        self.assertIn('Client agreements',labels);self.assertIn('Billing and finances',labels)
        for title in ('Clients','Event projects','Event sites','Assign workers','Client invoices','Fixed milestones','Your company'):self.assertNotIn(title,labels)
    def test_guest_cannot_use_hierarchy(self):
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):op.catalogue()
