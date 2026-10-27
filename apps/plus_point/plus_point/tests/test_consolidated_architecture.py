"""Client bearer grants, honest event lifecycle and the consolidated navigation."""
import unittest
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs
import frappe
from frappe.utils import today,add_days
from plus_point.tests import test_hierarchy as h
from plus_point import operations as op,agreement_events as ae,drafts,signing,client_portal as portal


class ConsolidatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):h.HierarchyTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):h.HierarchyTests.tearDownClass.__func__(cls)
    setUp=h.HierarchyTests.setUp
    tearDown=h.HierarchyTests.tearDown
    agreement=h.HierarchyTests.agreement

    def event(self,a,title='Client event'):
        return ae.create_event(agreement=a['name'],event_name=title,start_date=today(),end_date=add_days(today(),2))

    def token(self,result):return parse_qs(urlparse(result['url']).query)['token'][0]

    def test_copy_reuses_current_encrypted_grant_and_never_creates_a_pdf(self):
        a=self.agreement();before=frappe.db.count('File')
        one=portal.link(agreement=a['name']);two=portal.link(agreement=a['name'])
        self.assertEqual(one['url'],two['url']);self.assertEqual(frappe.db.count('File'),before)
        share=frappe.get_doc('PP Agreement Share',one['name'])
        self.assertEqual(share.token_hash,signing.digest(self.token(one)))
        self.assertNotEqual(frappe.db.get_value('PP Agreement Share',share.name,'access_token'),self.token(one))
        from frappe.utils.password import get_decrypted_password
        self.assertEqual(get_decrypted_password('PP Agreement Share',share.name,'access_token'),self.token(one))

    def test_guest_reads_only_scoped_progress_and_can_sign_frozen_agreement(self):
        a=self.agreement();one=self.event(a);other=self.agreement('Unrelated agreement');self.event(other,'Hidden other client work')
        worker=frappe.get_doc('Employee',self.worker.name);worker.pp_daily_rate=100;worker.save()
        op.auto_assign(one['name']);grant=portal.link(agreement=a['name']);token=self.token(grant)
        frappe.set_user('Guest')
        data=signing.review(token)
        self.assertEqual([e['title'] for e in data['events']],['Client event'])
        encoded=frappe.as_json(data['events'])
        for secret in ('wage_rate','employee','notes','budget','profit','loan','email','file_url'):
            self.assertNotIn(secret,encoded)
        self.assertGreater(data['events'][0]['assigned_worker_days'],0)
        signed=signing.accept(token,'Client Representative','client@example.invalid',1)
        self.assertTrue(signed['signed']);self.assertEqual(signing.review(token)['status'],'Signed')

    def test_event_link_limits_progress_to_one_occurrence(self):
        a=self.agreement();one=self.event(a,'First occurrence');self.event(a,'Second occurrence')
        grant=portal.link(event=one['name']);frappe.set_user('Guest')
        data=signing.review(self.token(grant));self.assertEqual([e['title'] for e in data['events']],['First occurrence'])

    def test_revoked_expired_and_invalid_portal_links_are_denied(self):
        a=self.agreement();grant=portal.link(agreement=a['name']);token=self.token(grant)
        frappe.db.set_value('PP Agreement Share',grant['name'],'expires',add_days(today(),-1))
        for value in (token,'x'*54):
            with self.assertRaises(frappe.PermissionError):signing.review(value)
        frappe.db.set_value('PP Agreement Share',grant['name'],{'expires':add_days(today(),3),'status':'Revoked'})
        with self.assertRaises(frappe.PermissionError):signing.review(token)

    def test_guest_and_other_company_cannot_create_portal_links(self):
        a=self.agreement();event=self.event(a)
        with patch('plus_point.operations.company',return_value=frappe._dict(name='Other company')):
            with self.assertRaises((frappe.PermissionError,frappe.ValidationError)):portal.link(agreement=a['name'])
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):portal.link(event=event['name'])

    def test_operational_draft_is_not_upcoming_or_duplicated_by_edit_draft(self):
        a=self.agreement();d=drafts.event_for_agreement(a['name'])
        result=drafts.configure_event(d['name'],dict(event_name='Unfinished event',action='Now',new_occurrence=1))
        data=op.plan(result['event']);self.assertEqual(data['event_status'],'Draft')
        edit=drafts.save('Event',dict(record=data['name'],event_name='Unsaved edit'),client_key='edit-lifecycle')
        from plus_point.planning_list import rows
        listed=rows('PP Event Plan',fields=['name','event_name'],planning_status='Draft')
        self.assertEqual(listed['total'],1);self.assertEqual(listed['rows'][0].planning_state,'Draft')
        self.assertEqual(listed['rows'][0].pp_draft_name,edit['name'])
        self.assertNotIn('draft:'+edit['name'],[r.name for r in listed['rows']])
        grant=portal.link(agreement=a['name']);self.assertEqual(signing.review(self.token(grant))['events'],[])
        op.save_project(data['name'],dict(complete=1))
        self.assertEqual(op.plan(data['name'])['planning_state'],'Ready')
        self.assertEqual(len(signing.review(self.token(grant))['events']),1)

    def test_empty_operational_draft_cannot_finish_until_requirements_exist(self):
        result=ae.create_event(customer=self.f.customer.name,event_name='Incomplete job',start_date=today(),end_date=today())
        frappe.db.set_value('PP Event Plan',result['name'],'planning_state','Draft')
        with self.assertRaises(frappe.ValidationError):op.save_project(result['name'],dict(complete=1))
        self.assertEqual(frappe.db.get_value('PP Event Plan',result['name'],'planning_state'),'Draft')

    def test_date_status_only_applies_after_explicit_completion(self):
        from plus_point.events import lifecycle
        future=frappe._dict(start_date=add_days(today(),1),end_date=add_days(today(),2),planning_state='Draft')
        self.assertEqual(lifecycle(future),'Draft');future.planning_state='Ready';self.assertEqual(lifecycle(future),'Upcoming')
        future.start_date=add_days(today(),-2);future.end_date=add_days(today(),-1);self.assertEqual(lifecycle(future),'Completed')

    def test_draft_attendance_marks_do_not_post_earnings_before_event_completion(self):
        a=self.agreement();event=self.event(a)
        worker=frappe.get_doc('Employee',self.worker.name);worker.pp_daily_rate=100;worker.save()
        op.auto_assign(event['name']);frappe.db.set_value('PP Event Plan',event['name'],'planning_state','Draft')
        assignment=op.plan(event['name'])['allocations'][0]
        work=frappe.get_doc(dict(doctype='PP Work Entry',assignment=assignment.name,work_date=today(),units=1,status='Draft')).insert()
        work.status='Approved'
        with self.assertRaises(frappe.ValidationError):work.save()
        self.assertEqual(frappe.db.get_value('PP Work Entry',work.name,'status'),'Draft')
        op.save_project(event['name'],dict(complete=1));work=frappe.get_doc('PP Work Entry',work.name);work.status='Approved';work.save()
        self.assertEqual(frappe.db.get_value('PP Work Entry',work.name,'status'),'Approved')

    def test_sidebar_has_clickable_group_destinations_without_overview_children(self):
        from plus_point.navigation import product_navigation,SECTION_ALIASES
        from plus_point.sections import overview
        nav=product_navigation(False);items=nav['items'];labels=[i['label'] for i in items]
        for label in ('Clients','Agreements','Jobs and events','Workers','Inventory and equipment','Billing and invoices','Worker loans and advances','Worker statement'):
            self.assertIn(label,labels)
        self.assertEqual(labels.count('Overview'),1);self.assertIn('Attendance',labels)
        self.assertFalse(any(label.endswith(' overview') for label in labels))
        for old,new in SECTION_ALIASES.items():self.assertEqual(overview(old,self.f.company.name)['section'],new)

    def test_new_sidebar_order_starts_with_clients_and_keeps_deliberate_v2_order(self):
        from plus_point.navigation import product_navigation
        original=frappe.defaults.get_user_default
        def legacy(key,*args,**kwargs):
            if key=='pp_section_order_v1':return frappe.as_json(['Daily work','Clients and billing'])
            if key=='pp_section_order_v2':return None
            return original(key,*args,**kwargs)
        with patch('frappe.defaults.get_user_default',side_effect=legacy):
            self.assertEqual(product_navigation(False)['groups'][:2],['Clients and work','Workforce and resources'])
        def personal(key,*args,**kwargs):
            if key=='pp_section_order_v2':return frappe.as_json(['Finance','Clients and work','Workforce and resources','Reports and analytics'])
            return original(key,*args,**kwargs)
        with patch('frappe.defaults.get_user_default',side_effect=personal):
            self.assertEqual(product_navigation(False)['groups'][0],'Finance')

    def test_event_extension_rechecks_full_period_bookings_and_is_atomic(self):
        from plus_point.tests.test_events import EventTests
        from plus_point import events
        item,warehouse,_=EventTests.equipment(self)
        a=self.agreement();one=self.event(a);two=ae.create_event(agreement=a['name'],event_name='Later event',start_date=add_days(today(),3),end_date=add_days(today(),4))
        def reserve(event):
            plan=op.plan(event['name'])
            return frappe.get_doc(dict(doctype='PP Equipment Booking',project=plan['project'],site=plan['staffing'][0].site,item=item.name,warehouse=warehouse,quantity=10,start_date=plan['start_date'],end_date=plan['end_date'],status='Planned')).insert()
        first=reserve(one);second=reserve(two)
        with self.assertRaises(frappe.ValidationError):op.save_project(one['name'],dict(end_date=add_days(today(),3),budget=3456))
        self.assertEqual(str(op.plan(one['name'])['end_date']),str(add_days(today(),2)))
        self.assertEqual(str(frappe.db.get_value('PP Equipment Booking',first.name,'end_date')),str(add_days(today(),2)))
        self.assertNotEqual(float(op.plan(one['name'])['budget']),3456)
        second.status='Cancelled';second.save()
        before=events.stock_available(item.name,warehouse,today(),add_days(today(),4))['on_hand']
        op.save_project(one['name'],dict(end_date=add_days(today(),3)))
        self.assertEqual(str(frappe.db.get_value('PP Equipment Booking',first.name,'end_date')),str(add_days(today(),3)))
        self.assertEqual(events.stock_available(item.name,warehouse,today(),add_days(today(),4))['on_hand'],before)
