"""Native invoices/receipts and editable future currency defaults; all fixtures roll back."""
import unittest,uuid
from decimal import Decimal
from unittest.mock import patch
import frappe
from frappe.utils import today
from plus_point.tests.test_operations import fixture,insert
from plus_point import billing
from plus_point.finance import money


class CurrencyBillingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user('Administrator');cls.old=frappe.flags.get('pp_test_entitlement');frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
        frappe.db.savepoint('pp_currency_suite');cls.f=fixture('Currency QA '+uuid.uuid4().hex[:7])
    @classmethod
    def tearDownClass(cls):
        frappe.set_user('Administrator');frappe.db.rollback(save_point='pp_currency_suite');frappe.flags.pp_test_entitlement=cls.old
    def setUp(self):frappe.set_user('Administrator');frappe.db.savepoint('pp_currency_case')
    def tearDown(self):frappe.set_user('Administrator');frappe.db.rollback(save_point='pp_currency_case');frappe.clear_cache()
    def work(self):
        assignment=frappe.get_doc('PP Assignment',self.f.assignment.name);assignment.client_rate=28000;assignment.save()
        work=insert('PP Work Entry',assignment=assignment.name,work_date=today(),units=1,status='Draft');work.status='Approved';work.save();return work
    def invoice(self):
        self.work();frappe.db.set_value('Customer',self.f.customer.name,'default_currency','USD')
        return frappe.get_doc('Sales Invoice',billing.create_invoice(self.f.terms.name,self.f.item.name,exchange_rate=280)['name'])
    def test_editable_preference_preserves_existing_agreements_and_base(self):
        from plus_point.locations import set_company_country
        doc=frappe.get_doc('Company',self.f.company.name);set_company_country(doc,'Saudi Arabia','USD')
        self.assertEqual(doc.country,'Saudi Arabia');self.assertEqual(doc.pp_invoice_currency,'USD');self.assertEqual(doc.default_currency,'PKR')
        self.assertEqual(frappe.db.get_value('PP Contract Terms',self.f.terms.name,'currency'),'PKR')
        set_company_country(doc,'Saudi Arabia');self.assertEqual(doc.pp_invoice_currency,'SAR')
    def test_unused_company_accepts_manual_currency_override(self):
        from plus_point.locations import set_company_country
        doc=insert('Company',company_name='Unused currency QA '+uuid.uuid4().hex[:5],abbr=uuid.uuid4().hex[:5],country='Pakistan',default_currency='PKR')
        set_company_country(doc,'Saudi Arabia','USD');self.assertEqual(doc.default_currency,'USD');self.assertEqual(doc.pp_invoice_currency,'USD')
        self.assertEqual(frappe.db.get_value('Account',doc.default_cash_account,'account_currency'),'USD')
    def test_client_country_currency_override_persists(self):
        from plus_point.clients import create,details
        client=create(dict(customer_name='UAE USD client QA '+uuid.uuid4().hex[:5],contact_name='Sana Malik',email='sana@example.invalid',
            country='United Arab Emirates',city='Dubai',address_line1='12 Exhibition Road',default_currency='USD'))
        self.assertEqual(details(client.name)['default_currency'],'USD')
        self.assertEqual(billing.default_currency(self.f.company.name,client.name),'USD')
    def test_current_quote_is_cross_rate_and_missing_quote_blocks(self):
        with patch('plus_point.exchange._snapshot',return_value=dict(updated=1,rates={'USD':'1','PKR':'280','AED':'3.67','SAR':'3.75'})):
            self.assertEqual(Decimal(billing.quote(self.f.company.name,'USD')['rate']),280)
            self.assertEqual(Decimal(billing.quote(self.f.company.name,'AED')['rate']),Decimal(280)/Decimal('3.67'))
        from plus_point.exchange import RateUnavailable
        with patch('plus_point.exchange._snapshot',side_effect=RateUnavailable()):
            with self.assertRaises(frappe.ValidationError):billing.quote(self.f.company.name,'USD')
    def test_foreign_invoice_posts_native_gl_and_correct_base_outstanding(self):
        from plus_point.api import project_summary
        doc=self.invoice();self.assertEqual(doc.currency,'USD');self.assertEqual(money(doc.net_total),100);self.assertEqual(money(doc.base_net_total),28000)
        doc.submit();self.assertTrue(frappe.db.exists('GL Entry',{'voucher_no':doc.name,'is_cancelled':0}))
        summary=project_summary(self.f.project.name);self.assertEqual(summary['earned_revenue'],'28000.00');self.assertEqual(summary['client_outstanding_gross'],'28000.00')
        self.assertEqual(summary['invoiced_net'],'28000.00')
    def test_usd_receipt_in_foreign_bank_settles_invoice_and_updates_cash(self):
        from plus_point.api import project_summary
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
        doc=self.invoice();doc.submit()
        parent=frappe.db.get_value('Account',self.f.company.default_cash_account,'parent_account')
        bank=insert('Account',account_name='USD bank QA '+uuid.uuid4().hex[:5],parent_account=parent,company=self.f.company.name,
            is_group=0,account_type='Bank',account_currency='USD')
        payment=get_payment_entry('Sales Invoice',doc.name,bank_account=bank.name)
        payment.reference_no='Currency QA';payment.reference_date=today();payment.source_exchange_rate=280;payment.target_exchange_rate=280
        payment.insert();payment.submit();doc.reload();self.assertEqual(money(doc.outstanding_amount),0)
        summary=project_summary(self.f.project.name);self.assertEqual(summary['cash_collected_gross'],'28000.00');self.assertEqual(summary['client_outstanding_gross'],'0.00')
        self.assertEqual(summary['settled_against_invoices_gross'],'28000.00')
    def test_invoice_amount_tamper_and_invalid_rates_are_rejected(self):
        doc=self.invoice();doc.items[0].rate=99
        with self.assertRaises(frappe.ValidationError):doc.save()
        self.assertEqual(frappe.db.get_value('Sales Invoice',doc.name,'net_total'),100)
        for rate in ('nan','inf','0','-1','abc'):
            with self.assertRaises(frappe.ValidationError):billing.create_invoice(self.f.terms.name,self.f.item.name,invoice_currency='USD',exchange_rate=rate)
    def test_quote_and_invoice_options_reject_guest(self):
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):billing.quote(self.f.company.name,'USD')
        with self.assertRaises(frappe.PermissionError):billing.invoice_options(self.f.terms.name)
    def test_fixed_milestone_bills_in_usd_without_rewriting_base_contract(self):
        from plus_point.api import project_summary
        contract=insert('Contract',party_type='Customer',party_name=self.f.customer.name,contract_terms='FX fixed QA',start_date=today())
        terms=insert('PP Contract Terms',contract=contract.name,project=self.f.project.name,billing_model='Fixed',currency='PKR',fixed_amount=28000,status='Active',effective_start=today())
        milestone=insert('PP Milestone',contract_terms=terms.name,milestone_title='Completed event',due_date=today(),amount=28000,status='Approved')
        doc=frappe.get_doc('Sales Invoice',billing.create_invoice(terms.name,self.f.item.name,invoice_currency='USD',exchange_rate=280)['name']);doc.submit();milestone.reload()
        self.assertEqual(milestone.status,'Invoiced');self.assertEqual(money(milestone.amount),28000)
        self.assertEqual(money(doc.net_total),100);self.assertEqual(project_summary(self.f.project.name)['earned_revenue'],'28000.00')
