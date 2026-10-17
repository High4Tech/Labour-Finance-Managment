"""Local operator test helpers. No functions in this module are whitelisted."""
import frappe


def temporary_token():
    if not frappe.conf.get('allow_tests') or not frappe.local.site.endswith('.localhost'):
        frappe.throw('Test helper only supports test-enabled localhost sites')
    from frappe.core.doctype.user.user import generate_keys
    keys = generate_keys('Administrator')
    frappe.db.commit()
    from frappe.utils.password import get_decrypted_password
    # Read persisted values, not stale document/database value-cache state.
    key = frappe.db.sql('select api_key from tabUser where name=%s', ('Administrator',))[0][0]
    secret = get_decrypted_password('User', 'Administrator', 'api_secret')
    return dict(api_key=key, api_secret=secret)


def current_entitlement():
    if not frappe.conf.get('allow_tests') or not frappe.local.site.endswith('.localhost'):
        raise RuntimeError('Local test-enabled site required')
    return frappe.conf.get('pp_entitlement') or {}


def run_operations():
    if not frappe.conf.get('allow_tests'):
        raise RuntimeError('Tests are disabled')
    import unittest
    from plus_point.tests.test_operations import OperationsTests
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(OperationsTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError('PLUS POINT database regression suite failed')
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors))


def seed_demo():
    if not frappe.conf.get('allow_tests') or not frappe.local.site.endswith('.localhost'):
        raise RuntimeError('Demo seed only supports local test-enabled sites')
    from plus_point.tests.test_operations import fixture, insert
    from frappe.utils import today
    if frappe.db.exists('Company', 'PLUS POINT Demo'):
        _finish_demo_setup()
        return 'Existing demo preserved'
    f = fixture('PLUS POINT Demo')
    work = insert('PP Work Entry', assignment=f.assignment.name, work_date=today(), units=1)
    work.status = 'Approved'
    work.save()
    fixed_contract = insert('Contract', party_type='Customer', party_name=f.customer.name,
        contract_terms='Demo fixed-price construction agreement', start_date=today())
    terms = insert('PP Contract Terms', contract=fixed_contract.name, project=f.project.name,
        billing_model='Fixed', fixed_amount=100000, currency='PKR', status='Active', effective_start=today())
    insert('PP Milestone', contract_terms=terms.name, milestone_title='Demo mobilization', amount=25000, status='Approved')
    frappe.db.set_single_value('Global Defaults', 'default_company', f.company.name)
    frappe.defaults.set_global_default('company', f.company.name)
    _finish_demo_setup()
    frappe.db.commit()
    return dict(project=f.project.name, site=f.site.name, employee=f.employee.name,
                note='Clearly labelled local demonstration data; no production business records')


def seed_platform_demo():
    from plus_point.platform import require_platform, export_entitlement
    require_platform()
    if not frappe.conf.get('allow_tests'):
        raise RuntimeError('Test-enabled local platform required')
    from plus_point.tests.test_operations import insert
    from frappe.utils import today, add_days
    if frappe.db.exists('PP Tenant', 'qa.localhost'):
        _finish_demo_setup()
        return export_entitlement('qa.localhost')
    company = insert('Company', company_name='High4Tech Local Demo', abbr='H4TLD', country='Pakistan', default_currency='PKR')
    customer = insert('Customer', customer_name='PLUS POINT Trial Organization', customer_type='Company',
        customer_group='Commercial', territory='All Territories')
    item = insert('Item', item_code='PLUS POINT Local Subscription', item_name='PLUS POINT Local Subscription',
        is_stock_item=0, stock_uom='Nos', item_group='Services')
    plan = insert('Subscription Plan', plan_name='PLUS POINT Local Trial Plan', currency='PKR', item=item.name,
        price_determination='Fixed Rate', cost=1000, billing_interval='Month', billing_interval_count=1)
    subscription = insert('Subscription', party_type='Customer', party=customer.name, company=company.name,
        start_date=today(), trial_period_start=today(), trial_period_end=add_days(today(), 14),
        plans=[dict(plan=plan.name, qty=1)], generate_invoice_at='End of the current subscription period')
    insert('PP Tenant', organization_name='PLUS POINT Trial Organization', site_hostname='qa.localhost',
        owner_email='local-trial@example.invalid', subscription=subscription.name, worker_limit=10, user_limit=3, site_limit=5)
    frappe.defaults.set_global_default('company', company.name)
    frappe.db.set_single_value('Global Defaults', 'default_company', company.name)
    _finish_demo_setup()
    frappe.db.commit()
    return export_entitlement('qa.localhost')


