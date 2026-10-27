"""Commercial roots and independent delivery snapshots preserve native history."""
import unittest
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs
import frappe
from frappe.utils import today,add_days
from plus_point.tests import test_hierarchy as h
from plus_point import operations as op,agreement_events as ae,agreement_updates as updates,signing
class ArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):h.HierarchyTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):h.HierarchyTests.tearDownClass.__func__(cls)
    setUp=h.HierarchyTests.setUp
    tearDown=h.HierarchyTests.tearDown
    agreement=h.HierarchyTests.agreement
    def occurrence(self,a,**kw):
        return ae.create_event(agreement=a['name'],event_name='Independent delivery',start_date=today(),end_date=add_days(today(),2),**kw)
    def test_two_events_inherit_rates_have_independent_projects_sites_and_budgets(self):
        a=self.agreement();one=self.occurrence(a,budget=400);two=self.occurrence(a,budget=700)
        self.assertNotEqual(one['project'],two['project']);self.assertNotEqual(one['contract_terms'],two['contract_terms'])
        first=op.plan(one['name']);second=op.plan(two['name'])
        self.assertEqual(first['staffing'][0].client_rate,1500);self.assertNotEqual(first['staffing'][0].site,second['staffing'][0].site)
        self.assertEqual(first['budget'],400);self.assertEqual(second['budget'],700);self.assertEqual(len(ae.linked_events(a['name'])),2)
        self.assertEqual(len([r for r in op.catalogue()['agreements'] if r.project in (one['project'],two['project'])]),0)
    def test_ongoing_rate_card_has_no_quantities_or_end_and_creates_no_future_event(self):
        a=op.save_agreement(dict(customer=self.f.customer.name,agreement_title='Annual service',scope='Termination on thirty days notice',effective_start=today(),validity_mode='Ongoing',resource_mode='Rate card',rate_card=frappe.as_json([dict(designation=self.role,client_rate=1500)]),billing_model='Daily',status='Active',staffing=[]))
        self.assertIsNone(op.agreement(a['name'])['effective_end']);self.assertEqual(ae.linked_events(a['name']),[])
        snapshot=signing.snapshot(a['name']);self.assertIn('Ongoing',snapshot);self.assertIn('Negotiated rate card',snapshot);self.assertIn(self.role,snapshot)
        result=self.occurrence(a);self.assertEqual(op.plan(result['name'])['staffing'],[])
    def test_fixed_period_still_requires_ordered_end_date(self):
        for end in (None,add_days(today(),-1)):
            with self.assertRaises(frappe.ValidationError):op.save_agreement(dict(customer=self.f.customer.name,agreement_title='Invalid',scope='Details',effective_start=today(),effective_end=end,validity_mode='Fixed period',resource_mode='Per event',billing_model='Daily',status='Active',staffing=[]))
    def test_standalone_pending_can_plan_but_cannot_invoice_until_confirmed(self):
        r=ae.create_event(customer=self.f.customer.name,event_name='One day service',start_date=today(),end_date=today())
        data=op.plan(r['name']);self.assertTrue(data['standalone']);self.assertIsNone(data['governing_agreement'])
        terms=frappe.get_doc('PP Contract Terms',r['contract_terms'])
        with self.assertRaises(frappe.ValidationError):ae.assert_confirmed(terms)
        ae.confirm_event(r['name'],'Company attested','Client confirmed by telephone');ae.assert_confirmed(frappe.get_doc('PP Contract Terms',terms.name))
    def test_fixed_agreement_is_allocated_never_copied_to_each_event(self):
        a=self.agreement(fixed=True);one=self.occurrence(a,fixed_amount=4000);two=self.occurrence(a,fixed_amount=6000)
        with self.assertRaises(frappe.ValidationError):self.occurrence(a,fixed_amount=1)
        from plus_point.api import project_summary
        self.assertEqual(project_summary(one['project'])['earned_revenue'],'0.00');self.assertEqual(project_summary(two['project'])['fixed_contract_value'],'6000.00')
        summary=ae.financial_summary(a['name']);self.assertEqual(summary['contract_value'],'10000.00');self.assertEqual(summary['earned_revenue'],'0.00')
        from plus_point.reporting import project_finances
        rows=project_finances(dict(company=self.f.company.name))[1];self.assertNotIn(a['project'],[r['project'] for r in rows]);self.assertEqual(sum(float(r['fixed_contract_value']) for r in rows if r['project'] in (one['project'],two['project'])),10000)
    def test_legacy_event_api_retains_original_relationship(self):
        a=self.agreement();r=op.create_plan(a['name'],'Legacy compatible');again=op.create_plan(a['name'],'Retry')
        self.assertEqual(r['name'],again['name']);self.assertEqual(op.plan(r['name'])['project'],a['project'])
    def test_other_company_cannot_create_event_or_read_aggregation(self):
        a=self.agreement()
        with patch('plus_point.operations.company',return_value=frappe._dict(name='Another company')):
            with self.assertRaises((frappe.PermissionError,frappe.ValidationError)):self.occurrence(a)
            with self.assertRaises((frappe.PermissionError,frappe.ValidationError)):ae.financial_summary(a['name'])
    def test_manual_approval_records_company_attestation_and_preserves_existing_event_rate(self):
        a=self.agreement();r=self.occurrence(a);before=op.plan(r['name'])['staffing'][0].client_rate
        share=signing.create_link(a['name'])
        with self.assertRaises(frappe.ValidationError):op.save_agreement(dict(scope='Unapproved'),a['name'])
        result=updates.propose(a['name'],dict(scope='Approved revised scope'),'Scope clarified',method='Company attested')
        self.assertEqual(result['status'],'Signed');self.assertEqual(op.agreement(a['name'])['scope'],'Approved revised scope')
        self.assertEqual(op.plan(r['name'])['staffing'][0].client_rate,before)
        self.assertEqual(frappe.db.get_value('PP Agreement Share',result['name'],'approval_method'),'Company attested')
    def test_email_proposal_does_not_change_current_terms_until_client_accepts(self):
        a=self.agreement();old=op.agreement(a['name'])['scope']
        with patch('plus_point.agreement_updates.recipients',create=True),patch('plus_point.signing.send_link') as send,patch('frappe.db.exists',wraps=frappe.db.exists) as exists:
            original=exists._mock_wraps
            exists.side_effect=lambda dt,*args,**kw:True if dt=='Email Account' else original(dt,*args,**kw)
            result=updates.propose(a['name'],dict(scope='Client approved scope'),'Scope adjustment',recipient='client@example.invalid')
        self.assertEqual(op.agreement(a['name'])['scope'],old);self.assertEqual(send.call_count,1)
        token=parse_qs(urlparse(result['url']).query)['token'][0]
        signing.accept(token,'Test Client','client@example.invalid',1)
        self.assertEqual(op.agreement(a['name'])['scope'],'Client approved scope')
    def test_stale_update_cannot_overwrite_a_newer_approved_revision(self):
        a=self.agreement();one=updates.propose(a['name'],dict(scope='First'),'First update',method='Company attested')
        doc=frappe.get_doc('PP Agreement Share',one['name']);self.assertTrue(doc.base_modified)
        with self.assertRaises(frappe.ValidationError):updates.apply(doc)

    def test_approved_work_is_attributed_once_and_daily_period_creates_separate_event_invoices(self):
        a=self.agreement();one=self.occurrence(a);two=ae.create_event(agreement=a['name'],event_name='Later delivery',start_date=add_days(today(),3),end_date=add_days(today(),4))
        worker=frappe.get_doc('Employee',self.worker.name);worker.pp_daily_rate=100;worker.pp_salary_basis='Daily';worker.save()
        for event in (one,two):
            op.auto_assign(event['name']);plan=op.plan(event['name']);assignment=plan['allocations'][0]
            work=frappe.get_doc(dict(doctype='PP Work Entry',assignment=assignment.name,work_date=plan['start_date'],units=1,status='Draft')).insert();work.status='Approved';work.save()
        summary=ae.financial_summary(a['name']);self.assertEqual(summary['earned_revenue'],'3000.00');self.assertEqual(summary['labour_cost'],'200.00')
        from plus_point.daily_billing import create_period_invoice
        result=create_period_invoice(frappe.get_doc('PP Contract Terms',a['name']),dict(from_date=today(),to_date=add_days(today(),4),due_date=add_days(today(),5)))
        self.assertEqual(len(result['invoices']),2);self.assertEqual({frappe.db.get_value('Sales Invoice',n,'project') for n in result['invoices']},{one['project'],two['project']})
        self.assertEqual(ae.financial_summary(a['name'])['earned_revenue'],'3000.00')
        with self.assertRaises(frappe.ValidationError):create_period_invoice(frappe.get_doc('PP Contract Terms',a['name']),dict(from_date=today(),to_date=add_days(today(),4),due_date=add_days(today(),5)))
    def test_uncovered_event_rate_needs_commercial_confirmation(self):
        a=self.agreement();r=self.occurrence(a);terms=frappe.get_doc('PP Contract Terms',r['contract_terms']);self.assertEqual(terms.commercial_status,'Confirmed')
        from plus_point.tests.test_operations import insert
        site=insert('PP Site',project=r['project'],site_name='Extra venue',is_active=1)
        op.add_requirement(r['name'],dict(site=site.name,designation=self.role,phase='Event',start_date=today(),end_date=add_days(today(),2),workers_required=1,wage_rate=100,client_rate=1700))
        with self.assertRaises(frappe.ValidationError):ae.assert_confirmed(frappe.get_doc('PP Contract Terms',terms.name))
        self.assertEqual(frappe.db.get_value('PP Agreement Staffing',{'parent':a['name']},'client_rate'),1500)
    def test_event_and_parent_milestones_share_one_approved_value_ceiling(self):
        a=self.agreement(fixed=True);r=self.occurrence(a,fixed_amount=6000)
        with self.assertRaises(frappe.ValidationError):op.save_milestone(a['name'],dict(milestone_title='Overallocated root delivery',due_date=today(),amount=5000,status='Approved'))
        op.save_milestone(a['name'],dict(milestone_title='Remaining agreement allocation',due_date=today(),amount=4000,status='Approved'))
        op.save_milestone(r['contract_terms'],dict(milestone_title='Event delivery',due_date=today(),amount=6000,status='Approved'))
        with self.assertRaises(frappe.ValidationError):op.save_milestone(a['name'],dict(milestone_title='Duplicate recognition',due_date=today(),amount=1,status='Approved'))
    def test_multiple_cc_addresses_accept_separators_but_reject_headers(self):
        from plus_point.agreement_documents import recipients
        self.assertEqual(recipients('client@example.invalid','one@example.invalid;two@example.invalid\nthree@example.invalid')[1],['one@example.invalid','two@example.invalid','three@example.invalid'])
        with self.assertRaises(frappe.ValidationError):recipients('client@example.invalid','one@example.invalid\nBcc: hidden@example.invalid')

    def test_standalone_draft_creates_once_without_formal_agreement(self):
        from plus_point import drafts
        payload=dict(event_path='Standalone',event_name='Standalone draft delivery',customer=self.f.customer.name,start_date=today(),end_date=today(),billing_model='Daily',new_occurrence=1)
        d=drafts.save('Event',payload,client_key='standalone-architecture')
        first=drafts.configure_event(d['name'],dict(action='Now'));second=drafts.configure_event(d['name'],dict(action='Now'))
        self.assertEqual(first['event'],second['event']);self.assertTrue(op.plan(first['event'])['standalone'])

    def test_event_schedule_does_not_change_ongoing_parent_validity(self):
        a=op.save_agreement(dict(customer=self.f.customer.name,agreement_title='Ongoing',scope='Thirty days termination notice',effective_start=today(),validity_mode='Ongoing',resource_mode='Per event',billing_model='Daily',status='Active',staffing=[]))
        event=self.occurrence(a)
        from plus_point.daily_billing import periods
        schedule=periods(today(),add_days(today(),2),'Weekly',5);ae.save_schedule(event['name'],schedule)
        self.assertEqual(len(frappe.parse_json(frappe.db.get_value('PP Contract Terms',event['contract_terms'],'pp_daily_checkpoints'))),1)
        self.assertIsNone(frappe.db.get_value('Contract',frappe.db.get_value('PP Contract Terms',a['name'],'contract'),'end_date'))
        self.assertIsNone(op.agreement(a['name'])['effective_end'])

    def test_existing_single_event_can_share_remaining_fixed_value_with_another_event(self):
        a=self.agreement(fixed=True);legacy=op.create_plan(a['name'],'Original delivery');second=self.occurrence(a,fixed_amount=4000)
        from plus_point.api import project_summary
        self.assertEqual(project_summary(a['project'])['fixed_contract_value'],'6000.00')
        with self.assertRaises(frappe.ValidationError):op.save_milestone(a['name'],dict(milestone_title='Too much',due_date=today(),amount=7000,status='Approved'))
        op.save_milestone(a['name'],dict(milestone_title='Original allocation',due_date=today(),amount=6000,status='Approved'))
        op.save_milestone(second['contract_terms'],dict(milestone_title='Second allocation',due_date=today(),amount=4000,status='Approved'))
        self.assertEqual(ae.financial_summary(a['name'])['earned_revenue'],'10000.00')

    def test_rate_card_currency_is_converted_once_and_snapshot_uses_client_units(self):
        a=op.save_agreement(dict(customer=self.f.customer.name,agreement_title='Foreign rate card',scope='Support services',effective_start=today(),effective_end=add_days(today(),4),billing_model='Daily',resource_mode='Rate card',rate_card=frappe.as_json([dict(designation=self.role,client_rate=10)]),agreement_currency='USD',agreement_rate=275,status='Active',staffing=[]))
        doc=op.agreement(a['name']);self.assertEqual(frappe.parse_json(doc['rate_card'])[0]['client_rate'],2750)
        self.assertIn('10.00 USD',signing.snapshot(a['name']))

    def test_rate_card_owns_crew_prices_and_preserves_existing_event_snapshot(self):
        a=self.agreement()
        op.save_agreement(dict(resource_mode='Rate card',rate_card=frappe.as_json([dict(designation=self.role,client_rate=800)])),a['name'])
        self.assertEqual(op.agreement(a['name'])['staffing'][0].client_rate,800)
        event=self.occurrence(a)
        op.save_agreement(dict(rate_card=frappe.as_json([dict(designation=self.role,client_rate=900)])),a['name'])
        self.assertEqual(op.agreement(a['name'])['staffing'][0].client_rate,900)
        self.assertEqual(op.plan(event['name'])['staffing'][0].client_rate,800)

    def test_rate_card_overrides_independent_price_after_one_currency_conversion(self):
        a=self.agreement();rows=[dict(r) for r in op.agreement(a['name'])['staffing']]
        rows[0]['client_rate']=999
        op.save_agreement(dict(resource_mode='Rate card',rate_card=frappe.as_json([dict(designation=self.role,client_rate=10)]),agreement_currency='USD',agreement_rate=275,staffing=rows),a['name'])
        self.assertEqual(op.agreement(a['name'])['staffing'][0].client_rate,2750)
        self.assertIn('10.00 USD',signing.snapshot(a['name']))

    def test_rate_card_requires_a_price_for_each_crew_category(self):
        a=self.agreement()
        with self.assertRaisesRegex(frappe.ValidationError,'rate card'):
            op.save_agreement(dict(resource_mode='Rate card',rate_card='[]'),a['name'])

    def test_signed_rate_card_still_requires_client_approval(self):
        a=self.agreement();op.save_agreement(dict(resource_mode='Rate card',rate_card=frappe.as_json([dict(designation=self.role,client_rate=800)])),a['name'])
        signing.create_link(a['name'])
        with self.assertRaisesRegex(frappe.ValidationError,'Propose an agreement update'):
            op.save_agreement(dict(rate_card=frappe.as_json([dict(designation=self.role,client_rate=900)])),a['name'])

    def test_native_contract_edit_cannot_bypass_agreement_approval(self):
        a=self.agreement();signing.create_link(a['name']);contract=frappe.get_doc('Contract',frappe.db.get_value('PP Contract Terms',a['name'],'contract'));old=contract.contract_terms;contract.contract_terms='Unapproved native edit'
        with self.assertRaises(frappe.ValidationError):contract.save()
        self.assertEqual(frappe.db.get_value('Contract',contract.name,'contract_terms'),old)

    def test_daily_milestone_title_survives_save_and_date_rebase(self):
        from plus_point.daily_billing import periods
        a=self.agreement();terms=frappe.get_doc('PP Contract Terms',a['name'])
        schedule=periods(terms.effective_start,terms.effective_end,'Weekly',5)
        schedule[0]['title']='Venue support payment'
        op.save_agreement(dict(pp_daily_checkpoints=frappe.as_json(schedule)),a['name'])
        saved=frappe.parse_json(op.agreement(a['name'])['pp_daily_checkpoints'])
        self.assertEqual(saved[0]['title'],'Venue support payment')
        op.save_agreement(dict(effective_end=add_days(terms.effective_end,7)),a['name'])
        rebased=frappe.parse_json(op.agreement(a['name'])['pp_daily_checkpoints'])
        self.assertEqual(rebased[0]['title'],'Venue support payment')
        self.assertEqual(rebased[-1]['to_date'],str(add_days(terms.effective_end,7)))
