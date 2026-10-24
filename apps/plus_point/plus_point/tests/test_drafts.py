"""Partial drafts, scheduled creation and attendance-only checkpoints; rollback only."""
import json,unittest
from datetime import timedelta
from unittest.mock import patch
import frappe
from frappe.utils import today,add_days,now_datetime
from plus_point import drafts,daily_billing,operations as op
from plus_point.tests import test_hierarchy as hierarchy
from plus_point.tests.test_operations import insert


class DraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):hierarchy.HierarchyTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):hierarchy.HierarchyTests.tearDownClass.__func__(cls)
    setUp=hierarchy.HierarchyTests.setUp
    tearDown=hierarchy.HierarchyTests.tearDown
    agreement=hierarchy.HierarchyTests.agreement
    event=hierarchy.HierarchyTests.event

    def test_partial_draft_does_not_create_client_contract_or_event(self):
        before=[frappe.db.count(dt) for dt in ['Customer','Contract','PP Contract Terms','PP Event Plan']]
        payload=dict(details=dict(agreement_title='Incomplete',scope=''),client=dict(email='not-valid-yet'),staffing=[])
        result=drafts.save('Agreement',payload,client_key='partial')
        self.assertEqual(drafts.load(result['name'])['payload'],payload)
        self.assertEqual(before,[frappe.db.count(dt) for dt in ['Customer','Contract','PP Contract Terms','PP Event Plan']])

    def test_retries_are_idempotent_and_stale_revisions_are_refused(self):
        a=drafts.save('Event',dict(event_name='First'),client_key='retry')
        b=drafts.save('Event',dict(event_name='First'),client_key='retry',revision=0)
        self.assertEqual((a['name'],a['revision']),(b['name'],b['revision']))
        with self.assertRaises(frappe.ValidationError):drafts.save('Event',dict(event_name='Stale'),name=a['name'],revision=0)
        self.assertEqual(drafts.load(a['name'])['payload']['event_name'],'First')

    def test_drafts_cannot_cross_company_or_change_through_native_api(self):
        a=drafts.save('Agreement',{},client_key='private')
        with patch('plus_point.operations.company',return_value=frappe._dict(name='Different company')):
            with self.assertRaises(frappe.PermissionError):drafts.load(a['name'])
        doc=frappe.get_doc(drafts.DT,a['name']);doc.title='Native bypass'
        with self.assertRaises(frappe.PermissionError):doc.save()

    def test_agreement_handoff_creates_one_event_draft_and_no_allocations(self):
        a=self.agreement();first=drafts.event_for_agreement(a['name']);second=drafts.event_for_agreement(a['name'])
        self.assertEqual(first['name'],second['name']);self.assertEqual(first['status'],'Draft')
        self.assertFalse(frappe.db.exists('PP Event Plan',{'project':a['project']}))
        self.assertFalse(frappe.db.exists('PP Assignment',{'project':a['project']}))

    def test_event_schedule_rejects_past_and_invalid_event_dates(self):
        a=self.agreement();d=drafts.event_for_agreement(a['name'])
        with self.assertRaises(frappe.ValidationError):drafts.configure_event(d['name'],dict(action='Schedule',event_name='Later',scheduled_for=now_datetime()-timedelta(minutes=1)))
        with self.assertRaises(frappe.ValidationError):drafts.configure_event(d['name'],dict(action='Now',event_name='Wrong dates',start_date=add_days(today(),3),end_date=today()))
        self.assertFalse(frappe.db.exists('PP Event Plan',{'project':a['project']}))

    def test_scheduled_creation_is_once_only_and_has_no_financial_posting(self):
        a=self.agreement();d=drafts.event_for_agreement(a['name']);due=now_datetime()+timedelta(minutes=2)
        drafts.configure_event(d['name'],dict(action='Schedule',event_name='Scheduled event',scheduled_for=due))
        with patch('plus_point.drafts.now_datetime',return_value=due+timedelta(seconds=1)):
            drafts.run_scheduled();drafts.run_scheduled()
        saved=drafts.load(d['name']);self.assertEqual(saved['status'],'Completed')
        self.assertEqual(frappe.db.count('PP Event Plan',{'project':a['project']}),1)
        self.assertFalse(frappe.db.exists('PP Assignment',{'project':a['project']}))
        self.assertFalse(frappe.db.exists('PP Work Entry',{'contract_terms':a['name']}))

    def test_schedule_failure_stays_visible_and_does_not_create_an_event(self):
        a=self.agreement();d=drafts.event_for_agreement(a['name']);due=now_datetime()+timedelta(minutes=2)
        drafts.configure_event(d['name'],dict(action='Schedule',event_name='Closed agreement',scheduled_for=due))
        op.save_agreement(dict(status='Closed'),a['name'])
        with patch('plus_point.drafts.now_datetime',return_value=due+timedelta(seconds=1)):drafts.run_scheduled()
        self.assertEqual(drafts.load(d['name'])['status'],'Failed');self.assertTrue(drafts.load(d['name'])['last_error'])
        self.assertFalse(frappe.db.exists('PP Event Plan',{'project':a['project']}))

    def checkpoint(self,**changes):
        return dict(dict(id='one',title='Daily approved work',frequency='Daily',from_date=today(),to_date=today(),due_date=today()),**changes)

    def test_daily_checkpoint_is_not_a_fixed_revenue_milestone(self):
        a=self.agreement();op.save_agreement(dict(pp_daily_checkpoints=json.dumps([self.checkpoint()])),a['name'])
        self.assertEqual(daily_billing.overview(a['name'])[0]['amount'],0)
        self.assertFalse(frappe.db.exists('PP Milestone',{'contract_terms':a['name']}))
        self.assertFalse(frappe.db.exists('PP Work Entry',{'contract_terms':a['name']}))

    def test_daily_checkpoints_refuse_overlap_dates_and_invoice_forgery(self):
        a=self.agreement()
        for rows in [[self.checkpoint(),self.checkpoint(id='two')],[self.checkpoint(to_date=add_days(today(),-1))],[self.checkpoint(invoice='fake-invoice')]]:
            with self.assertRaises(frappe.ValidationError):op.save_agreement(dict(pp_daily_checkpoints=json.dumps(rows)),a['name'])
        self.assertEqual(frappe.parse_json(op.agreement(a['name'])['pp_daily_checkpoints'] or '[]'),[])

    def test_daily_invoice_uses_approved_attendance_once_and_releases_deleted_draft(self):
        a=self.agreement();op.save_agreement(dict(pp_daily_checkpoints=json.dumps([self.checkpoint()])),a['name'])
        event=self.event(a);op.auto_assign(event)
        allocation=frappe.db.get_value('PP Assignment',{'project':a['project']},'name')
        work=insert('PP Work Entry',assignment=allocation,work_date=today(),units=1,status='Draft');work.status='Approved';work.save()
        first=daily_billing.invoice(a['name'],'one');second=daily_billing.invoice(a['name'],'one')
        self.assertEqual(first['name'],second['name'])
        self.assertEqual(frappe.get_doc('Sales Invoice',first['name']).docstatus,0)
        frappe.delete_doc('Sales Invoice',first['name'])
        self.assertFalse(frappe.parse_json(op.agreement(a['name'])['pp_daily_checkpoints'])[0].get('invoice'))
        self.assertTrue(daily_billing.overview(a['name'])[0]['sources'])

    def test_daily_checkpoints_are_in_the_client_signing_snapshot(self):
        from plus_point.signing import snapshot
        a=self.agreement();op.save_agreement(dict(pp_daily_checkpoints=json.dumps([self.checkpoint()])),a['name'])
        html=snapshot(a['name']);self.assertIn('Daily billing milestones',html);self.assertIn('Daily approved work',html)

    def test_cancelling_scheduled_creation_leaves_a_reusable_draft(self):
        a=self.agreement();d=drafts.event_for_agreement(a['name']);due=now_datetime()+timedelta(minutes=2)
        drafts.configure_event(d['name'],dict(action='Schedule',event_name='Scheduled',scheduled_for=due))
        saved=drafts.configure_event(d['name'],dict(action='Draft',event_name='Later'))
        self.assertEqual(saved['status'],'Draft');self.assertIsNone(saved['scheduled_for'])
        with patch('plus_point.drafts.now_datetime',return_value=due+timedelta(seconds=1)):drafts.run_scheduled()
        self.assertFalse(frappe.db.exists('PP Event Plan',{'project':a['project']}))

    def test_event_dates_can_use_a_subset_of_the_agreement(self):
        a=self.agreement();d=drafts.event_for_agreement(a['name'])
        saved=drafts.configure_event(d['name'],dict(action='Now',event_name='One day',start_date=today(),end_date=today()))
        event=frappe.get_doc('PP Event Plan',saved['event']);self.assertEqual(str(event.start_date),str(event.end_date))
        self.assertTrue(all(str(r.start_date)==today() and str(r.end_date)==today() for r in event.staffing))

    def test_native_checkpoint_invoice_reference_cannot_be_forged(self):
        a=self.agreement();doc=frappe.get_doc('PP Contract Terms',a['name']);doc.pp_daily_checkpoints=json.dumps([self.checkpoint(invoice='fake')])
        with self.assertRaises(frappe.ValidationError):doc.save()

    def test_draft_size_is_bounded(self):
        with self.assertRaises(frappe.ValidationError):drafts.save('Agreement',dict(details=dict(scope='x'*100000)),client_key='oversized')
