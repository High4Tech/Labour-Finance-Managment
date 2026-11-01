"""Real company ledgers; no balance query marks wages paid or changes history."""
import unittest
from unittest.mock import patch
import frappe
from frappe.utils import today, getdate
from plus_point.tests.test_operations import fixture, insert
from plus_point.wage_payments import overview, due_cutoff, set_cycle


class PaymentOverviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user('Administrator');cls.previous=frappe.flags.get('pp_test_entitlement');frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
        frappe.db.savepoint('payment_overview_suite');cls.f=fixture()
        cls.event=insert('PP Event Plan',event_name='Payment confirmation event',project=cls.f.project.name,contract_terms=cls.f.terms.name,
            start_date=today(),end_date=today(),wage_rate=2000,client_rate=3000,
            staffing=[dict(site=cls.f.site.name,phase='Event',start_date=today(),end_date=today(),workers_required=1)])
        cls.scope=patch('plus_point.event_setup.companies',return_value=[cls.f.company]);cls.scope.start()
    @classmethod
    def tearDownClass(cls):
        frappe.set_user('Administrator');cls.scope.stop();frappe.db.rollback(save_point='payment_overview_suite');frappe.flags.pp_test_entitlement=cls.previous
    def setUp(self):frappe.db.savepoint('payment_overview_case')
    def tearDown(self):
        frappe.set_user('Administrator');frappe.db.rollback(save_point='payment_overview_case')
    def work(self,approved):
        w=insert('PP Work Entry',assignment=self.f.assignment.name,work_date=today(),units=.5,status='Draft')
        if approved:w.status='Approved';w.save()
        return w
    def test_assigned_worker_without_approved_work_is_not_paid(self):
        self.work(False);data=overview(self.f.company.name)
        self.assertEqual(data['rows'][0]['status'],'No approved wages');self.assertEqual(data['summary']['outstanding'],'0')
    def test_actual_outstanding_is_approved_wages_not_projected_salary(self):
        self.work(True);data=overview(self.f.company.name)
        self.assertEqual(data['rows'][0]['status'],'Unpaid');self.assertEqual(data['rows'][0]['outstanding'],'1000.00');self.assertEqual(data['rows'][0]['paid'],'0')
    def test_configuring_cadence_does_not_create_money_or_work(self):
        self.work(True);types=['Payment Entry','PP Wage Settlement','PP Loan Recovery','PP Work Entry','GL Entry'];before={dt:frappe.db.count(dt) for dt in types}
        set_cycle(self.event.name,'Daily');data=overview(self.f.company.name)
        self.assertEqual(data['rows'][0]['cycle'],'Daily');self.assertEqual(data['rows'][0]['due'],'0')
        self.assertEqual(before,{dt:frappe.db.count(dt) for dt in types})
    def test_daily_and_monthly_cutoffs_and_final_event_pay(self):
        event=frappe._dict(wage_payment_cycle='Daily',end_date='2027-06-30')
        self.assertEqual(due_cutoff(event,'2027-02-01'),getdate('2027-01-31'))
        event.wage_payment_cycle='Monthly';self.assertEqual(due_cutoff(event,'2027-02-23'),getdate('2027-01-31'))
        event.end_date='2027-02-10';self.assertEqual(due_cutoff(event,'2027-02-23'),getdate('2027-02-10'))
        event.wage_payment_cycle='Manual';self.assertIsNone(due_cutoff(event,'2027-02-23'))
    def test_partial_and_complete_actual_payments_update_status_once(self):
        self.work(True)
        payment=insert('Payment Entry',company=self.f.company.name,project=self.f.project.name,payment_type='Pay',party_type='Employee',party=self.f.employee.name,
            posting_date=today(),paid_from=self.f.company.default_cash_account,paid_to=self.f.company.default_payable_account,
            paid_amount=400,received_amount=400,source_exchange_rate=1,target_exchange_rate=1,reference_no='Partial wages QA',reference_date=today())
        payment.submit();insert('PP Wage Settlement',employee=self.f.employee.name,project=self.f.project.name,payment_entry=payment.name).submit()
        row=overview(self.f.company.name)['rows'][0]
        self.assertEqual(row['status'],'Partly paid');self.assertEqual(row['paid'],'400.00');self.assertEqual(row['outstanding'],'600.00')
        from plus_point.record_actions import settle_event_crew
        args=dict(name=self.event.name,employees=[self.f.employee.name],account=self.f.company.default_cash_account,posting_date=today(),reference='Final wages QA',balances={self.f.employee.name:600})
        first=settle_event_crew(**args);self.assertEqual(settle_event_crew(**args),first)
        row=overview(self.f.company.name)['rows'][0]
        self.assertEqual(row['status'],'Paid');self.assertEqual(row['outstanding'],'0');self.assertEqual(row['paid'],'1000.00')
    def test_scope_invalid_event_and_invalid_cadence(self):
        with self.assertRaises(frappe.PermissionError):overview('other-company')
        with self.assertRaises(frappe.PermissionError):overview(self.f.company.name,event='other-event')
        with self.assertRaises(frappe.ValidationError):set_cycle(self.event.name,'Automatically paid')
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):overview(self.f.company.name)
    def test_search_is_bounded_and_does_not_expose_unrelated_records(self):
        from plus_point.company_tools import search
        rows=search('workers',self.f.employee.name,self.f.company.name)
        self.assertEqual([r['name'] for r in rows],[self.f.employee.name]);self.assertLessEqual(len(rows),20)
        self.assertEqual(search('workers','no matching worker anywhere',self.f.company.name),[])
        with self.assertRaises(frappe.ValidationError):search('User','',self.f.company.name)
        clients=search('clients',self.f.customer.name,self.f.company.name)
        self.assertEqual([r['name'] for r in clients],[self.f.customer.name])
        self.assertTrue(clients[0]['href'].startswith('/desk/customer/'))
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):search('clients','',self.f.company.name)
    def test_mark_read_rejects_unowned_notifications(self):
        from plus_point.company_tools import mark_read
        with self.assertRaises(frappe.PermissionError):mark_read(['unowned-notification'])

    def batch_items(self):
        self.work(True)
        project=insert('Project',project_name=self.f.company.name+' second event',company=self.f.company.name,customer=self.f.customer.name)
        worker=insert('Employee',first_name='Second Batch Worker',gender='Male',date_of_birth='1990-01-01',date_of_joining='2020-01-01',company=self.f.company.name,status='Active')
        contract=insert('Contract',party_type='Customer',party_name=self.f.customer.name,contract_terms='Second event QA',start_date=today())
        terms=insert('PP Contract Terms',contract=contract.name,project=project.name,billing_model='Daily',currency='PKR',status='Active',effective_start=today())
        site=insert('PP Site',site_name='Second batch venue',project=project.name,is_active=1)
        event=insert('PP Event Plan',event_name='Second batch event',project=project.name,contract_terms=terms.name,start_date=today(),end_date=today(),wage_rate=500,client_rate=1000,
            staffing=[dict(site=site.name,phase='Event',start_date=today(),end_date=today(),workers_required=1)])
        assignment=insert('PP Assignment',employee=worker.name,site=site.name,project=project.name,contract_terms=terms.name,start_date=today(),end_date=today(),wage_rate=500,client_rate=1000)
        work=insert('PP Work Entry',assignment=assignment.name,work_date=today(),units=.5,status='Draft');work.status='Approved';work.save()
        return [dict(event=self.event.name,employee=self.f.employee.name,balance='1000'),dict(event=event.name,employee=worker.name,balance='250')]

    def test_multi_event_batch_reviews_and_posts_once(self):
        from plus_point.wage_payments import review_payments,record_payments
        items=self.batch_items();review=review_payments(items,self.f.company.name)
        self.assertEqual(review['currency'],'PKR');self.assertEqual(review['total'],'1250.00');self.assertEqual(len({r['event'] for r in review['rows']}),2)
        args=dict(items=items,company=self.f.company.name,account=self.f.company.default_cash_account,posting_date=today(),reference='Multi event batch QA')
        first=record_payments(**args);self.assertEqual(len(first['payments']),2);self.assertEqual(first,record_payments(**args))
        rows=overview(self.f.company.name)['rows'];self.assertEqual({r['status'] for r in rows},{'Paid'});self.assertEqual({r['outstanding'] for r in rows},{'0'})

    def test_multi_event_batch_rolls_back_every_payment_if_one_balance_changed(self):
        from plus_point.wage_payments import record_payments
        items=sorted(self.batch_items(),key=lambda r:r['event']);items[-1]['balance']='9999'
        types=['Payment Entry','PP Wage Settlement','GL Entry'];before={dt:frappe.db.count(dt) for dt in types}
        with self.assertRaises(frappe.ValidationError):record_payments(items,self.f.company.default_cash_account,today(),'Stale batch QA',self.f.company.name)
        self.assertEqual(before,{dt:frappe.db.count(dt) for dt in types})

    def test_batch_rejects_duplicate_or_unreviewed_rows(self):
        from plus_point.wage_payments import review_payments
        item=dict(event=self.event.name,employee=self.f.employee.name,balance=1000)
        with self.assertRaises(frappe.ValidationError):review_payments([item,item],self.f.company.name)
        with self.assertRaises(frappe.ValidationError):review_payments([dict(event=self.event.name,employee=self.f.employee.name)],self.f.company.name)
        with self.assertRaises(frappe.ValidationError):review_payments([item]*201,self.f.company.name)
