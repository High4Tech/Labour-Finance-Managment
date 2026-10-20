"""Real database tests for simulated payment and isolated workspace activation."""
import hashlib
import unittest
from unittest.mock import patch
import uuid

import frappe
from plus_point import activation, signup


class SignupTests(unittest.TestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        self.original_user='Administrator'
        frappe.db.savepoint('pp_signup_test')
        self.plan=frappe.get_doc('Subscription Plan','PLUS POINT Local Trial Plan')
        self.plan.pp_public_plan=1;self.plan.save()
        self.email=uuid.uuid4().hex+'@signup-test.example'

    def tearDown(self):
        frappe.set_user(self.original_user)
        frappe.db.rollback(save_point='pp_signup_test')

    def register(self,**overrides):
        return signup.register(**dict(contact_name='QA Person',business_name='QA Business',email=self.email,
            plan=self.plan.name,**overrides))

    def test_guest_payment_approval_queues_one_private_workspace_without_money(self):
        counts={dt:frappe.db.count(dt) for dt in ('User','PP Tenant','Subscription','Customer','Sales Invoice','Payment Entry')}
        frappe.set_user('Guest');request=self.register()
        self.assertEqual(request['status'],'Pending payment')
        doc=frappe.get_doc('PP Signup Request',request['reference'])
        self.assertEqual(doc.token_hash,hashlib.sha256(request['token'].encode()).hexdigest())
        self.assertNotEqual(doc.token_hash,request['token'])
        args=dict(reference=request['reference'],token=request['token'])
        self.assertEqual(signup.simulate_payment(**args)['status'],'Awaiting approval')
        self.assertEqual(signup.simulate_payment(**args)['status'],'Awaiting approval')
        with self.assertRaises(frappe.PermissionError):signup.review(request['reference'],'Approved')
        frappe.set_user('Administrator');signup.review(request['reference'],'Approved')
        frappe.set_user('Guest');state=signup.status(**args)
        self.assertEqual(state['status'],'Approved');self.assertNotIn('token_hash',state);self.assertNotIn('email',state)
        frappe.set_user('Administrator')
        self.assertEqual(state['activation'],'Queued')
        self.assertEqual(state['login_email'],self.email)
        self.assertNotIn('setup_url',state)
        for dt,count in counts.items():
            self.assertEqual(frappe.db.count(dt),count+int(dt in ('PP Tenant','Subscription','Customer')),dt)
        doc=frappe.get_doc('PP Signup Request',request['reference'])
        self.assertEqual(doc.workspace_site,activation.hostname(doc))
        self.assertEqual(activation.queue(doc.name)['workspace_url'],state['workspace_url'])
        for dt in ('PP Tenant','Subscription','Customer'):self.assertEqual(frappe.db.count(dt),counts[dt]+1)
        sub=frappe.get_doc('Subscription',doc.workspace_subscription)
        self.assertEqual(sub.pp_demo_workspace,1)
        self.assertFalse(sub.can_generate_new_invoice())
        with self.assertRaises(frappe.ValidationError):sub.generate_invoice()
        with self.assertRaises(frappe.ValidationError):sub.create_invoice()
        self.assertEqual(frappe.db.count('Sales Invoice'),counts['Sales Invoice'])

    def test_quote_is_server_derived_and_preserved_after_plan_price_changes(self):
        request=self.register();self.plan.cost+=100;self.plan.save()
        doc=frappe.get_doc('PP Signup Request',request['reference'])
        self.assertEqual(doc.amount,float(request['amount']))
        self.assertNotEqual(doc.amount,self.plan.cost)

    def test_hidden_plan_and_invalid_input_are_rejected(self):
        self.plan.pp_public_plan=0;self.plan.save()
        with self.assertRaises(frappe.ValidationError):self.register()
        self.plan.pp_public_plan=1;self.plan.save()
        for key,value in [('email','invalid'),('contact_name',''),('business_name','x'*141),('website','bot')]:
            values=dict(contact_name='QA',business_name='QA',email=self.email,plan=self.plan.name);values[key]=value
            with self.assertRaises(frappe.ValidationError):signup.register(**values)

    def test_wrong_token_and_generic_guest_document_access_are_rejected(self):
        request=self.register();frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):signup.status(request['reference'],'0'*64)
        with self.assertRaises(frappe.PermissionError):frappe.get_doc('PP Signup Request',request['reference']).check_permission('read')

    def test_review_requires_payment_and_cannot_be_replayed(self):
        request=self.register()
        with self.assertRaises(frappe.ValidationError):signup.review(request['reference'],'Approved')
        signup.simulate_payment(request['reference'],request['token']);signup.review(request['reference'],'Rejected')
        with self.assertRaises(frappe.ValidationError):signup.review(request['reference'],'Approved')
        self.assertEqual(signup.simulate_payment(request['reference'],request['token'])['status'],'Rejected')

    def test_customer_site_cannot_register_or_read_the_platform_flow(self):
        with patch.dict(frappe.conf,{'pp_control_plane':False}):
            with self.assertRaises(frappe.PermissionError):self.register()
            with self.assertRaises(frappe.PermissionError):signup.plans()

    def test_activation_requires_platform_role_and_approved_payment(self):
        request=self.register()
        with self.assertRaises(frappe.ValidationError):activation.queue(request['reference'])
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):activation.queue(request['reference'])
        with self.assertRaises(frappe.PermissionError):activation.account_details(request['reference'])
        with self.assertRaises(frappe.PermissionError):signup.refresh_password_setup(request['reference'],'0'*64)

    def test_direct_identity_status_and_workspace_edits_are_rejected(self):
        request=self.register()
        for key,value in [('email','other@example.invalid'),('review_status','Approved'),('workspace_site','other.localhost')]:
            doc=frappe.get_doc('PP Signup Request',request['reference']);doc.set(key,value)
            with self.assertRaises(frappe.ValidationError):doc.save()

    def test_alias_validation_and_separate_pending_requests(self):
        for alias in ('a','Administrator','Guest','spaces here','x'*65):
            with self.assertRaises(frappe.ValidationError):self.register(login_username=alias)
        first=self.register(login_username='qa.business')
        second=self.register(login_username='qa.business')
        self.assertNotEqual(first['reference'],second['reference'])
        self.assertEqual(first['login_username'],'qa.business')

    def test_expired_setup_is_hidden_and_only_private_owner_can_refresh(self):
        from frappe.utils import add_to_date,now_datetime
        from frappe.utils.password import set_encrypted_password,remove_encrypted_password
        request=self.register();signup.simulate_payment(request['reference'],request['token'])
        signup.review(request['reference'],'Approved')
        doc=frappe.get_doc('PP Signup Request',request['reference'])
        link=f'http://{doc.workspace_site}:8000/update-password?key=privateTestKey'
        try:
            set_encrypted_password(doc.doctype,doc.name,link,'setup_secret')
            doc.setup_secret='********';doc.activation_status='Ready';doc.setup_expires_on=add_to_date(now_datetime(),seconds=300)
            doc.flags.signup_activation=True;doc.save()
            self.assertEqual(activation.account_details(doc.name)['setup_url'],link)
            frappe.set_user('Guest')
            self.assertEqual(signup.status(doc.name,request['token'])['setup_url'],link)
            with self.assertRaises(frappe.PermissionError):signup.status(doc.name,'0'*64)
            frappe.set_user('Administrator')
            doc.setup_expires_on=add_to_date(now_datetime(),seconds=-60);doc.save()
            self.assertNotIn('setup_url',activation.account_details(doc.name))
            frappe.set_user('Guest')
            self.assertEqual(signup.refresh_password_setup(doc.name,request['token'])['activation'],'Queued')
        finally:
            frappe.set_user('Administrator');remove_encrypted_password(doc.doctype,doc.name,'setup_secret')

