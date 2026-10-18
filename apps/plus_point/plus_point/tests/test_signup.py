"""Real database tests for the local demo request/approval boundary."""
import hashlib
import unittest
from unittest.mock import patch
import uuid

import frappe
from plus_point import signup


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

    def test_guest_payment_admin_approval_and_no_account_or_money_created(self):
        counts={dt:frappe.db.count(dt) for dt in ('User','PP Tenant','Sales Invoice','Payment Entry')}
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
        for dt,count in counts.items():self.assertEqual(frappe.db.count(dt),count,dt)

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

