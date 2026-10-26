"""Finite choices and editable event dates preserve staffing and recorded work."""
import unittest
from unittest.mock import patch
import frappe
from frappe.utils import today,add_days
from plus_point import operations as op,phases,drafts
from plus_point.tests import test_hierarchy as hierarchy
class EventControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):hierarchy.HierarchyTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):hierarchy.HierarchyTests.tearDownClass.__func__(cls)
    setUp=hierarchy.HierarchyTests.setUp
    tearDown=hierarchy.HierarchyTests.tearDown
    agreement=hierarchy.HierarchyTests.agreement
    event=hierarchy.HierarchyTests.event
    def test_phases_normalize_and_reject_unknown_values(self):
        self.assertEqual(phases.normalize(['Event','Setup','Event']),'Setup, Event')
        self.assertEqual(phases.normalize('event | pack down'),'Event, Pack-down')
        for value in ['Invalid','Setup, Bad',[],['Event',7]]:
            with self.subTest(value=value),self.assertRaises(frappe.ValidationError):phases.normalize(value)
    def test_two_phases_share_one_headcount_in_agreement_event_and_coverage(self):
        a=self.agreement();rows=op.agreement(a['name'])['staffing'];rows[0].phase='Setup, Event';op.save_agreement(dict(staffing=rows),a['name']);event=self.event(a)
        doc=frappe.get_doc('PP Event Plan',event);self.assertEqual(len(doc.staffing),1);self.assertEqual(doc.staffing[0].phase,'Setup, Event')
        self.assertTrue(all(row['planned']==1 and row['required']==1 for row in op.coverage(doc)))
        doc.staffing[0].phase='Unsupported'
        with self.assertRaises(frappe.ValidationError):doc.save()
    def test_unassigned_event_dates_can_change_with_inherited_staffing(self):
        a=self.agreement();event=self.event(a);first=add_days(today(),1);last=add_days(today(),3)
        op.save_project(event,dict(start_date=first,end_date=last));doc=frappe.get_doc('PP Event Plan',event)
        self.assertEqual((str(doc.start_date),str(doc.end_date)),(first,last));self.assertEqual((str(doc.staffing[0].start_date),str(doc.staffing[0].end_date)),(first,last))
        self.assertEqual(str(frappe.get_doc('PP Contract Terms',a['name']).effective_start),today())
    def test_date_change_cannot_exclude_existing_worker_allocations(self):
        a=self.agreement();event=self.event(a);op.auto_assign(event)
        with self.assertRaises(frappe.ValidationError):op.save_project(event,dict(start_date=add_days(today(),1)))
        self.assertEqual(str(frappe.get_doc('PP Event Plan',event).start_date),today())
    def test_existing_event_metadata_can_be_drafted_without_changing_live_event(self):
        event=self.event();before=frappe.get_doc('PP Event Plan',event);payload=dict(record=event,contract_terms=before.contract_terms,event_name='Revised event',notes='Draft instructions',start_date=str(before.start_date),end_date=str(before.end_date))
        draft=drafts.save('Event',payload,client_key='event-edit-control');self.assertEqual(drafts.load(draft['name'])['payload'],payload);self.assertEqual(frappe.db.get_value('PP Event Plan',event,'event_name'),before.event_name)
        with patch('plus_point.event_setup.companies',return_value=[]),self.assertRaises((frappe.PermissionError,frappe.ValidationError)):drafts.save('Event',payload,client_key='wrong-company')