def _finish_demo_setup():
    from frappe.desk.page.setup_wizard.setup_wizard import (
        disable_future_access, enable_setup_wizard_complete,
    )
    for app in frappe.get_installed_apps():
        enable_setup_wizard_complete(app)
    # Complete the native post-setup transition too. Leaving desktop:home_page
    # on setup-wizard makes All apps repeatedly reload an already completed wizard.
    disable_future_access()
    frappe.db.set_single_value('System Settings', {
        'setup_complete': 1, 'time_zone': 'Asia/Karachi', 'country': 'Pakistan',
        'currency': 'PKR', 'language': 'en', 'enable_onboarding': 0,
    })
    frappe.db.commit()
    frappe.clear_cache()


def cleanup_http_fixtures():
    if not frappe.conf.get('allow_tests') or not frappe.local.site.endswith('.localhost'):
        raise RuntimeError('Local test site required')
    import re
    count = 0
    for row in frappe.get_all('ToDo', filters={'description': ['like', 'PLUS POINT HTTP QA %']}, fields=['name', 'description']):
        if re.fullmatch(r'PLUS POINT HTTP QA [0-9a-f]{32}( updated| tenant B)?', row.description):
            frappe.delete_doc('ToDo', row.name)
            count += 1
    for row in frappe.get_all('PP Work Entry', filters={'status': 'Draft', 'remarks': ['like', 'PLUS POINT HTTP QA %']}, fields=['name', 'remarks']):
        if re.fullmatch(r'PLUS POINT HTTP QA [0-9a-f]{32}', row.remarks):
            frappe.delete_doc('PP Work Entry', row.name)
            count += 1
    frappe.db.commit()
    return dict(temporary_todos_removed=count)


def run_platform_finance():
    """Real native plan → subscription → posted invoice → receipt; all rolled back."""
    from plus_point.platform import require_platform
    require_platform()
    if not frappe.conf.get('allow_tests') or not frappe.local.site.endswith('.localhost'):
        raise RuntimeError('Local test-enabled platform required')
    import uuid
    from decimal import Decimal
    from frappe.utils import today, add_days
    from plus_point.tests.test_operations import insert
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    marker='PLUS POINT software finance QA '+uuid.uuid4().hex[:8]
    original_mute=frappe.flags.mute_emails
    frappe.flags.mute_emails=True
    try:
        subscription_name=frappe.db.get_value('PP Tenant',{},'subscription')
        company_name=frappe.db.get_value('Subscription',subscription_name,'company')
        company=frappe.get_doc('Company',company_name)
        customer=insert('Customer',customer_name=marker,customer_type='Company',customer_group='Commercial',territory='All Territories')
        item=insert('Item',item_code=marker,item_name=marker,item_group='Services',stock_uom='Nos',is_stock_item=0)
        plan=insert('Subscription Plan',plan_name=marker,currency=company.default_currency,item=item.name,
            price_determination='Fixed Rate',cost=1250,billing_interval='Month',billing_interval_count=1)
        start=add_days(today(),1)
        subscription=insert('Subscription',party_type='Customer',party=customer.name,company=company.name,
            start_date=start,plans=[dict(plan=plan.name,qty=1)],submit_invoice=1,
            generate_invoice_at='Beginning of the current subscription period')
        invoice=subscription.generate_invoice(from_date=subscription.current_invoice_start,
            to_date=subscription.current_invoice_end,posting_date=start)
        if invoice.docstatus==0:
            invoice.submit()
        assert Decimal(str(invoice.base_grand_total))==Decimal('1250.00'), (
            f'Expected 1250; total={invoice.base_grand_total}, net={invoice.base_net_total}, '
            f'rows={[(row.rate,row.qty,row.amount) for row in invoice.items]}, '
            f'period={subscription.current_invoice_start}..{subscription.current_invoice_end}')
        assert frappe.db.exists('GL Entry',{'voucher_type':'Sales Invoice','voucher_no':invoice.name,'is_cancelled':0})
        payment=get_payment_entry('Sales Invoice',invoice.name,bank_account=company.default_cash_account)
        payment.posting_date=start
        payment.reference_no='PLUS POINT software finance QA'
        payment.reference_date=start
        payment.insert();payment.submit();invoice.reload()
        assert Decimal(str(invoice.outstanding_amount))==0
        assert frappe.db.exists('GL Entry',{'voucher_type':'Payment Entry','voucher_no':payment.name,'is_cancelled':0})
        return dict(monthly_plan=True,subscription_invoice_posted=True,price='1250.00',receipt_posted=True,client_balance='0.00',fixtures='rolled back')
    finally:
        frappe.db.rollback()
        frappe.flags.mute_emails=original_mute


