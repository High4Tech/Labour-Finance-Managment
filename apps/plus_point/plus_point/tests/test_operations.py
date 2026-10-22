"""Real MariaDB/ERPNext/HRMS tests. All business fixtures roll back after the suite."""
from datetime import date
from decimal import Decimal
import unittest
import uuid
import frappe
from frappe.utils import today, add_days
from plus_point.api import project_summary, prepare_daily_register, worker_statement
from plus_point.billing import create_invoice
from plus_point.tenancy import enforce_write
from plus_point.reporting import project_finances, worker_statement_report


def insert(doctype, **values):
    return frappe.get_doc(dict(doctype=doctype, **values)).insert()


def fixture(prefix=None):
    prefix = prefix or ('PP QA ' + uuid.uuid4().hex[:8])
    company = insert('Company', company_name=prefix, abbr=uuid.uuid4().hex[:5],
                     country='Pakistan', default_currency='PKR')
    customer = insert('Customer', customer_name=prefix, customer_type='Company',
                      customer_group='Commercial', territory='All Territories')
    project = insert('Project', project_name=prefix, company=company.name, customer=customer.name)
    employee = insert('Employee', first_name='Test Worker '+''.join(chr(97+int(c,16)) for c in company.abbr), gender='Male', date_of_birth='1990-01-01',
                      date_of_joining='2020-01-01', company=company.name, status='Active')
    contract = insert('Contract', party_type='Customer', party_name=customer.name,
                      contract_terms='Temporary QA contract', start_date=today())
    terms = insert('PP Contract Terms', contract=contract.name, project=project.name,
                   billing_model='Daily', currency='PKR', status='Active', effective_start=today())
    site = insert('PP Site', site_name=prefix, project=project.name, is_active=1)
    assignment = insert('PP Assignment', employee=employee.name, site=site.name, project=project.name,
                        contract_terms=terms.name, start_date=today(), wage_rate=2000, client_rate=3000)
    item = insert('Item', item_code=prefix, item_name=prefix, item_group='Services',
                  stock_uom='Nos', is_stock_item=0)
    return frappe._dict(company=company, customer=customer, project=project, employee=employee,
                        contract=contract, terms=terms, site=site, assignment=assignment, item=item)


class OperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user('Administrator')
        cls.original_override=frappe.flags.get('pp_test_entitlement')
        frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
        frappe.db.savepoint('pp_suite')
        cls.f = fixture()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user('Administrator')
        frappe.db.rollback(save_point='pp_suite')
        frappe.flags.pp_test_entitlement=cls.original_override

    def setUp(self):
        frappe.set_user('Administrator')
        frappe.db.savepoint('pp_test')
        self.original_entitlement = frappe.conf.get('pp_entitlement')
        frappe.flags.pp_test_entitlement = {'valid_until':'2099-12-31'}

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.conf.pp_entitlement = self.original_entitlement
        frappe.flags.pp_test_entitlement = {'valid_until':'2099-12-31'}
        frappe.db.rollback(save_point='pp_test')

    def work(self, units=1, day=None, assignment=None):
        work = insert('PP Work Entry', assignment=(assignment or self.f.assignment).name,
                      work_date=day or today(), units=units, status='Draft')
        work.status = 'Approved'
        work.save()
        return work

    def fixed_terms(self):
        contract = insert('Contract', party_type='Customer', party_name=self.f.customer.name,
                          contract_terms='Fixed QA contract', start_date=today())
        return insert('PP Contract Terms', contract=contract.name, project=self.f.project.name,
                       billing_model='Fixed', fixed_amount=10000, currency='PKR', status='Active', effective_start=today())

    def test_real_relationships_and_daily_rates(self):
        work = self.work('0.5')
        self.assertEqual(work.employee, self.f.employee.name)
        self.assertEqual(work.project, self.f.project.name)
        self.assertEqual(money(work.wage_amount), Decimal('1000.00'))
        self.assertEqual(money(work.billable_amount), Decimal('1500.00'))
        summary = project_summary(self.f.project.name)
        self.assertEqual(summary['earned_revenue'], '1500.00')
        self.assertEqual(worker_statement(self.f.employee.name)['wages_earned'], '1000.00')

    def test_duplicate_attendance_rejected(self):
        self.work()
        with self.assertRaises(frappe.ValidationError):
            self.work()

    def test_full_day_across_sites_rejected(self):
        self.work()
        site = insert('PP Site', site_name='Second QA site', project=self.f.project.name)
        assignment = insert('PP Assignment', employee=self.f.employee.name, site=site.name,
            project=self.f.project.name, contract_terms=self.f.terms.name, start_date=today(), wage_rate=2000, client_rate=3000)
        with self.assertRaises(frappe.ValidationError):
            self.work(0.5, assignment=assignment)

    def test_snapshot_cannot_be_changed(self):
        work = insert('PP Work Entry', assignment=self.f.assignment.name, work_date=today(), units=1)
        work.wage_rate = 1
        with self.assertRaises(frappe.ValidationError):
            work.save()

    def test_approved_work_immutable(self):
        work = self.work()
        work.units = 0.5
        with self.assertRaises(frappe.ValidationError):
            work.save()

    def test_bulk_register_posts_work_atomically(self):
        result = prepare_daily_register(self.f.site.name, today())
        register = frappe.get_doc('PP Daily Register', result['name'])
        register.entries[0].attendance_status='Present';register.entries[0].units='1'
        register.submit()
        work = frappe.get_doc('PP Work Entry', register.entries[0].work_entry)
        self.assertEqual(work.status, 'Approved')
        self.assertEqual(work.wage_amount, 2000)
        self.assertEqual(register.docstatus, 1)

    def test_used_assignment_cannot_rewrite_history(self):
        self.work()
        assignment = frappe.get_doc('PP Assignment', self.f.assignment.name)
        assignment.wage_rate = 1
        with self.assertRaises(frappe.ValidationError):
            assignment.save()

    def test_zero_amount_terms_can_close_without_rewriting_history(self):
        self.work()
        terms = frappe.get_doc('PP Contract Terms', self.f.terms.name)
        terms.fixed_amount = 0
        terms.status = 'Closed'
        terms.save()
        self.assertEqual(terms.status, 'Closed')

    def test_used_assignment_allows_notes_without_numeric_representation_error(self):
        self.work()
        assignment = frappe.get_doc('PP Assignment', self.f.assignment.name)
        assignment.wage_rate = '2000'
        assignment.notes = 'QA historical note'
        assignment.save()
        self.assertEqual(assignment.notes, 'QA historical note')

    def test_summary_does_not_silently_stop_at_twenty_rows(self):
        for n in range(25):
            self.work(day=add_days(today(), n))
        self.assertEqual(project_summary(self.f.project.name)['earned_revenue'], '75000.00')
        statement = worker_statement_report(dict(company=self.f.company.name, employee=self.f.employee.name))
        self.assertEqual(len(statement[1]), 25)
        self.assertEqual(statement[4][-1]['value'], Decimal('50000.00'))

    def test_fixed_milestone_cap(self):
        terms = self.fixed_terms()
        insert('PP Milestone', contract_terms=terms.name, milestone_title='First', amount=7000, status='Approved')
        self.assertEqual(project_summary(self.f.project.name)['earned_revenue'], '7000.00')
        with self.assertRaises(frappe.ValidationError):
            insert('PP Milestone', contract_terms=terms.name, milestone_title='Too much', amount=4000, status='Approved')

    def test_fixed_worker_days_do_not_create_daily_revenue(self):
        terms = self.fixed_terms()
        self.f.assignment.delete()
        assignment = insert('PP Assignment', employee=self.f.employee.name, site=self.f.site.name,
            project=self.f.project.name, contract_terms=terms.name, start_date=today(), wage_rate=2000, client_rate=0)
        work = self.work(assignment=assignment)
        self.assertEqual(work.billable_amount, 0)
        self.assertEqual(project_summary(self.f.project.name)['earned_revenue'], '0.00')
        report = worker_statement_report(dict(company=self.f.company.name, employee=self.f.employee.name))
        self.assertEqual(report[1][0]['direct_client_earnings'], Decimal('0.00'))
        finances = project_finances(dict(company=self.f.company.name))
        self.assertEqual(finances[1][0]['fixed_contract_value'], '10000.00')
        self.assertEqual(finances[1][0]['earned_revenue'], '0.00')

    def test_used_assignment_can_close_and_new_rate_preserves_history(self):
        work = self.work()
        assignment = frappe.get_doc('PP Assignment', self.f.assignment.name)
        assignment.end_date = today()
        assignment.save()
        replacement = insert('PP Assignment', employee=assignment.employee, site=assignment.site,
            project=assignment.project, contract_terms=assignment.contract_terms,
            start_date=add_days(today(), 1), wage_rate=2500, client_rate=3500)
        next_work = self.work(day=add_days(today(), 1), assignment=replacement)
        work.reload()
        self.assertEqual(money(work.wage_amount), Decimal('2000.00'))
        self.assertEqual(money(next_work.wage_amount), Decimal('2500.00'))
        prepared = prepare_daily_register(self.f.site.name, add_days(today(), 2))
        self.assertEqual(frappe.get_doc('PP Daily Register', prepared['name']).entries[0].assignment, replacement.name)
        with self.assertRaises(frappe.ValidationError):
            assignment.end_date = None
            assignment.save()

    def test_assignment_close_cannot_exclude_existing_draft(self):
        insert('PP Work Entry', assignment=self.f.assignment.name, work_date=add_days(today(), 2), units=1)
        assignment = frappe.get_doc('PP Assignment', self.f.assignment.name)
        assignment.end_date = today()
        with self.assertRaises(frappe.ValidationError):
            assignment.save()

    def test_same_site_assignment_overlap_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            insert('PP Assignment', employee=self.f.employee.name, site=self.f.site.name,
                project=self.f.project.name, contract_terms=self.f.terms.name,
                start_date=add_days(today(), 1), wage_rate=2500, client_rate=3500)

    def test_worker_statement_opening_and_period_payments(self):
        self.work()
        self.work('0.5', day=add_days(today(), 1))
        company = self.f.company
        payment = insert('Payment Entry', payment_type='Pay', company=company.name,
            party_type='Employee', party=self.f.employee.name, project=self.f.project.name,
            posting_date=add_days(today(), 1), paid_from=company.default_cash_account,
            paid_to=company.default_payable_account, paid_amount=500, received_amount=500,
            source_exchange_rate=1, target_exchange_rate=1, reference_no='PP statement QA', reference_date=today())
        payment.submit()
        insert('PP Wage Settlement', employee=self.f.employee.name, project=self.f.project.name,
            payment_entry=payment.name).submit()
        filters = dict(company=company.name, employee=self.f.employee.name,
                       from_date=add_days(today(), 1), to_date=add_days(today(), 1))
        report = worker_statement_report(filters)
        self.assertEqual([row['kind'] for row in report[1]], ['Work', 'Payment'])
        self.assertEqual([row['value'] for row in report[4]],
            [Decimal('2000.00'), Decimal('0.5'), Decimal('1000.00'), Decimal('500.00'), Decimal('2500.00')])
        self.assertEqual(report[1][-1]['payment_entry'], payment.name)
        prior = worker_statement_report(dict(filters, from_date=today(), to_date=today()))
        self.assertEqual(prior[4][-1]['value'], Decimal('2000.00'))
        self.assertEqual(len(prior[1]), 1)

    def test_deployment_report_deduplicates_workers_without_claiming_attendance(self):
        site = insert('PP Site', site_name='Second statement QA site', project=self.f.project.name)
        insert('PP Assignment', employee=self.f.employee.name, site=site.name, project=self.f.project.name,
            contract_terms=self.f.terms.name, start_date=today(), wage_rate=2000, client_rate=3000)
        report = project_finances(dict(company=self.f.company.name, view='Deployment overview'))
        self.assertEqual(len(report[1]), 1)
        self.assertEqual(report[1][0]['active_sites'], 2)
        self.assertEqual(report[1][0]['deployed_today'], 1)
        self.assertEqual(report[1][0]['worked_days'], Decimal(0))
        self.assertIn('not confirmed attendance', report[2])
        history = worker_statement_report(dict(company=self.f.company.name, employee=self.f.employee.name,
                                               view='Assignment history'))
        self.assertEqual(len(history[1]), 2)

    def test_reports_validate_company_and_date_scope(self):
        other = fixture()
        with self.assertRaises(frappe.ValidationError):
            project_finances(dict(company=other.company.name, project=self.f.project.name))
        with self.assertRaises(frappe.ValidationError):
            worker_statement_report(dict(company=self.f.company.name, employee=self.f.employee.name,
                from_date=add_days(today(), 1), to_date=today()))
        self.assertEqual(project_finances(dict(company=other.company.name, customer=self.f.customer.name))[1], [])
        self.work()
        self.assertEqual(worker_statement_report(dict(company=other.company.name, employee=self.f.employee.name))[1], [])

    def test_reports_reject_guests_and_control_plane(self):
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            project_finances(dict(company=self.f.company.name))
        with self.assertRaises(frappe.PermissionError):
            worker_statement_report(dict(company=self.f.company.name, employee=self.f.employee.name))
        frappe.set_user('Administrator')
        original = frappe.conf.get('pp_control_plane')
        try:
            frappe.conf.pp_control_plane = True
            with self.assertRaises(frappe.PermissionError):
                project_finances(dict(company=self.f.company.name))
        finally:
            frappe.conf.pp_control_plane = original

    def test_native_invoice_reserves_sources_and_releases_deleted_draft(self):
        work = self.work()
        result = create_invoice(self.f.terms.name, self.f.item.name)
        invoice = frappe.get_doc('Sales Invoice', result['name'])
        self.assertEqual(invoice.customer, self.f.customer.name)
        self.assertEqual(money(invoice.net_total), Decimal('3000.00'))
        self.assertEqual(frappe.db.get_value('PP Work Entry', work.name, 'sales_invoice'), invoice.name)
        with self.assertRaises(frappe.ValidationError):
            create_invoice(self.f.terms.name, self.f.item.name)
        invoice.delete()
        self.assertFalse(frappe.db.get_value('PP Work Entry', work.name, 'sales_invoice'))

    def test_guest_finance_access_rejected(self):
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            project_summary(self.f.project.name)
        with self.assertRaises(frappe.PermissionError):
            create_invoice(self.f.terms.name, self.f.item.name)

    def test_authenticated_non_manager_is_denied(self):
        user = insert('User', email='pp-qa-' + uuid.uuid4().hex[:8] + '@example.invalid',
            first_name='PLUS POINT QA Reader', send_welcome_email=0,
            roles=[{'role': 'Employee'}])
        frappe.set_user(user.name)
        with self.assertRaises(frappe.PermissionError):
            project_summary(self.f.project.name)
        with self.assertRaises(frappe.PermissionError):
            insert('PP Site', site_name='Unauthorized', project=self.f.project.name)

    def test_submitted_native_invoice_and_receivable(self):
        year = date.today().year
        if not frappe.db.exists('Fiscal Year', str(year)):
            insert('Fiscal Year', year=str(year), year_start_date=f'{year}-01-01', year_end_date=f'{year}-12-31')
        self.work()
        result = create_invoice(self.f.terms.name, self.f.item.name)
        invoice = frappe.get_doc('Sales Invoice', result['name'])
        invoice.submit()
        summary = project_summary(self.f.project.name)
        self.assertEqual(summary['invoiced_net'], '3000.00')
        self.assertEqual(summary['client_outstanding_gross'], '3000.00')
        self.assertTrue(frappe.db.exists('GL Entry', {'voucher_type': 'Sales Invoice', 'voucher_no': invoice.name, 'is_cancelled': 0}))
        invoice.cancel()
        self.assertEqual(project_summary(self.f.project.name)['invoiced_net'], '0.00')

    def test_milestone_invoice_uses_native_submission(self):
        year = date.today().year
        if not frappe.db.exists('Fiscal Year', str(year)):
            insert('Fiscal Year', year=str(year), year_start_date=f'{year}-01-01', year_end_date=f'{year}-12-31')
        terms = self.fixed_terms()
        milestone = insert('PP Milestone', contract_terms=terms.name, milestone_title='Approved QA', amount=5000, status='Approved')
        result = create_invoice(terms.name, self.f.item.name)
        self.assertEqual(frappe.db.get_value('PP Milestone', milestone.name, 'status'), 'Approved')
        invoice = frappe.get_doc('Sales Invoice', result['name'])
        invoice.submit()
        self.assertEqual(frappe.db.get_value('PP Milestone', milestone.name, 'status'), 'Invoiced')
        invoice.cancel()
        self.assertEqual(frappe.db.get_value('PP Milestone', milestone.name, 'status'), 'Approved')

    def test_billing_cannot_change_approved_amount(self):
        self.work()
        result = create_invoice(self.f.terms.name, self.f.item.name)
        invoice = frappe.get_doc('Sales Invoice', result['name'])
        invoice.items[0].rate = 1
        with self.assertRaises(frappe.ValidationError):
            invoice.save()

    def test_wage_settlement_uses_posted_native_payment(self):
        self.work()
        company = frappe.get_doc('Company', self.f.company.name)
        payment = insert('Payment Entry', payment_type='Pay', company=company.name,
            party_type='Employee', party=self.f.employee.name, project=self.f.project.name,
            paid_from=company.default_cash_account, paid_to=company.default_payable_account,
            paid_amount=1000, received_amount=1000, source_exchange_rate=1, target_exchange_rate=1,
            reference_no='PP QA', reference_date=today())
        payment.submit()
        settlement = insert('PP Wage Settlement', employee=self.f.employee.name, project=self.f.project.name,
            payment_entry=payment.name)
        settlement.submit()
        self.assertEqual(project_summary(self.f.project.name)['wages_paid'], '1000.00')
        self.assertEqual(project_summary(self.f.project.name)['wages_outstanding'], '1000.00')
        with self.assertRaises(frappe.ValidationError):
            payment.cancel()

    def test_unpaid_wages_are_not_marked_paid(self):
        self.work()
        self.assertEqual(project_summary(self.f.project.name)['wages_paid'], '0.00')
        self.assertEqual(project_summary(self.f.project.name)['wages_outstanding'], '2000.00')

    def test_native_client_receipt_is_distinct_from_invoice_revenue(self):
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
        self.work()
        invoice = frappe.get_doc('Sales Invoice', create_invoice(self.f.terms.name, self.f.item.name)['name'])
        invoice.submit()
        self.assertEqual(project_summary(self.f.project.name)['cash_collected_gross'], '0.00')
        company = frappe.get_doc('Company', self.f.company.name)
        payment = get_payment_entry('Sales Invoice', invoice.name, bank_account=company.default_cash_account)
        payment.project = self.f.project.name
        payment.reference_no = 'PP QA Receipt'
        payment.reference_date = today()
        payment.insert()
        payment.submit()
        summary = project_summary(self.f.project.name)
        self.assertEqual(summary['cash_collected_gross'], '3000.00')
        self.assertEqual(summary['client_outstanding_gross'], '0.00')
        self.assertEqual(summary['earned_revenue'], '3000.00')
        report = project_finances(dict(company=self.f.company.name))
        self.assertEqual(report[1][0]['cash_collected_gross'], '3000.00')
        self.assertEqual(report[1][0]['invoiced_gross'], '3000.00')
        self.assertEqual(report[1][0]['earned_revenue'], '3000.00')

    def test_expired_subscription_blocks_upstream_and_custom_writes(self):
        frappe.flags.pp_test_entitlement = {'valid_until': '2000-01-01'}
        with self.assertRaises(frappe.PermissionError):
            insert('Customer', customer_name='Blocked', customer_type='Company', customer_group='Commercial', territory='All Territories')
        with self.assertRaises(frappe.PermissionError):
            insert('PP Site', site_name='Blocked', project=self.f.project.name)
        self.assertEqual(frappe.get_doc('PP Site', self.f.site.name).name, self.f.site.name)

    def test_plan_limit_blocks_site_creation(self):
        frappe.flags.pp_test_entitlement = {'valid_until': '2099-12-31', 'limits': {'sites': 1}}
        with self.assertRaises(frappe.PermissionError):
            insert('PP Site', site_name='Over limit', project=self.f.project.name)

    def test_tenant_admin_cannot_use_platform_registry(self):
        from plus_point.platform import require_platform
        with self.assertRaises(frappe.PermissionError):
            require_platform()

    def test_dashboard_company_totals_match_approved_work(self):
        from plus_point.dashboard import overview
        self.work('0.5')
        result = overview(self.f.company.name)
        self.assertEqual(result['company'], self.f.company.name)
        self.assertEqual(result['workers'], 1)
        self.assertEqual(result['active_sites'], 1)
        self.assertEqual(result['open_projects'], 1)
        self.assertEqual(result['wages_unpaid'], '1000.00')
        self.assertEqual(result['earned_revenue'], '1500.00')
        self.assertEqual(result['contribution'], '500.00')
        self.assertEqual(result['client_balance'], '0.00')
        self.assertEqual(result['attendance'][-1]['units'], '0.5')
        self.assertEqual([row['name'] for row in result['projects']], [self.f.project.name])

    def test_dashboard_excludes_drafts_and_rejects_unauthorized_scope(self):
        from plus_point.dashboard import overview
        insert('PP Work Entry', assignment=self.f.assignment.name, work_date=today(), units=1, status='Draft')
        result = overview(self.f.company.name)
        self.assertEqual(result['wages_unpaid'], '0.00')
        self.assertEqual(result['attendance'][-1]['units'], '0')
        with self.assertRaises(frappe.PermissionError):
            overview('missing-dashboard-company')
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            overview(self.f.company.name)

    def set_spending_budget(self, amount):
        project=frappe.get_doc('Project',self.f.project.name)
        project.estimated_costing=amount
        project.pp_enforce_spending_budget=1
        project.save()

    def test_spending_limit_warns_at_eighty_percent_and_blocks_approval(self):
        from plus_point.budget import status
        self.set_spending_budget(1250)
        self.work('0.5')
        self.assertEqual(status(self.f.project.name)['level'],'warning')
        self.assertEqual(status(self.f.project.name)['used'],'1000.00')
        with self.assertRaises(frappe.ValidationError):
            self.work('0.5',day=add_days(today(),1))
        self.assertEqual(frappe.db.count('PP Work Entry',{'project':self.f.project.name,'status':'Approved'}),1)
        self.assertEqual(status(self.f.project.name)['used'],'1000.00')

    def test_budget_is_separate_from_fixed_revenue_and_existing_overrun_is_visible(self):
        from plus_point.budget import status
        self.set_spending_budget(2000)
        fixed=self.fixed_terms()
        insert('PP Milestone',contract_terms=fixed.name,milestone_title='QA separate client price',amount=9000,status='Approved')
        self.work()
        self.assertEqual(status(self.f.project.name)['remaining'],'0.00')
        self.set_spending_budget(1500)
        self.assertEqual(status(self.f.project.name)['level'],'error')
        self.assertEqual(status(self.f.project.name)['remaining'],'-500.00')
        self.work(0,day=add_days(today(),1))  # zero-cost records still work during an overrun
        self.assertEqual(status(self.f.project.name)['used'],'2000.00')

    def test_over_budget_register_stops_before_creating_any_wages(self):
        self.set_spending_budget(1000)
        result=prepare_daily_register(self.f.site.name,today())
        register=frappe.get_doc('PP Daily Register',result['name'])
        register.entries[0].attendance_status='Present';register.entries[0].units='1'
        with self.assertRaises(frappe.ValidationError):
            register.submit()
        self.assertEqual(frappe.db.get_value('PP Daily Register',register.name,'docstatus'),0)
        self.assertEqual(frappe.db.count('PP Work Entry',{'project':self.f.project.name}),0)

    def test_native_purchase_spending_is_checked_and_counted_once(self):
        from plus_point.budget import status, costs, costs_many
        self.set_spending_budget(1200)
        self.work('0.5')
        company=frappe.get_doc('Company',self.f.company.name)
        supplier=insert('Supplier',supplier_name='PP budget '+uuid.uuid4().hex[:8],supplier_group='All Supplier Groups',supplier_type='Company')
        invoice=insert('Purchase Invoice',company=company.name,supplier=supplier.name,project=self.f.project.name,
            items=[dict(item_code=self.f.item.name,qty=1,rate=300,project=self.f.project.name,
                        expense_account=company.default_expense_account,cost_center=company.cost_center)])
        with self.assertRaises(frappe.ValidationError):
            invoice.submit()
        self.assertEqual(frappe.db.get_value('Purchase Invoice',invoice.name,'docstatus'),0)
        invoice.reload();invoice.items[0].rate=200;invoice.save();invoice.submit()
        self.assertEqual(status(self.f.project.name)['used'],'1200.00')
        self.assertEqual(project_summary(self.f.project.name)['other_project_costs'],'200.00')
        self.assertEqual(costs_many([self.f.project.name])[self.f.project.name],costs(self.f.project.name))
        invoice.cancel()
        self.assertEqual(status(self.f.project.name)['used'],'1000.00')

    def test_native_expense_claim_spending_is_checked_and_counted_once(self):
        from plus_point.budget import status, costs, costs_many
        self.set_spending_budget(500)
        company=frappe.get_doc('Company',self.f.company.name)
        expense_type=insert('Expense Claim Type',expense_type='PP budget '+uuid.uuid4().hex[:8],
            accounts=[dict(company=company.name,default_account=company.default_expense_account)])
        claim=insert('Expense Claim',company=company.name,employee=self.f.employee.name,
            expense_approver='Administrator',approval_status='Approved',project=self.f.project.name,
            payable_account=company.default_payable_account,cost_center=company.cost_center,
            currency=company.default_currency,exchange_rate=1,
            expenses=[dict(expense_date=today(),expense_type=expense_type.name,description='Temporary budget QA',
                amount=600,sanctioned_amount=600,project=self.f.project.name,cost_center=company.cost_center)])
        with self.assertRaises(frappe.ValidationError):
            claim.submit()
        self.assertEqual(frappe.db.get_value('Expense Claim',claim.name,'docstatus'),0)
        claim.reload();claim.expenses[0].amount=500;claim.expenses[0].sanctioned_amount=500
        claim.save();claim.submit()
        self.assertEqual(status(self.f.project.name)['used'],'500.00')
        self.assertEqual(project_summary(self.f.project.name)['other_project_costs'],'500.00')
        self.assertEqual(costs_many([self.f.project.name])[self.f.project.name],costs(self.f.project.name))
        claim.cancel()
        self.assertEqual(status(self.f.project.name)['used'],'0.00')

    def test_budget_preview_rejects_guests_and_invalid_documents(self):
        from plus_point.budget import preview
        with self.assertRaises(frappe.ValidationError):
            preview(dict(doctype='User'))
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            preview(dict(doctype='PP Work Entry',assignment=self.f.assignment.name,units=1))

    def test_dashboard_conditions_have_actions_and_track_setup_progress(self):
        from plus_point.dashboard import overview
        result=overview(self.f.company.name)
        self.assertTrue(any(row['title']=='Set a spending limit' for row in result['conditions']))
        self.assertTrue(all(row['label'] and row['path'].startswith('/desk/') for row in result['conditions']))
        self.set_spending_budget(500)
        self.assertEqual(overview(self.f.company.name)['budgets'][0]['level'],'success')
        self.work(0)
        frappe.db.set_value('PP Site',self.f.site.name,'is_active',0)
        result=overview(self.f.company.name)
        self.assertTrue(any(row['title']=='Add a work site' and row['action']=='new:PP Site' for row in result['conditions']))


    def test_client_activity_uses_approved_days_and_excludes_future_work(self):
        from plus_point.activity import client_activity,day_detail
        self.work('0.5')
        self.work('1',day=add_days(today(),1))
        data=client_activity(self.f.company.name)
        self.assertEqual(data['client_count'],1)
        client=data['clients'][0]
        self.assertEqual(client['active_days'],1)
        self.assertEqual(Decimal(client['units']),Decimal('0.5'))
        self.assertEqual(client['longest_streak'],1)
        self.assertEqual(len(client['days']),91)
        detail=day_detail(self.f.company.name,self.f.customer.name,today())
        self.assertEqual(Decimal(detail['worker_days']),Decimal('0.5'))
        self.assertEqual(detail['rows'][0]['worker'],self.f.employee.employee_name)

    def test_activity_isolates_other_companies_and_rejects_guest(self):
        from plus_point.activity import client_activity,customer_summary,day_detail
        self.work()
        other=fixture('Other activity '+uuid.uuid4().hex[:6])
        self.assertEqual(client_activity(other.company.name)['clients'][0]['active_days'],0)
        with self.assertRaises(frappe.ValidationError):
            day_detail(self.f.company.name,self.f.customer.name,add_days(today(),-91))
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            customer_summary(self.f.customer.name,self.f.company.name)

    def test_section_order_is_personal_validated_and_persists_in_navigation(self):
        import json
        from plus_point.navigation import CUSTOMER_GROUPS,save_section_order,product_navigation
        original=frappe.defaults.get_user_default('pp_section_order_v1')
        order=[name for name,_ in reversed(CUSTOMER_GROUPS)]
        try:
            save_section_order(order)
            self.assertEqual(product_navigation(False)['groups'],order)
            with self.assertRaises(frappe.ValidationError):
                save_section_order([order[0]]*len(order))
        finally:
            frappe.defaults.set_user_default('pp_section_order_v1',original)

    def test_section_dashboard_counts_and_notification_acknowledgement(self):
        from plus_point.sections import overview as section
        from plus_point.dashboard import overview,mark_updates_read
        self.work()
        data=section('Daily work',self.f.company.name)
        self.assertEqual(next(r for r in data['links'] if r['doctype']=='Employee')['count'],1)
        self.assertTrue(overview(self.f.company.name)['notifications'])
        original=frappe.defaults.get_user_default('pp_read_updates_v1')
        try:
            mark_updates_read(self.f.company.name)
            self.assertTrue(all(r['read'] for r in overview(self.f.company.name)['notifications']))
            self.work(0.5,day=add_days(today(),1))
            self.assertTrue(any(not r['read'] for r in overview(self.f.company.name)['notifications']))
            self.assertTrue(overview(self.f.company.name)['conditions'])
        finally:
            frappe.defaults.set_user_default('pp_read_updates_v1',original)

    def test_display_currency_converts_money_without_changing_work_or_books(self):
        from copy import deepcopy
        from unittest.mock import patch
        from plus_point.dashboard import overview
        from plus_point.exchange import present
        self.set_spending_budget(2800)
        self.work('0.5')
        original=overview(self.f.company.name)
        before=deepcopy(original)
        with patch('plus_point.exchange._snapshot',return_value=dict(updated=1700000000,rates={'USD':'1','PKR':'280'})):
            converted=present(original,'USD')
            tiny=present(dict(currency='PKR',wages_unpaid='0.01',contribution='-0.01'),'USD')
        self.assertEqual(tiny['wages_unpaid'],'0.00')
        self.assertEqual(tiny['source_signs']['wages_unpaid'],1)
        self.assertEqual(tiny['source_signs']['contribution'],-1)
        self.assertEqual(converted['currency'],'USD')
        self.assertEqual(converted['earned_revenue'],'5.36')
        self.assertEqual(converted['wages_unpaid'],'3.57')
        self.assertEqual(converted['budgets'][0]['limit'],'10.00')
        self.assertEqual(converted['budgets'][0]['currency'],'USD')
        self.assertEqual(converted['workers'],original['workers'])
        self.assertEqual(converted['activity']['clients'],original['activity']['clients'])
        self.assertEqual(converted['budgets'][0]['level'],original['budgets'][0]['level'])
        self.assertEqual([r['id'] for r in converted['notifications']],[r['id'] for r in original['notifications']])
        self.assertEqual(original,before)
        self.assertEqual(project_summary(self.f.project.name)['labour_cost'],'1000.00')

    def test_currency_rate_failure_keeps_original_amounts_and_currency(self):
        from unittest.mock import patch
        from plus_point.dashboard import overview
        from plus_point.exchange import RateUnavailable
        self.work()
        original=overview(self.f.company.name)
        with patch('plus_point.exchange._snapshot',side_effect=RateUnavailable('Offline')):
            result=overview(self.f.company.name,display_currency='USD')
        self.assertEqual(result['currency'],'PKR')
        self.assertEqual(result['earned_revenue'],original['earned_revenue'])
        self.assertEqual(result['fx']['status'],'unavailable')
        self.assertEqual(result['fx']['requested'],'USD')

    def test_currency_selection_validates_before_request_and_rejects_guest(self):
        from unittest.mock import patch
        from plus_point.dashboard import overview
        with patch('plus_point.exchange._snapshot') as fetch:
            self.assertEqual(overview(self.f.company.name,display_currency='PKR')['fx']['status'],'base')
            with self.assertRaises(frappe.ValidationError):
                overview(self.f.company.name,display_currency='XXX')
            frappe.set_user('Guest')
            with self.assertRaises(frappe.PermissionError):
                overview(self.f.company.name,display_currency='USD')
            fetch.assert_not_called()

    def test_currency_snapshot_rejects_stale_future_and_invalid_rates(self):
        from copy import deepcopy
        from plus_point.exchange import _validate,RateUnavailable,MAX_AGE
        payload=dict(result='success',base_code='USD',time_last_update_unix=1000000,rates={'USD':1,'PKR':280})
        self.assertEqual(_validate(payload,1000001)['rates']['PKR'],'280')
        for age in (-1,MAX_AGE+1):
            with self.assertRaises(RateUnavailable):
                _validate(payload,1000000+age)
        for invalid in (0,-1,'NaN','Infinity'):
            row=deepcopy(payload);row['rates']['PKR']=invalid
            with self.assertRaises(RateUnavailable):
                _validate(row,1000001)

from plus_point.finance import money
