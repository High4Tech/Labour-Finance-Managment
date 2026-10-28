"""Read-only dashboard periods, scope, snapshots and conversion on native business fixtures."""
import unittest,uuid
from decimal import Decimal
from unittest.mock import patch
import frappe
from frappe.utils import today, add_days
from plus_point.tests.test_operations import fixture, insert
from plus_point.dashboard_analytics import analytics, snapshot, period_dates


class DashboardAnalyticsTests(unittest.TestCase):
    def setUp(self):
        frappe.set_user('Administrator');self.previous=frappe.flags.get('pp_test_entitlement');frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
        frappe.db.savepoint('dashboard_analytics');self.f=fixture();self.scope=patch('plus_point.event_setup.companies',return_value=[self.f.company]);self.scope.start()
    def tearDown(self):
        frappe.set_user('Administrator');self.scope.stop();frappe.db.rollback(save_point='dashboard_analytics');frappe.flags.pp_test_entitlement=self.previous
    def work(self,approved=True):
        doc=insert('PP Work Entry',assignment=self.f.assignment.name,work_date=today(),units=.5,status='Draft')
        if approved:doc.status='Approved';doc.save()
        return doc
    def test_approved_half_day_uses_saved_rates_and_actual_dates(self):
        self.work();data=analytics(self.f.company.name)
        self.assertEqual(data['approved_days'],'0.5');self.assertEqual(data['finance_series'][-1]['revenue'],'1500.00');self.assertEqual(data['finance_series'][-1]['wages'],'1000.00')
    def test_drafts_and_previous_month_do_not_earn_revenue(self):
        self.work(False);data=analytics(self.f.company.name)
        self.assertEqual(data['approved_days'],'0');self.assertTrue(all(Decimal(r['revenue'])==0 for r in data['finance_series']))
        self.assertLess(period_dates('last_month')[1],period_dates('month')[0])
    def test_assignment_distribution_does_not_claim_unique_workers(self):
        site=insert('PP Site',site_name='Second dashboard venue',project=self.f.project.name)
        # Legacy overlaps remain reportable; new overlapping bookings are refused.
        legacy=frappe.get_doc(dict(doctype='PP Assignment',employee=self.f.employee.name,site=site.name,project=self.f.project.name,contract_terms=self.f.terms.name,start_date=today(),wage_rate=2000,client_rate=3000))
        legacy.name='legacy-dashboard-'+uuid.uuid4().hex[:10];legacy.db_insert()
        data=snapshot(self.f.company.name,[self.f.project.name],[self.f.employee.name]);self.assertEqual(data['assignment_total'],2);self.assertEqual(sum(r['value'] for r in data['assignments']),2)
    def test_outstanding_wages_have_no_invented_due_date(self):
        self.work();data=snapshot(self.f.company.name,[self.f.project.name],[self.f.employee.name])
        self.assertEqual(data['payments'][0]['amount'],'1000.00');self.assertNotIn('due_date',data['payments'][0]);self.assertEqual(len(data['recent']),1)
    def test_dashboard_loading_does_not_post_or_create_financial_records(self):
        self.work();types=['GL Entry','Sales Invoice','Payment Entry','PP Wage Settlement','PP Loan Recovery','PP Work Entry'];before={dt:frappe.db.count(dt) for dt in types}
        analytics(self.f.company.name);snapshot(self.f.company.name,[self.f.project.name],[self.f.employee.name])
        self.assertEqual(before,{dt:frappe.db.count(dt) for dt in types})
    def test_invalid_period_company_and_guest_are_rejected(self):
        with self.assertRaises(frappe.ValidationError):analytics(self.f.company.name,period='forever')
        with self.assertRaises(frappe.PermissionError):analytics('different-company')
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):analytics(self.f.company.name)
    def test_display_conversion_preserves_worker_days_and_native_amounts(self):
        work=self.work()
        with patch('plus_point.exchange._snapshot',return_value=dict(updated=1700000000,rates={'USD':'1','PKR':'100'})):
            data=analytics(self.f.company.name,display_currency='USD')
        self.assertEqual(data['approved_days'],'0.5');self.assertEqual(data['finance_series'][-1]['revenue'],'15.00');self.assertEqual(data['currency'],'USD');self.assertEqual(frappe.db.get_value('PP Work Entry',work.name,'billable_amount'),1500)
    def test_failed_conversion_keeps_original_currency_and_values(self):
        from plus_point.exchange import RateUnavailable
        self.work()
        with patch('plus_point.exchange._snapshot',side_effect=RateUnavailable('offline')):data=analytics(self.f.company.name,display_currency='USD')
        self.assertEqual(data['currency'],'PKR');self.assertEqual(data['fx']['status'],'unavailable');self.assertEqual(data['finance_series'][-1]['revenue'],'1500.00')

    def test_overview_uses_native_report_amounts_before_one_display_conversion(self):
        from plus_point.dashboard import overview
        self.work();native=frappe.defaults.get_user_default
        with patch('frappe.defaults.get_user_default',side_effect=lambda key,*a,**kw:'USD' if key=='pp_display_currency' else native(key,*a,**kw)),patch('plus_point.exchange._snapshot',return_value=dict(updated=1700000000,rates={'USD':'1','PKR':'100'})):
            data=overview(company=self.f.company.name,display_currency='USD')
        self.assertEqual(data['earned_revenue'],'15.00');self.assertEqual(data['dashboard_snapshot']['payments'][0]['amount'],'10.00')
