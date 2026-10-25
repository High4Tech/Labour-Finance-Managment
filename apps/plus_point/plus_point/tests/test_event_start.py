"""Starting an event hands off to live staffing without duplicate records."""
import json, unittest
from unittest.mock import patch
from datetime import timedelta
import frappe
from frappe.utils import now_datetime
from plus_point import drafts, operations as op
from plus_point.tests import test_hierarchy as hierarchy


class EventStartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): hierarchy.HierarchyTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls): hierarchy.HierarchyTests.tearDownClass.__func__(cls)
    setUp=hierarchy.HierarchyTests.setUp
    tearDown=hierarchy.HierarchyTests.tearDown
    agreement=hierarchy.HierarchyTests.agreement
    event=hierarchy.HierarchyTests.event

    def test_create_preserves_budget_comments_and_exposes_assignable_requirements(self):
        a=self.agreement();d=drafts.event_for_agreement(a['name'])
        op.add_comment('PP Planning Draft',d['name'],'Registration briefing at 08:00.')
        result=drafts.configure_event(d['name'],dict(action='Now',event_name='Working event',budget=2500,enforce_budget=1))
        plan=op.plan(result['event'])
        self.assertEqual(plan['event_name'],'Working event');self.assertEqual(plan['budget'],2500)
        self.assertEqual(plan['enforce_budget'],1);self.assertTrue(plan['staffing'])
        requirement=plan['staffing'][0]['name']
        available=op.available_crew(result['event'],requirement)
        self.assertTrue(any(row['name']==self.worker.name for row in available['rows']))
        self.assertTrue(frappe.db.exists('Comment',{'reference_doctype':'PP Event Plan','reference_name':result['event'],'content':'<p>Registration briefing at 08:00.</p>'}))
        self.assertEqual(drafts.load(d['name'])['status'],'Completed')
        self.assertFalse(frappe.db.exists('PP Work Entry',{'contract_terms':a['name']}))

    def test_retry_returns_the_same_event(self):
        a=self.agreement();d=drafts.event_for_agreement(a['name'])
        first=drafts.configure_event(d['name'],dict(action='Now',event_name='One event'))
        second=drafts.configure_event(d['name'],dict(action='Now',event_name='A retry'))
        self.assertEqual(first['event'],second['event'])
        self.assertEqual(frappe.db.count('PP Event Plan',{'project':a['project']}),1)

    def test_existing_event_is_reused_without_overwriting_details(self):
        a=self.agreement();event=self.event(a)
        op.save_project(event,dict(event_name='Keep this name',notes='Keep these notes',budget=1700))
        d=drafts.save('Event',dict(contract_terms=a['name'],event_name='Old duplicate draft',budget=9999),client_key='existing-event')
        result=drafts.configure_event(d['name'],dict(action='Now',event_name='Do not overwrite',notes='Do not overwrite'))
        self.assertEqual(result['event'],event)
        plan=op.plan(event)
        self.assertEqual(plan['event_name'],'Keep this name');self.assertEqual(plan['notes'],'Keep these notes');self.assertEqual(plan['budget'],1700)

    def test_budget_uses_the_agreement_currency(self):
        a=self.agreement();frappe.db.set_value('PP Contract Terms',a['name'],{'pp_agreement_currency':'USD','pp_agreement_rate':275})
        d=drafts.event_for_agreement(a['name'])
        result=drafts.configure_event(d['name'],dict(action='Now',event_name='Foreign currency budget',budget=100))
        self.assertEqual(op.plan(result['event'])['budget'],27500)

    def test_scheduling_keeps_budget_and_draft_comments(self):
        a=self.agreement();d=drafts.event_for_agreement(a['name'])
        d=drafts.save('Event',dict(d['payload'],budget=500,enforce_budget=1),name=d['name'],revision=d['revision'])
        op.add_comment('PP Planning Draft',d['name'],'Load equipment at 07:00.')
        due=now_datetime()+timedelta(minutes=5)
        drafts.configure_event(d['name'],dict(action='Schedule',event_name='Scheduled working event',scheduled_for=due))
        self.assertEqual(json.loads(frappe.db.get_value('PP Planning Draft',d['name'],'payload'))['budget'],500)
        with patch('plus_point.drafts.now_datetime',return_value=due+timedelta(seconds=1)):drafts.run_scheduled()
        result=drafts.load(d['name'])
        self.assertEqual(result['status'],'Completed');self.assertEqual(op.plan(result['event'])['budget'],500)
        self.assertTrue(frappe.db.exists('Comment',{'reference_doctype':'PP Event Plan','reference_name':result['event'],'content':'<p>Load equipment at 07:00.</p>'}))

    def test_invalid_budget_is_refused(self):
        for value in (-1,'not a number','NaN','Infinity'):
            frappe.db.savepoint('invalid_event_budget')
            a=self.agreement();d=drafts.event_for_agreement(a['name'])
            with self.assertRaises(frappe.ValidationError):drafts.configure_event(d['name'],dict(action='Now',event_name='Invalid budget',budget=value))
            frappe.db.rollback(save_point='invalid_event_budget')
