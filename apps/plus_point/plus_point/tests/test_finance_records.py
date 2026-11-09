"""Accounting form contract against installed ERPNext; all fixtures roll back."""
import unittest
from unittest.mock import patch
import frappe
from frappe.utils import today
from plus_point.tests.test_operations import fixture, insert
from plus_point import finance_records as records


class FinanceRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user('Administrator')
        cls.old = frappe.flags.get('pp_test_entitlement')
        frappe.flags.pp_test_entitlement = {'valid_until': '2099-12-31'}
        frappe.db.savepoint('react_finance_suite')
        cls.f = fixture()
        cls.scope = patch('plus_point.event_setup.companies', return_value=[cls.f.company])
        cls.scope.start()

    @classmethod
    def tearDownClass(cls):
        cls.scope.stop()
        frappe.set_user('Administrator')
        frappe.db.rollback(save_point='react_finance_suite')
        frappe.flags.pp_test_entitlement = cls.old

    def setUp(self):
        frappe.set_user('Administrator')
        frappe.db.savepoint('react_finance_case')

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback(save_point='react_finance_case')

    def invoice(self):
        result = records.save('Sales Invoice', dict(customer=self.f.customer.name,
            posting_date=today(), due_date=today(), project=self.f.project.name,
            currency='PKR', conversion_rate=1, items=[dict(item_code=self.f.item.name, qty=2, rate=150)]))
        return frappe.get_doc('Sales Invoice', result['name'])

    def test_four_forms_have_native_schema_and_permissions(self):
        for doctype, names in records.FIELDS.items():
            data = records.detail(doctype)
            self.assertEqual(data['company'], self.f.company.name)
            self.assertTrue(data['can_write'])
            self.assertTrue(data['fields'])
            self.assertTrue(set(f['key'] for f in data['fields']).issubset(names))

    def test_new_payment_keeps_worker_loan_context_without_saving(self):
        count = frappe.db.count('Payment Entry', {'company': self.f.company.name})
        data = records.detail('Payment Entry', defaults=dict(company=self.f.company.name,
            party_type='Employee', party=self.f.employee.name, payment_type='Pay',
            paid_amount=250, received_amount=250, posting_date=today()))
        self.assertEqual(data['values']['party'], self.f.employee.name)
        self.assertEqual(data['values']['paid_amount'], 250)
        self.assertEqual(frappe.db.count('Payment Entry', {'company': self.f.company.name}), count)

    def test_advanced_new_allocations_are_flagged_instead_of_silently_dropped(self):
        data = records.detail('Payment Entry', defaults={'references': [dict(reference_name='Invoice context')]})
        self.assertEqual(data['advanced'], ['references'])

    def test_invoice_create_calculates_native_totals(self):
        invoice = self.invoice()
        self.assertEqual(invoice.company, self.f.company.name)
        self.assertEqual(invoice.grand_total, 300)
        self.assertEqual(invoice.docstatus, 0)

    def test_edit_preserves_unexposed_accounting_fields_and_child_identity(self):
        invoice = self.invoice()
        invoice.po_no = 'Customer PO kept'
        invoice.save()
        item = invoice.items[0]
        records.save('Sales Invoice', dict(remarks='Updated', items=[dict(name=item.name,
            item_code=item.item_code, qty=3, rate=150)]), invoice.name, str(invoice.modified))
        invoice.reload()
        self.assertEqual(invoice.po_no, 'Customer PO kept')
        self.assertEqual(invoice.items[0].name, item.name)
        self.assertEqual(invoice.grand_total, 450)

    def test_conflict_rejects_stale_save(self):
        invoice = self.invoice()
        with self.assertRaises(frappe.ValidationError):
            records.save('Sales Invoice', {'remarks': 'stale'}, invoice.name, '2000-01-01')
        self.assertNotEqual(frappe.db.get_value('Sales Invoice', invoice.name, 'remarks'), 'stale')

    def test_company_and_unlisted_fields_cannot_be_injected(self):
        with self.assertRaises(frappe.PermissionError):
            records.save('Sales Invoice', {'company': 'Other company'})
        with self.assertRaises(frappe.PermissionError):
            records.detail('Journal Entry')

    def test_unknown_child_cannot_replace_another_document_line(self):
        invoice = self.invoice()
        with self.assertRaises(frappe.ValidationError):
            records.save('Sales Invoice', {'items': [dict(name='not-this-invoice', qty=99)]},
                invoice.name, str(invoice.modified))

    def test_submit_posts_and_then_blocks_editing(self):
        invoice = self.invoice()
        records.submit('Sales Invoice', invoice.name, str(invoice.modified))
        invoice.reload()
        self.assertEqual(invoice.docstatus, 1)
        self.assertTrue(frappe.db.exists('GL Entry', {'voucher_type': 'Sales Invoice', 'voucher_no': invoice.name}))
        with self.assertRaises(frappe.ValidationError):
            records.save('Sales Invoice', {'remarks': 'change posted'}, invoice.name, str(invoice.modified))

    def test_worker_payment_link_uses_native_paid_amount_and_outstanding_guard(self):
        work=insert('PP Work Entry',assignment=self.f.assignment.name,work_date=today(),units=1,status='Draft')
        work.status='Approved';work.save()
        company=frappe.get_doc('Company',self.f.company.name)
        payment=insert('Payment Entry',payment_type='Pay',company=company.name,party_type='Employee',
            party=self.f.employee.name,project=self.f.project.name,paid_from=company.default_cash_account,
            paid_to=company.default_payable_account,paid_amount=1000,received_amount=1000,
            source_exchange_rate=1,target_exchange_rate=1,reference_no='QA React settlement',reference_date=today())
        payment.submit()
        values=dict(employee=self.f.employee.name,project=self.f.project.name,payment_entry=payment.name)
        name=records.save('PP Wage Settlement',values)['name']
        data=records.detail('PP Wage Settlement',name)
        self.assertEqual(data['totals']['amount'],1000)
        records.submit('PP Wage Settlement',name,data['modified'])
        self.assertEqual(frappe.db.get_value('PP Wage Settlement',name,'docstatus'),1)
        with self.assertRaises(frappe.PermissionError):
            records.save('PP Wage Settlement',dict(values,amount=1))
        with self.assertRaises(frappe.PermissionError):
            with patch('plus_point.finance_records.company_scope',return_value=frappe._dict(name='Other business')):
                records.detail('PP Wage Settlement',name)

    def test_cash_receipt_posts_using_native_accounts(self):
        account = records.payment_accounts('Customer', self.f.customer.name, 'Receive', today())['account']
        cash = frappe.get_list('Account', filters={'company': self.f.company.name,
            'account_type': 'Cash', 'is_group': 0}, pluck='name', limit_page_length=1)[0]
        result = records.save('Payment Entry', dict(payment_type='Receive', posting_date=today(),
            party_type='Customer', party=self.f.customer.name, paid_from=account, paid_to=cash,
            paid_amount=100, received_amount=100, source_exchange_rate=1, target_exchange_rate=1))
        doc = frappe.get_doc('Payment Entry', result['name'])
        records.submit('Payment Entry', doc.name, str(doc.modified))
        self.assertEqual(frappe.db.get_value('Payment Entry', doc.name, 'docstatus'), 1)

    def test_purchase_draft_uses_supplier_and_native_item_defaults(self):
        supplier = insert('Supplier', supplier_name=self.f.company.name, supplier_group='All Supplier Groups', supplier_type='Company')
        result = records.save('Purchase Invoice', dict(supplier=supplier.name, posting_date=today(),
            currency='PKR', conversion_rate=1, items=[dict(item_code=self.f.item.name, qty=2, rate=50)]))
        self.assertEqual(frappe.db.get_value('Purchase Invoice', result['name'], 'grand_total'), 100)

    def test_guest_cannot_read_or_create_financial_records(self):
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            records.detail('Payment Entry')

    def test_currency_choices_are_scoped_to_native_accounts(self):
        cash = frappe.get_list('Account', filters={'company': self.f.company.name,
            'account_type': 'Cash', 'is_group': 0}, pluck='name', limit_page_length=1)[0]
        self.assertEqual(records.payment_currencies(cash, cash), {'source': 'PKR', 'target': 'PKR'})
        with self.assertRaises(frappe.PermissionError):
            records.payment_currencies('not-an-accessible-account')

    def test_finance_lists_always_include_the_selected_company(self):
        from plus_point.finance_hub import list_records
        with patch('frappe.get_list', return_value=[]) as native:
            for doctype in ('Payment Entry','Sales Invoice','Purchase Invoice','Expense Claim'):
                list_records(doctype, search='QA')
                self.assertEqual(native.call_args.kwargs['filters']['company'], self.f.company.name)
                self.assertEqual(native.call_args.kwargs['limit_page_length'], 21)

    def test_finance_lists_keep_contextual_project_and_native_child_filter(self):
        from plus_point.finance_hub import list_records
        invoice = self.invoice()
        for doctype in ('Payment Entry','Sales Invoice','Purchase Invoice','Expense Claim'):
            result = list_records(doctype, project=self.f.project.name)
            self.assertEqual(result['project']['name'], self.f.project.name)
            if doctype == 'Sales Invoice':
                self.assertIn(invoice.name, [row.name for row in result['rows']])
        with self.assertRaises(frappe.DoesNotExistError):
            list_records('Sales Invoice', project='missing-react-project')

    def test_advanced_unsaved_edits_return_without_writing_or_allowing_submit(self):
        doc = self.invoice()
        data = records.detail('Sales Invoice', doc.name, defaults={'remarks': 'Unposted edit'})
        self.assertEqual(data['values']['remarks'], 'Unposted edit')
        self.assertFalse(data['can_submit'])
        self.assertNotEqual(frappe.db.get_value('Sales Invoice', doc.name, 'remarks'), 'Unposted edit')

    def test_pdf_preview_uses_native_print_without_creating_attachments(self):
        import base64
        doc = self.invoice()
        count = frappe.db.count('File')
        with patch('frappe.get_print', return_value=b'%PDF-1.4 QA') as native:
            result = records.print_data('Sales Invoice', doc.name)
            native.assert_called_once_with('Sales Invoice', doc.name, as_pdf=True)
        self.assertEqual(base64.b64decode(result['content']), b'%PDF-1.4 QA')
        self.assertEqual(frappe.db.count('File'), count)

    def test_worker_reimbursement_can_be_created_and_reviewed(self):
        expense = frappe.get_list('Account', filters={'company': self.f.company.name,
            'root_type': 'Expense', 'is_group': 0}, pluck='name', limit_page_length=1)[0]
        category = insert('Expense Claim Type', expense_type=self.f.company.name,
            accounts=[dict(company=self.f.company.name, default_account=expense)])
        result = records.save('Expense Claim', dict(employee=self.f.employee.name,
            posting_date=today(), expenses=[dict(expense_date=today(), expense_type=category.name,
                description='QA travel', amount=125, sanctioned_amount=125, project=self.f.project.name)]))
        data = records.detail('Expense Claim', result['name'])
        self.assertEqual(data['totals']['total_claimed_amount'], 125)
        self.assertEqual(data['docstatus'], 0)
        from plus_point.finance_hub import list_records
        self.assertIn(result['name'], [row.name for row in list_records(
            'Expense Claim', project=self.f.project.name)['rows']])

    def test_equipment_edit_keeps_native_stock_and_reservation_protection(self):
        from plus_point import resources
        item = insert('Item', item_code=self.f.company.name + ' stock', item_name='Event barriers',
            item_group='Services', stock_uom='Nos', is_stock_item=1)
        resources.update_profile('equipment', item.name, dict(item_name='Safety barriers', stock_uom='Nos'))
        self.assertEqual(frappe.db.get_value('Item', item.name, 'item_name'), 'Safety barriers')
        warehouse = frappe.db.get_value('Warehouse', {'company': self.f.company.name, 'is_group': 0}, 'name')
        resources.count_stock(warehouse, item.name, 10, 50, today())
        insert('PP Event Plan', event_name='Resource React QA', project=self.f.project.name,
            contract_terms=self.f.terms.name, start_date=today(), end_date=today(), wage_rate=0, client_rate=3000,
            staffing=[dict(site=self.f.site.name, phase='Event', start_date=today(), end_date=today(), workers_required=1)])
        resources.save_booking(self.f.project.name, 'equipment', dict(site=self.f.site.name,
            item=item.name, warehouse=warehouse, quantity=4, start_date=today(), end_date=today(), status='Planned'))
        with self.assertRaises(frappe.ValidationError):
            resources.update_profile('equipment', item.name, {'disabled': 1})
        with self.assertRaises(frappe.ValidationError):
            resources.update_stock(warehouse, [dict(item=item.name, quantity=3, expected_quantity=10)])


def run():
    if frappe.local.site != 'qa.localhost' or not frappe.conf.get('allow_tests') or getattr(frappe.local, 'request', None):
        raise RuntimeError('Local QA operator only')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FinanceRecordTests))
    if not result.wasSuccessful():
        raise RuntimeError('React accounting regression tests failed')
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors))
