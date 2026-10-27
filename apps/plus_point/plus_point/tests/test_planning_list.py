"""Unified list filtering, pagination, source-aware deletion and tenant boundaries."""
import unittest
from unittest.mock import patch
import frappe
from frappe.utils import today, add_days, now_datetime
from plus_point import drafts, planning_list as listing, record_actions
from plus_point.tests import test_hierarchy as hierarchy


class PlanningListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): hierarchy.HierarchyTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls): hierarchy.HierarchyTests.tearDownClass.__func__(cls)
    setUp = hierarchy.HierarchyTests.setUp
    tearDown = hierarchy.HierarchyTests.tearDown
    agreement = hierarchy.HierarchyTests.agreement
    event = hierarchy.HierarchyTests.event

    def draft(self, title='Partial agreement', kind='Agreement', **extra):
        data = dict(details=dict(agreement_title=title, effective_start=today(), effective_end=add_days(today(), 4)),
                    terms=dict(billing_model='Fixed', fixed_amount=5000, agreement_currency='PKR')) if kind == 'Agreement' else dict(event_name=title)
        return drafts.save(kind, dict(data, **extra), client_key=title)

    def test_native_rows_and_drafts_share_totals_without_creating_records(self):
        baseline=listing.rows('PP Contract Terms',fields=['name'])['total']
        a = self.agreement()
        before = [frappe.db.count(dt) for dt in ('Customer','Project','Contract','PP Contract Terms','PP Event Plan')]
        d = self.draft()
        self.draft('Partial event', kind='Event')
        rows = listing.rows('PP Contract Terms', fields=['name','agreement_title','status'])
        self.assertEqual(rows['total'], baseline+2)
        self.assertTrue({a['name'], 'draft:' + d['name']} <= {r.name for r in rows['rows']})
        self.assertEqual(next(r.status for r in rows['rows'] if r.pp_draft_name), 'Draft')
        self.assertEqual(listing.rows('PP Event Plan', fields=['event_name'])['total'], 1)
        self.assertEqual(before, [frappe.db.count(dt) for dt in ('Customer','Project','Contract','PP Contract Terms','PP Event Plan')])

    def test_search_status_dates_sort_and_pagination_apply_to_both_sources(self):
        self.agreement('Alpha actual'); self.draft('Beta partial'); self.draft('Gamma partial')
        args=dict(doctype='PP Contract Terms', fields=['name','agreement_title','effective_start'], order_by='agreement_title asc',filters=[['PP Contract Terms','agreement_title','in',['Alpha actual','Beta partial','Gamma partial']]])
        self.assertEqual(listing.rows(**args, planning_status='Draft')['total'], 2)
        self.assertEqual(listing.rows(**args, planning_status='Created')['total'], 1)
        first=listing.rows(**args, page_length=2)
        second=listing.rows(**args, page_length=2, start=2)
        self.assertEqual([r.agreement_title for r in first['rows'] + second['rows']], ['Alpha actual','Beta partial','Gamma partial'])
        filtered=listing.rows(**{k:v for k,v in args.items() if k!='filters'}, filters=[['PP Contract Terms','agreement_title','like','%partial%'],['PP Contract Terms','effective_start','=',today()]])
        self.assertEqual(filtered['total'], 2)
        self.assertEqual(listing.rows(**args,planning_status='Draft')['total'],2)
        self.assertEqual(listing.rows('PP Contract Terms',fields=['name'],planning_status='Draft',filters={'creation':['timespan','today'],'fixed_amount':['>=',5000]})['total'],2)
        with self.assertRaises(frappe.ValidationError): listing.rows('PP Contract Terms', order_by='modified desc; DROP TABLE X')

    def test_completion_and_schedule_state_are_reflected_without_duplicates(self):
        a=self.agreement();d=drafts.event_for_agreement(a['name'])
        drafts.configure_event(d['name'],dict(event_name='Scheduled forum',action='Schedule',scheduled_for=add_days(now_datetime(),1)))
        row=listing.rows('PP Event Plan', fields=['name','event_name'])['rows'][0]
        self.assertEqual(row.pp_draft_status,'Scheduled');self.assertTrue(row.pp_scheduled_for)
        self.assertTrue(record_actions.review('PP Event Plan',row.name)['blocked'])
        saved=drafts.configure_event(d['name'],dict(event_name='Scheduled forum',action='Now'))
        rows=listing.rows('PP Event Plan',fields=['name'])
        self.assertEqual(rows['total'],1);self.assertEqual(rows['rows'][0].name,saved['event'])

    def test_draft_deletion_uses_actual_source_and_checks_kind(self):
        d=self.draft('Delete only this draft');name='draft:'+d['name']
        self.assertFalse(record_actions.review('PP Contract Terms',name)['blocked'])
        with self.assertRaises(frappe.PermissionError):record_actions.remove_many('PP Event Plan',[name])
        record_actions.remove_many('PP Contract Terms',[name])
        self.assertFalse(frappe.db.exists('PP Planning Draft',d['name']))

    def test_native_alias_fields_and_wrong_company_do_not_leak(self):
        a=self.agreement();d=self.draft()
        rows=listing.rows('PP Contract Terms',fields=['name','project.project_name as project_project_name'],filters={'name':['in',[a['name'],'draft:'+d['name']]]})
        self.assertEqual(len(rows['rows']),2)
        self.assertTrue(next(r for r in rows['rows'] if r.name==a['name']).project_project_name)
        with patch('plus_point.operations.company',return_value=frappe._dict(name='Different company')):
            self.assertEqual(listing.rows('PP Contract Terms',fields=['name'])['total'],0)

    def test_mixed_selection_deletes_each_actual_source(self):
        name=self.event();d=self.draft('Discard uncreated event',kind='Event')
        project=frappe.db.get_value('PP Event Plan',name,'project')
        frappe.db.set_value('Project',project,'pp_archived',1)
        self.assertEqual(next(row for row in listing.rows('PP Event Plan',fields=['name'])['rows'] if row.name==name).pp_record_archived,1)
        record_actions.remove_many('PP Event Plan',[name,'draft:'+d['name']])
        self.assertFalse(frappe.db.exists('PP Event Plan',name))
        self.assertFalse(frappe.db.exists('PP Planning Draft',d['name']))

    def test_navigation_has_only_respective_lists(self):
        from plus_point.navigation import product_navigation
        labels=[row['label'] for row in product_navigation(False)['items']]
        self.assertNotIn('Drafts',labels)
        self.assertIn('Agreements',labels);self.assertIn('Jobs and events',labels)
