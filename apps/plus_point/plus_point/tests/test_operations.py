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
    employee = insert('Employee', first_name=prefix, gender='Male', date_of_birth='1990-01-01',
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
        frappe.db.savepoint('pp_suite')
        cls.f = fixture()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user('Administrator')
        frappe.db.rollback(save_point='pp_suite')

    def setUp(self):
        frappe.set_user('Administrator')
        frappe.db.savepoint('pp_test')
        self.original_entitlement = frappe.conf.get('pp_entitlement')
        frappe.flags.pp_test_entitlement = None

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.conf.pp_entitlement = self.original_entitlement
        frappe.flags.pp_test_entitlement = None
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


from plus_point.finance import money
