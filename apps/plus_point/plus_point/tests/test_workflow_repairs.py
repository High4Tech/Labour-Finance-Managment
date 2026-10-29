"""Empty drafts, site reuse, occupied slots and focused event removal; rollback only."""
import unittest
from unittest.mock import patch
import frappe
from frappe.utils import today,add_days
from plus_point import drafts,planning,operations as op,record_actions as actions
from plus_point.tests import test_hierarchy as hierarchy
from plus_point.tests.test_operations import insert


class WorkflowRepairsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):hierarchy.HierarchyTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):hierarchy.HierarchyTests.tearDownClass.__func__(cls)
    setUp=hierarchy.HierarchyTests.setUp
    tearDown=hierarchy.HierarchyTests.tearDown
    agreement=hierarchy.HierarchyTests.agreement
    event=hierarchy.HierarchyTests.event

    def test_auto_daily_worker_overrides_keep_profile_snapshot_and_booking_checks(self):
        event=self.event();doc=frappe.get_doc('PP Event Plan',event);role=doc.staffing[0].name;settings={role:dict(basis='Daily')}
        preview=op.auto_assign_preview(event,[role],settings);worker=preview['assignments'][0]['employee']
        with self.assertRaises(frappe.ValidationError):op.auto_assign(event,requirements=[role],payments=settings,rates={'foreign-worker':125},expected=preview['snapshot'])
        for amount in (-1,0,'NaN'):
            with self.assertRaises(frappe.ValidationError):op.auto_assign_preview(event,[role],settings,rates={worker:amount})
        result=op.auto_assign(event,requirements=[role],payments=settings,rates={worker:125},expected=preview['snapshot'])
        self.assertEqual(frappe.db.get_value('PP Assignment',result['assignments'][0],'wage_rate'),125)

    def test_monthly_auto_selection_rejects_daily_worker_override(self):
        event=self.event();doc=frappe.get_doc('PP Event Plan',event);role=doc.staffing[0].name
        worker=frappe.get_doc('Employee',self.worker.name);worker.pp_monthly_rate=3000;worker.save()
        settings={role:dict(basis='Monthly')};preview=op.auto_assign_preview(event,[role],settings)
        with self.assertRaises(frappe.ValidationError):op.auto_assign(event,requirements=[role],payments=settings,expected=preview['snapshot'],rates={self.worker.name:125})
        self.assertFalse(frappe.db.exists('PP Assignment',{'pp_event_plan':event}))

    def test_bulk_requirements_rejects_foreign_rows_and_invalid_dates(self):
        event=self.event();doc=frappe.get_doc('PP Event Plan',event);role=doc.staffing[0].name
        with self.assertRaises(frappe.ValidationError):op.bulk_requirements(event,[role,'foreign'],dict(workers_required=2))
        self.assertEqual(frappe.get_doc('PP Event Plan',event).staffing[0].workers_required,1)
        with self.assertRaises(frappe.ValidationError):op.bulk_requirements(event,[role],dict(end_date=add_days(today(),-1)))
        op.bulk_requirements(event,[role],dict(workers_required=2))
        self.assertEqual(frappe.get_doc('PP Event Plan',event).staffing[0].workers_required,2)

    def test_early_period_document_does_not_consume_attendance_or_recognize_revenue(self):
        from plus_point import daily_billing as daily
        agreement=self.agreement();terms=frappe.get_doc('PP Contract Terms',agreement['name'])
        terms.pp_daily_checkpoints=frappe.as_json(daily.periods(terms.effective_start,terms.effective_end,'Completion'));terms.save();row=frappe.parse_json(terms.pp_daily_checkpoints)[0]
        before=(frappe.db.count('Sales Invoice'),frappe.db.count('PP Work Entry'),frappe.db.count('GL Entry'))
        with patch('plus_point.agreement_documents.pdf_content',return_value=b'pdf-rendered') as render,patch('plus_point.agreement_documents.save_pdf',return_value=dict(name='estimate',file_name='Pro forma invoice.pdf')):
            result=daily.invoice(terms.name,row['id'])
        self.assertIn('Estimated',render.call_args.args[0]);self.assertIn('Attendance is not finalized',render.call_args.args[0])
        self.assertTrue(result['estimated']);self.assertIn('Pro forma invoice',result['pdf']['file_name'])
        self.assertEqual(before,(frappe.db.count('Sales Invoice'),frappe.db.count('PP Work Entry'),frappe.db.count('GL Entry')))
        terms.reload();self.assertFalse(frappe.parse_json(terms.pp_daily_checkpoints)[0].get('invoice'))

    def test_signature_document_uses_readable_time_and_optional_verification(self):
        from plus_point.agreement_documents import signed_body
        html=signed_body(frappe._dict(snapshot='<h1>Agreement</h1>',status='Signed',signed_by='Sara Khan',signed_on='2026-10-29 11:54:44.808002',digest='a'*64))
        self.assertIn('29 Oct 2026',html);self.assertNotIn('.808002',html);self.assertIn('<details>',html);self.assertNotIn('Agreement version:',html)

    def test_estimate_does_not_prevent_later_actual_attendance_invoice(self):
        from plus_point import daily_billing as daily
        event=self.event();plan=frappe.get_doc('PP Event Plan',event);terms=frappe.get_doc('PP Contract Terms',plan.contract_terms)
        terms.pp_daily_checkpoints=frappe.as_json(daily.periods(terms.effective_start,terms.effective_end,'Completion'));terms.save();row=frappe.parse_json(terms.pp_daily_checkpoints)[0]
        with patch('plus_point.agreement_documents.estimated_period_invoice',return_value=dict(name='estimated-document')):
            self.assertTrue(daily.invoice(terms.name,row['id'])['estimated'])
        allocation=op.auto_assign(event)['assignments'][0]
        work=insert('PP Work Entry',assignment=allocation,work_date=today(),units=1,status='Draft');work.status='Approved';work.save()
        count=frappe.db.count('Sales Invoice')
        with patch('plus_point.daily_billing.today',return_value=add_days(today(),10)):
            actual=daily.invoice(terms.name,row['id'])
            self.assertEqual(daily.invoice(terms.name,row['id'])['name'],actual['name'])
        self.assertEqual(frappe.db.count('Sales Invoice'),count+1)
        invoice=frappe.get_doc('Sales Invoice',actual['name']);self.assertEqual(invoice.docstatus,0)
        self.assertEqual(float(invoice.total),1500);self.assertEqual(frappe.db.get_value('PP Work Entry',work.name,'sales_invoice'),invoice.name)

    def test_bulk_milestones_are_atomic_and_cannot_touch_other_agreements(self):
        agreement=self.agreement('Bulk fixed',fixed=True)
        first=op.save_milestone(agreement['name'],dict(milestone_title='First',due_date=today(),amount=2000,status='Planned'))['name']
        second=op.save_milestone(agreement['name'],dict(milestone_title='Second',due_date=today(),amount=2000,status='Planned'))['name']
        with self.assertRaises(frappe.ValidationError):op.bulk_milestones(agreement['name'],[first,second],dict(amount=8000))
        self.assertEqual(float(frappe.db.get_value('PP Milestone',first,'amount')),2000)
        other=self.agreement('Other fixed',fixed=True)
        foreign=op.save_milestone(other['name'],dict(milestone_title='Foreign',due_date=today(),amount=1000,status='Planned'))['name']
        with self.assertRaises(frappe.ValidationError):op.bulk_milestones(agreement['name'],[first,foreign],dict(due_date=add_days(today(),1)))
        op.bulk_milestones(agreement['name'],[first,second],dict(due_date=add_days(today(),1)))
        self.assertEqual(str(frappe.db.get_value('PP Milestone',second,'due_date')),add_days(today(),1))

    def test_empty_and_default_only_agreements_do_not_create_drafts(self):
        before=frappe.db.count(drafts.DT)
        for payload in [{},dict(details=dict(effective_start=today(),effective_end=today(),scope='<p><br></p>'),client=dict(country='Pakistan',customer_type='Company'),terms=dict(billing_model='Daily',agreement_currency='PKR'),staffing=[],sites=[])]:
            self.assertTrue(drafts.save('Agreement',payload,client_key='empty')['skipped'])
        self.assertEqual(before,frappe.db.count(drafts.DT))
        saved=drafts.save('Agreement',dict(details=dict(agreement_title='First actual detail')),client_key='empty')
        self.assertTrue(saved['name'])
        # Clearing a previously saved draft must not silently delete it.
        self.assertEqual(drafts.save('Agreement',{},name=saved['name'],revision=saved['revision'])['name'],saved['name'])

    def test_partial_new_client_contact_is_a_meaningful_draft(self):
        saved=drafts.save('Agreement',dict(client_mode='Add new client',client=dict(phone='0300123')),client_key='phone')
        self.assertEqual(drafts.load(saved['name'])['payload']['client']['phone'],'0300123')

    def test_site_suggestions_include_sites_without_crew_and_typed_client_name(self):
        a=self.agreement();site=insert('PP Site',project=a['project'],site_name='Reception only',city='Lahore',address_line1='12 Main Road')
        rows=planning.recent_sites(customer_name=self.f.customer.customer_name)
        found=next(r for r in rows if r['site']==site.name)
        self.assertEqual(found['customer'],self.f.customer.name);self.assertFalse(found['has_plan']);self.assertEqual(found['city'],'Lahore')
        self.assertTrue(any(r['has_plan'] for r in rows))
        with patch('plus_point.operations.company',return_value=frappe._dict(name='Other company')):
            self.assertEqual(planning.recent_sites(customer_name=self.f.customer.customer_name),[])
        self.assertEqual(planning.recent_sites(),[])

    def test_native_assignment_rejects_same_dates_at_a_different_site(self):
        site=insert('PP Site',project=self.f.project.name,site_name='Second location')
        with self.assertRaisesRegex(frappe.ValidationError,'already booked'):
            insert('PP Assignment',employee=self.f.employee.name,project=self.f.project.name,contract_terms=self.f.terms.name,site=site.name,start_date=today(),end_date=today(),wage_rate=2000,client_rate=3000)

    def test_cross_event_booking_refused_and_next_unbooked_day_allowed(self):
        a=self.agreement();event=self.event(a);op.auto_assign(event)
        second=self.agreement(title='Different event agreement');site=op.agreement(second['name'])['venues'][0].name
        with self.assertRaisesRegex(frappe.ValidationError,'already booked'):
            insert('PP Assignment',employee=self.worker.name,project=second['project'],contract_terms=second['name'],site=site,start_date=add_days(today(),4),end_date=add_days(today(),4),wage_rate=1000,client_rate=1500)
        insert('PP Assignment',employee=self.worker.name,project=second['project'],contract_terms=second['name'],site=site,start_date=add_days(today(),5),end_date=add_days(today(),5),wage_rate=1000,client_rate=1500)
        self.assertIn(self.worker.name,op.worker_filter('Assigned'));self.assertNotIn(self.worker.name,op.worker_filter('Available'))

    def test_selected_unused_bookings_release_without_a_form(self):
        event=self.event();allocation=op.auto_assign(event)['assignments'][0]
        review=actions.review('PP Event Plan',event);self.assertEqual(review['resolution'],'event')
        self.assertEqual(actions.event_review(event)['workers'][0]['outstanding'],'0')
        actions.release_event_assignments(event,[allocation]);actions.remove('PP Event Plan',event)
        self.assertFalse(frappe.db.exists('PP Event Plan',event));self.assertFalse(frappe.db.exists('PP Assignment',allocation))

    def test_release_rejects_other_event_atomically(self):
        event=self.event();allocation=op.auto_assign(event)['assignments'][0]
        with self.assertRaises(frappe.PermissionError):actions.release_event_assignments(event,[allocation,self.f.assignment.name])
        self.assertTrue(frappe.db.exists('PP Assignment',allocation))

    def test_recorded_attendance_is_preserved_and_only_approved_wages_can_be_paid(self):
        event=self.event();allocation=op.auto_assign(event)['assignments'][0]
        work=insert('PP Work Entry',assignment=allocation,work_date=today(),units=1,status='Draft')
        before=frappe.db.count('Payment Entry')
        with self.assertRaises(frappe.ValidationError):actions.settle_event_crew(event,[self.worker.name],self.f.company.default_cash_account,today(),'No planned wages',balances={self.worker.name:0})
        self.assertEqual(before,frappe.db.count('Payment Entry'))
        with self.assertRaises(frappe.ValidationError):actions.release_event_assignments(event,[allocation])
        work.status='Approved';work.save()
        rows=actions.event_review(event)['workers'];worker=next(r for r in rows if r['employee']==self.worker.name)
        self.assertEqual(worker['outstanding'],'1000.00')
        with self.assertRaisesRegex(frappe.ValidationError,'balance changed'):actions.settle_event_crew(event,[self.worker.name],self.f.company.default_cash_account,today(),'Stale balance',balances={self.worker.name:999})
        self.assertEqual(before,frappe.db.count('Payment Entry'))
        paid=actions.settle_event_crew(event,[self.worker.name],self.f.company.default_cash_account,today(),'Confirmed crew payment',balances={self.worker.name:1000})
        self.assertEqual(actions.settle_event_crew(event,[self.worker.name],self.f.company.default_cash_account,today(),'Confirmed crew payment',balances={self.worker.name:1000}),paid)
        self.assertEqual(frappe.get_doc('Payment Entry',paid['payments'][0]).docstatus,1)
        self.assertEqual(actions.event_review(event)['workers'][0]['outstanding'],'0')
        actions.cancel_event(event)
        self.assertTrue(frappe.db.exists('PP Work Entry',work.name));self.assertTrue(frappe.db.exists('PP Event Plan',event))
        self.assertEqual(frappe.db.get_value('Project',frappe.get_doc('PP Event Plan',event).project,'status'),'Cancelled')
        self.assertEqual(str(frappe.db.get_value('PP Assignment',allocation,'end_date')),today())

    def test_cancellation_releases_unused_slots_and_retains_unpaid_earnings(self):
        event=self.event();allocation=op.auto_assign(event)['assignments'][0]
        work=insert('PP Work Entry',assignment=allocation,work_date=today(),units=.5,status='Draft');work.status='Approved';work.save()
        actions.cancel_event(event)
        self.assertEqual(actions.event_review(event)['workers'][0]['outstanding'],'500.00')
        self.assertTrue(actions.review('PP Event Plan',event)['blocked'])

    def test_worker_profile_and_bulk_pay_recheck_slots_and_use_monthly_profiles(self):
        from plus_point import benefits
        event=self.event();allocation=op.auto_assign(event)['assignments'][0]
        positions=benefits.event_positions(self.worker.name,event)
        self.assertTrue(positions['booked']);self.assertEqual(positions['positions'],[])
        with self.assertRaises(frappe.ValidationError):benefits.assign_event(self.worker.name,event,extra=1)
        frappe.db.set_value('Employee',self.worker.name,'pp_monthly_rate',9000)
        planning.save_pay_batch(event,[allocation],'Monthly')
        saved=frappe.get_doc('PP Assignment',allocation)
        self.assertEqual(saved.pp_pay_amount,9000);self.assertEqual(saved.wage_rate,300)
        insert('PP Work Entry',assignment=allocation,work_date=today(),units=1,status='Draft')
        with self.assertRaises(frappe.ValidationError):planning.save_pay_batch(event,[allocation],'Daily',1000)
        self.assertEqual(frappe.get_doc('PP Assignment',allocation).pp_pay_basis,'Monthly')

    def test_equipment_profile_uses_native_prices_without_posting_finances(self):
        from plus_point import resources
        import uuid
        item=insert('Item',item_code='Event chairs QA '+uuid.uuid4().hex[:8],item_name='Padded event chair',item_group='Services',stock_uom='Nos',is_stock_item=1)
        before=frappe.db.count('Sales Invoice')
        resources.save_equipment_rate(item.name,25)
        data=resources.equipment_profile(item.name)
        self.assertEqual(data['uom'],'Nos');self.assertEqual(data['daily_rate'],'25.0')
        self.assertTrue(frappe.db.exists('Item Price',{'item_code':item.name,'price_list':'Event daily hire PKR'}))
        self.assertEqual(frappe.db.count('Sales Invoice'),before)
        with self.assertRaises(frappe.ValidationError):resources.save_equipment_rate(item.name,-1)
        warehouse=frappe.db.get_value('Warehouse',{'company':self.f.company.name,'is_group':0},'name')
        resources.count_stock(warehouse,item.name,10,50,today())
        event=self.event();doc=frappe.get_doc('PP Event Plan',event)
        booking=resources.save_booking(doc.project,'equipment',dict(site=doc.staffing[0].site,warehouse=warehouse,item=item.name,quantity=3,start_date=today(),end_date=today(),status='Planned'))
        stock=next(r for r in resources.equipment_profile(item.name)['stock'] if r['warehouse']==warehouse)
        self.assertEqual(float(stock['on_hand']),10);self.assertEqual(float(stock['reserved']),3);self.assertEqual(float(stock['available']),7)
        with self.assertRaises(frappe.ValidationError):resources.bulk_bookings([dict(kind='equipment',name=booking['name'])],dict(end_date=add_days(today(),-1)))
        self.assertEqual(frappe.db.get_value('PP Equipment Booking',booking['name'],'status'),'Planned')
        resources.bulk_bookings([dict(kind='equipment',name=booking['name'])],dict(status='Cancelled'))
        stock=next(r for r in resources.equipment_profile(item.name)['stock'] if r['warehouse']==warehouse)
        self.assertEqual(float(stock['available']),10)


    def test_completion_payment_is_one_bounded_period_with_payment_terms(self):
        from plus_point.daily_billing import periods
        rows=periods('2026-10-29','2027-02-12','Completion',7)
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['from_date'],rows[0]['to_date'],rows[0]['due_date']),('2026-10-29','2027-02-12','2027-02-19'))
        self.assertEqual(rows[0]['title'],'Pay after completion')
        for frequency in ('Daily','Weekly','Biweekly','Monthly','Quarterly'):
            rows=periods('2026-10-29','2027-02-12',frequency)
            self.assertEqual(rows[-1]['to_date'],'2027-02-12')

    def test_role_auto_preview_is_read_only_and_custom_daily_rate_is_confirmed(self):
        event=self.event();doc=frappe.get_doc('PP Event Plan',event);role=doc.staffing[0].name
        settings={role:dict(basis='Daily',amount=125)}
        before=frappe.db.count('PP Assignment',{'project':doc.project})
        preview=op.auto_assign_preview(event,[role],settings)
        self.assertEqual(before,frappe.db.count('PP Assignment',{'project':doc.project}))
        self.assertTrue(preview['assignments'])
        self.assertTrue(all(r['requirement']==role and r['pp_pay_amount']==125 for r in preview['assignments']))
        saved=op.auto_assign(event,requirements=[role],payments=settings,expected=preview['snapshot'])
        self.assertTrue(saved['assignments'])
        self.assertTrue(all(frappe.db.get_value('PP Assignment',k,'wage_rate')==125 for k in saved['assignments']))

    def test_role_auto_monthly_uses_profile_and_rejects_foreign_roles(self):
        event=self.event();doc=frappe.get_doc('PP Event Plan',event);role=doc.staffing[0].name
        worker=frappe.get_doc('Employee',self.worker.name);worker.pp_monthly_rate=3000;worker.save()
        preview=op.auto_assign_preview(event,[role],{role:dict(basis='Monthly')})
        mine=next(r for r in preview['assignments'] if r['employee']==worker.name)
        self.assertEqual(mine['pp_pay_amount'],3000);self.assertEqual(mine['wage_rate'],100)
        with self.assertRaises(frappe.ValidationError):op.auto_assign_preview(event,['unknown-role'],{})
        with self.assertRaises(frappe.ValidationError):op.auto_assign_preview(event,[role],{role:dict(basis='Monthly',amount=20)})
        with self.assertRaises(frappe.ValidationError):op.auto_assign_preview(event,[role],{role:dict(basis='Daily',amount=-5)})

    def test_auto_preview_changed_pay_requires_new_review(self):
        event=self.event();doc=frappe.get_doc('PP Event Plan',event);role=doc.staffing[0].name
        preview=op.auto_assign_preview(event,[role],{role:dict(basis='Daily',amount=125)})
        with self.assertRaises(frappe.ValidationError):op.auto_assign(event,requirements=[role],payments={role:dict(basis='Daily',amount=126)},expected=preview['snapshot'])
        self.assertFalse(frappe.db.exists('PP Assignment',{'project':doc.project}))

    def test_auto_selection_is_scoped_to_requested_role(self):
        event=self.event();doc=frappe.get_doc('PP Event Plan',event)
        existing=doc.staffing[0]
        doc.append('staffing',dict(site=existing.site,designation='Driver',phase=existing.phase,start_date=existing.start_date,end_date=existing.end_date,workers_required=1,wage_rate=100,client_rate=200));doc.save()
        role=next(r for r in doc.staffing if r.designation=='Driver')
        result=op.auto_assign_preview(event,[role.name],{role.name:dict(basis='Daily',amount=100)})
        self.assertFalse(result['assignments'])
        self.assertEqual(result['shortages'][0]['designation'],'Driver')
        self.assertEqual(result['shortages'][0]['missing'],1)


    def test_customer_completion_requires_payment_terms_without_changing_native_draft_work(self):
        from plus_point.daily_billing import periods
        event=self.event();doc=frappe.get_doc('PP Event Plan',event)
        with self.assertRaises(frappe.ValidationError):op.save_project(event,dict(complete=1,require_payment_plan=1))
        terms=frappe.get_doc('PP Contract Terms',doc.contract_terms)
        terms.pp_daily_checkpoints=frappe.as_json(periods(terms.effective_start,terms.effective_end,'Completion'));terms.save()
        self.assertEqual(op.save_project(event,dict(complete=1,require_payment_plan=1))['name'],event)
        fixed=self.agreement('Fixed payment validation',fixed=True);terms=frappe.get_doc('PP Contract Terms',fixed['name'])
        with self.assertRaises(frappe.ValidationError):op.require_payments(terms)
        op.save_milestone(terms.name,dict(milestone_title='Pay after completion',due_date=terms.effective_end,amount=10000,status='Planned'))
        op.require_payments(terms)


    def test_ongoing_master_uses_dated_event_payment_terms(self):
        from plus_point import agreement_events as ae
        from plus_point.daily_billing import periods
        master=op.save_agreement(dict(customer=self.f.customer.name,agreement_title='Ongoing service',scope='Services on request',effective_start=today(),validity_mode='Ongoing',resource_mode='Per event',billing_model='Daily',status='Active',require_payment_plan=1))
        result=ae.create_event(agreement=master['name'],event_name='Dated occurrence',start_date=today(),end_date=add_days(today(),2))
        plan=op.plan(result['name']);self.assertTrue(plan['event_payment_terms']);self.assertFalse(plan['payment_plan_defined'])
        terms=frappe.get_doc('PP Contract Terms',result['contract_terms'])
        with self.assertRaises(frappe.ValidationError):op.require_payments(terms)
        ae.save_schedule(result['name'],periods(today(),add_days(today(),2),'Completion'))
        terms.reload();op.require_payments(terms);self.assertTrue(op.plan(result['name'])['payment_plan_defined'])


    def test_event_snapshot_blocker_routes_to_its_event_profile(self):
        from plus_point import agreement_events as ae
        master=self.agreement()
        event=ae.create_event(agreement=master['name'],event_name='Linked delivery',start_date=today(),end_date=add_days(today(),2))
        links=[dict(reference_doctype='PP Contract Terms',reference_docname=event['contract_terms'])]
        with patch('frappe.model.delete_doc.get_linked_docs',return_value=links),patch('frappe.model.delete_doc.get_dynamic_linked_docs',return_value=[]):
            review=actions.review('PP Contract Terms',master['name'])
        self.assertEqual(review['dependency']['doctype'],'PP Event Plan')
        self.assertEqual(review['dependency']['name'],event['name'])