def restore_support_test_setting(value):
    if (getattr(frappe.local, 'request', None) or not frappe.conf.get('allow_tests')
            or frappe.local.site != 'qa.localhost' or int(value) not in (0, 1)):
        raise RuntimeError('Local QA operator required')
    frappe.db.set_single_value('System Settings', 'allow_login_using_user_name', int(value))
    frappe.clear_cache()
    frappe.db.commit()
    return True


def seed_platform_customer_demo():
    """Register the existing MVP demo as a software customer, without fake sales."""
    from plus_point.platform import require_platform
    require_platform()
    if not frappe.conf.get('allow_tests') or frappe.local.site != 'platform.localhost':
        raise RuntimeError('Local test-enabled platform required')
    base=frappe.get_doc('PP Tenant', 'qa.localhost')
    existing=frappe.get_doc('Subscription', base.subscription)
    if not frappe.db.get_single_value('Global Defaults', 'default_company'):
        frappe.db.set_single_value('Global Defaults', 'default_company', existing.company)
        frappe.defaults.set_global_default('company', existing.company)
        frappe.db.commit()
    if frappe.db.exists('PP Tenant', 'demo.localhost'):
        return dict(customer_site='demo.localhost', existing=True)
    from plus_point.tests.test_operations import insert
    from frappe.utils import today, add_days
    customer=insert('Customer', customer_name='PLUS POINT Demo', customer_type='Company',
                    customer_group='Commercial', territory='All Territories')
    subscription=insert('Subscription', party_type='Customer', party=customer.name,
        company=existing.company, start_date=today(), trial_period_start=today(), trial_period_end=add_days(today(),14),
        plans=[dict(plan=existing.plans[0].plan,qty=1)], generate_invoice_at='End of the current subscription period')
    insert('PP Tenant', organization_name='PLUS POINT Demo', site_hostname='demo.localhost',
        owner_email='example@email.com', subscription=subscription.name, worker_limit=10, user_limit=3, site_limit=5)
    frappe.db.commit()
    return dict(customer_site='demo.localhost', status=subscription.status, sales_recorded=False)


def cleanup_support_test_fixtures():
    """Recover only this harness's strictly named temporary records after failure."""
    if getattr(frappe.local, 'request', None) or not frappe.conf.get('allow_tests') or frappe.local.site != 'platform.localhost':
        raise RuntimeError('Local platform QA operator required')
    import re
    count=0
    for row in frappe.get_all('PP Support Request', fields=['name', 'target_email', 'status']):
        if re.fullmatch(r'pp-support-qa-[0-9a-f]{10}@example\.invalid', row.target_email or '') and row.status in ('Completed', 'Failed'):
            frappe.delete_doc('PP Support Request', row.name)
            count+=1
    for name in frappe.get_all('Subscription Plan', pluck='name'):
        if re.fullmatch(r'pp-support-qa-[0-9a-f]{10}', name):
            frappe.delete_doc('Subscription Plan', name)
            count+=1
    frappe.db.commit()
    return dict(temporary_records_removed=count)
