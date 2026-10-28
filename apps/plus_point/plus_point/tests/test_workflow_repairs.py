"""Empty drafts, site reuse, occupied slots and focused event removal; rollback only."""
import unittest
from unittest.mock import patch
import frappe
from frappe.utils import today,add_days
from plus_point import drafts,planning,operations as op,record_actions as actions
from plus_point.tests import test_hierarchy as hierarchy
from plus_point.tests.test_operations import insert


class WorkflowRepairsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):hierarchy.HierarchyTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):hierarchy.HierarchyTests.tearDownClass.__func__(cls)
    setUp=hierarchy.HierarchyTests.setUp
    tearDown=hierarchy.HierarchyTests.tearDown
    agreement=hierarchy.HierarchyTests.agreement
    event=hierarchy.HierarchyTests.event

    def test_empty_and_default_only_agreements_do_not_create_drafts(self):
        before=frappe.db.count(drafts.DT)
        for payload in [{},dict(details=dict(effective_start=today(),effective_end=today(),scope='<p><br></p>'),client=dict(country='Pakistan',customer_type='Company'),terms=dict(billing_model='Daily',agreement_currency='PKR'),staffing=[],sites=[])]:
            self.assertTrue(drafts.save('Agreement',payload,client_key='empty')['skipped'])
        self.assertEqual(before,frappe.db.count(drafts.DT))
        saved=drafts.save('Agreement',dict(details=dict(agreement_title='First actual detail')),client_key='empty')
        self.assertTrue(saved['name'])
        # Clearing a previously saved draft must not silently delete it.
        self.assertEqual(drafts.save('Agreement',{},name=saved['name'],revision=saved['revision'])['name'],saved['name'])

    def test_partial_new_client_contact_is_a_meaningful_draft(self):
        saved=drafts.save('Agreement',dict(client_mode='Add new client',client=dict(phone='0300123')),client_key='phone')
        self.assertEqual(drafts.load(saved['name'])['payload']['client']['phone'],'0300123')

    def test_site_suggestions_include_sites_without_crew_and_typed_client_name(self):
        a=self.agreement();site=insert('PP Site',project=a['project'],site_name='Reception only',city='Lahore',address_line1='12 Main Road')
        rows=planning.recent_sites(customer_name=self.f.customer.customer_name)
        found=next(r for r in rows if r['site']==site.name)
        self.assertEqual(found['customer'],self.f.customer.name);self.assertFalse(found['has_plan']);self.assertEqual(found['city'],'Lahore')
        self.assertTrue(any(r['has_plan'] for r in rows))
        with patch('plus_point.operations.company',return_value=frappe._dict(name='Other company')):
            self.assertEqual(planning.recent_sites(customer_name=self.f.customer.customer_name),[])
        self.assertEqual(planning.recent_sites(),[])

    def test_native_assignment_rejects_same_dates_at_a_different_site(self):
        site=insert('PP Site',project=self.f.project.name,site_name='Second location')
        with self.assertRaisesRegex(frappe.ValidationError,'already booked'):
            insert('PP Assignment',employee=self.f.employee.name,project=self.f.project.name,contract_terms=self.f.terms.name,site=site.name,start_date=today(),end_date=today(),wage_rate=2000,client_rate=3000)

    def test_cross_event_booking_refused_and_next_unbooked_day_allowed(self):
        a=self.agreement();event=self.event(a);op.auto_assign(event)
        second=self.agreement(title='Different event agreement');site=op.agreement(second['name'])['venues'][0].name
        with self.assertRaisesRegex(frappe.ValidationError,'already booked'):
            insert('PP Assignment',employee=self.worker.name,project=second['project'],contract_terms=second['name'],site=site,start_date=add_days(today(),4),end_date=add_days(today(),4),wage_rate=1000,client_rate=1500)
        insert('PP Assignment',employee=self.worker.name,project=second['project'],contract_terms=second['name'],site=site,start_date=add_days(today(),5),end_date=add_days(today(),5),wage_rate=1000,client_rate=1500)
        self.assertIn(self.worker.name,op.worker_filter('Assigned'));self.assertNotIn(self.worker.name,op.worker_filter('Available'))

    def test_selected_unused_bookings_release_without_a_form(self):
        event=self.event();allocation=op.auto_assign(event)['assignments'][0]
        review=actions.review('PP Event Plan',event);self.assertEqual(review['resolution'],'event')
        self.assertEqual(actions.event_review(event)['workers'][0]['outstanding'],'0')
        actions.release_event_assignments(event,[allocation]);actions.remove('PP Event Plan',event)
        self.assertFalse(frappe.db.exists('PP Event Plan',event));self.assertFalse(frappe.db.exists('PP Assignment',allocation))

    def test_release_rejects_other_event_atomically(self):
        event=self.event();allocation=op.auto_assign(event)['assignments'][0]
        with self.assertRaises(frappe.PermissionError):actions.release_event_assignments(event,[allocation,self.f.assignment.name])
        self.assertTrue(frappe.db.exists('PP Assignment',allocation))

    def test_recorded_attendance_is_preserved_and_only_approved_wages_can_be_paid(self):
        event=self.event();allocation=op.auto_assign(event)['assignments'][0]
        work=insert('PP Work Entry',assignment=allocation,work_date=today(),units=1,status='Draft')
        before=frappe.db.count('Payment Entry')
        with self.assertRaises(frappe.ValidationError):actions.settle_event_crew(event,[self.worker.name],self.f.company.default_cash_account,today(),'No planned wages',balances={self.worker.name:0})
        self.assertEqual(before,frappe.db.count('Payment Entry'))
        with self.assertRaises(frappe.ValidationError):actions.release_event_assignments(event,[allocation])
        work.status='Approved';work.save()
        rows=actions.event_review(event)['workers'];worker=next(r for r in rows if r['employee']==self.worker.name)
        self.assertEqual(worker['outstanding'],'1000.00')
        with self.assertRaisesRegex(frappe.ValidationError,'balance changed'):actions.settle_event_crew(event,[self.worker.name],self.f.company.default_cash_account,today(),'Stale balance',balances={self.worker.name:999})
        self.assertEqual(before,frappe.db.count('Payment Entry'))
        paid=actions.settle_event_crew(event,[self.worker.name],self.f.company.default_cash_account,today(),'Confirmed crew payment',balances={self.worker.name:1000})
        self.assertEqual(actions.settle_event_crew(event,[self.worker.name],self.f.company.default_cash_account,today(),'Confirmed crew payment',balances={self.worker.name:1000}),paid)
        self.assertEqual(frappe.get_doc('Payment Entry',paid['payments'][0]).docstatus,1)
        self.assertEqual(actions.event_review(event)['workers'][0]['outstanding'],'0')
        actions.cancel_event(event)
        self.assertTrue(frappe.db.exists('PP Work Entry',work.name));self.assertTrue(frappe.db.exists('PP Event Plan',event))
        self.assertEqual(frappe.db.get_value('Project',frappe.get_doc('PP Event Plan',event).project,'status'),'Cancelled')
        self.assertEqual(str(frappe.db.get_value('PP Assignment',allocation,'end_date')),today())

    def test_cancellation_releases_unused_slots_and_retains_unpaid_earnings(self):
        event=self.event();allocation=op.auto_assign(event)['assignments'][0]
        work=insert('PP Work Entry',assignment=allocation,work_date=today(),units=.5,status='Draft');work.status='Approved';work.save()
        actions.cancel_event(event)
        self.assertEqual(actions.event_review(event)['workers'][0]['outstanding'],'500.00')
        self.assertTrue(actions.review('PP Event Plan',event)['blocked'])

    def test_worker_profile_and_bulk_pay_recheck_slots_and_use_monthly_profiles(self):
        from plus_point import benefits
        event=self.event();allocation=op.auto_assign(event)['assignments'][0]
        positions=benefits.event_positions(self.worker.name,event)
        self.assertTrue(positions['booked']);self.assertEqual(positions['positions'],[])
        with self.assertRaises(frappe.ValidationError):benefits.assign_event(self.worker.name,event,extra=1)
        frappe.db.set_value('Employee',self.worker.name,'pp_monthly_rate',9000)
        planning.save_pay_batch(event,[allocation],'Monthly')
        saved=frappe.get_doc('PP Assignment',allocation)
        self.assertEqual(saved.pp_pay_amount,9000);self.assertEqual(saved.wage_rate,300)
        insert('PP Work Entry',assignment=allocation,work_date=today(),units=1,status='Draft')
        with self.assertRaises(frappe.ValidationError):planning.save_pay_batch(event,[allocation],'Daily',1000)
        self.assertEqual(frappe.get_doc('PP Assignment',allocation).pp_pay_basis,'Monthly')

    def test_equipment_profile_uses_native_prices_without_posting_finances(self):
        from plus_point import resources
        import uuid
        item=insert('Item',item_code='Event chairs QA '+uuid.uuid4().hex[:8],item_name='Padded event chair',item_group='Services',stock_uom='Nos',is_stock_item=1)
        before=frappe.db.count('Sales Invoice')
        resources.save_equipment_rate(item.name,25)
        data=resources.equipment_profile(item.name)
        self.assertEqual(data['uom'],'Nos');self.assertEqual(data['daily_rate'],'25.0')
        self.assertTrue(frappe.db.exists('Item Price',{'item_code':item.name,'price_list':'Event daily hire PKR'}))
        self.assertEqual(frappe.db.count('Sales Invoice'),before)
        with self.assertRaises(frappe.ValidationError):resources.save_equipment_rate(item.name,-1)
        warehouse=frappe.db.get_value('Warehouse',{'company':self.f.company.name,'is_group':0},'name')
        resources.count_stock(warehouse,item.name,10,50,today())
        event=self.event();doc=frappe.get_doc('PP Event Plan',event)
        resources.save_booking(doc.project,'equipment',dict(site=doc.staffing[0].site,warehouse=warehouse,item=item.name,quantity=3,start_date=today(),end_date=today(),status='Planned'))
        stock=next(r for r in resources.equipment_profile(item.name)['stock'] if r['warehouse']==warehouse)
        self.assertEqual(float(stock['on_hand']),10);self.assertEqual(float(stock['reserved']),3);self.assertEqual(float(stock['available']),7)
