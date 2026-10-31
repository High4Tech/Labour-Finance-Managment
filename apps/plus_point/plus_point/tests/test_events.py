"""Real event/date/resource/stock integration, with every fixture rolled back."""
import base64,csv,io,json,unittest,uuid
from unittest.mock import patch
from decimal import Decimal
import frappe
from frappe.utils import today,add_days
from plus_point import events,imports,event_setup
from plus_point.tests.test_operations import fixture,insert


class EventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user('Administrator');cls.old_entitlement=frappe.flags.get('pp_test_entitlement')
        frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
        frappe.db.savepoint('pp_events_suite');cls.f=fixture('PP Events QA '+uuid.uuid4().hex[:6])
        cls.f.assignment.end_date=today();cls.f.assignment.save()
        cls.worker=insert('Employee',first_name='Ayesha Events QA',gender='Female',date_of_birth='1992-01-01',
            date_of_joining='2020-01-01',company=cls.f.company.name,status='Active')
        cls.old_default=frappe.defaults.get_user_default('Company');cls.old_selected=frappe.defaults.get_user_default(event_setup.SELECTED)

    @classmethod
    def tearDownClass(cls):
        frappe.set_user('Administrator');frappe.db.rollback(save_point='pp_events_suite')
        frappe.flags.pp_test_entitlement=cls.old_entitlement
        frappe.defaults.set_user_default('Company',cls.old_default);frappe.defaults.set_user_default(event_setup.SELECTED,cls.old_selected)
        frappe.clear_cache()

    def setUp(self):frappe.set_user('Administrator');frappe.db.savepoint('pp_events_case')
    def tearDown(self):frappe.set_user('Administrator');frappe.db.rollback(save_point='pp_events_case');frappe.clear_cache()

    def event(self,headcount=1,start=None,end=None):
        start=start or add_days(today(),2);end=end or add_days(start,2)
        return events.create_event(self.f.company.name,self.f.customer.name,'QA Event '+uuid.uuid4().hex[:6],start,end,
            'Temporary event setup and staffing agreement','Daily',100,150,sites=[dict(site_name='QA Hall A',phase='Event',
            start_date=start,end_date=end,workers_required=headcount)])

    def vehicle(self,seats=3,capacity=100):
        return insert('Vehicle',license_plate='QA-'+uuid.uuid4().hex[:7],make='Toyota',model='Crew van',company=self.f.company.name,
            fuel_type='Diesel',uom='Litre',last_odometer=0,pp_crew_seats=seats,pp_cargo_capacity=capacity,pp_cargo_uom='units',pp_event_enabled=1)

    def equipment(self,qty=12):
        item=insert('Item',item_code='QA-CHAIR-'+uuid.uuid4().hex[:6],item_name='Event chair QA',item_group='Services',stock_uom='Nos',is_stock_item=1)
        warehouse=frappe.db.get_value('Warehouse',{'company':self.f.company.name,'is_group':0},'name')
        from plus_point.event_imports import save
        reconciliation=save('stock_balances',self.f.company.name,dict(date=today(),item_code=item.name,warehouse=warehouse,quantity=str(qty),valuation_rate='100'))
        return item,warehouse,reconciliation

    @patch('plus_point.resources.company')
    def test_inline_stock_updates_keep_valuation_and_reject_stale_or_partial_batches(self,business):
        from plus_point import resources
        business.return_value=self.f.company
        item,warehouse,_=self.equipment(12)
        result=resources.update_stock(warehouse,[dict(item=item.name,quantity=15,expected_quantity=12)])
        doc=frappe.get_doc('Stock Reconciliation',result['name'])
        self.assertEqual(doc.items[0].valuation_rate,100)
        self.assertEqual(str(doc.posting_date),today());self.assertEqual(doc.docstatus,1)
        self.assertTrue(result['updated_at'])
        with self.assertRaises(frappe.ValidationError):resources.update_stock(warehouse,[dict(item=item.name,quantity=16,expected_quantity=12)])
        second=insert('Item',item_code='QA-ZERO-'+uuid.uuid4().hex[:6],item_name='Quantity only equipment',item_group='Services',stock_uom='Nos',is_stock_item=1)
        resources.attach_item(warehouse,second.name)
        with self.assertRaises(frappe.ValidationError):resources.update_stock(warehouse,[dict(item=item.name,quantity=18,expected_quantity=15),dict(item=second.name,quantity=-1,expected_quantity=0)])
        self.assertEqual(frappe.db.get_value('Bin',{'item_code':item.name,'warehouse':warehouse},'actual_qty'),15)
        saved=resources.update_stock(warehouse,[dict(item=item.name,quantity=18,expected_quantity=15),dict(item=second.name,quantity=4,expected_quantity=0)])
        self.assertEqual(saved['updated'],2)
        doc=frappe.get_doc('Stock Reconciliation',saved['name']);self.assertEqual(len(doc.items),2)
        self.assertEqual(next(r.valuation_rate for r in doc.items if r.item_code==second.name),0)

    @patch('plus_point.resources.company')
    def test_inline_stock_cannot_reduce_future_reservations_and_ownership_is_native(self,business):
        from plus_point import resources
        business.return_value=self.f.company
        item,warehouse,_=self.equipment(12);event=self.event()
        resources.save_booking(event['project'],'equipment',self.booking(event,item=item.name,warehouse=warehouse,quantity=8))
        with self.assertRaises(frappe.ValidationError):resources.update_stock(warehouse,[dict(item=item.name,quantity=7,expected_quantity=12)])
        resources.update_profile('warehouses',warehouse,{'warehouse_type':'Rented'})
        self.assertEqual(frappe.db.get_value('Warehouse',warehouse,'warehouse_type'),'Rented')
        with self.assertRaises(frappe.ValidationError):resources.update_profile('warehouses',warehouse,{'warehouse_type':'Other company'})

    @patch("plus_point.resources.company")
    def test_composed_resources_share_reservations_and_vehicle_status(self,business):
        business.return_value=self.f.company
        from plus_point import resources
        frappe.db.set_single_value('PP Workspace Settings','company',self.f.company.name)
        event=self.event();plan=frappe.get_doc('PP Event Plan',event['plan']);vehicle=self.vehicle()
        values=self.booking(event,vehicle=vehicle.name,purpose='Crew',crew_count=2)
        result=resources.save_booking(event['project'],'vehicle',values)
        from plus_point.operations import plan as event_details
        reservation=next(row for row in event_details(plan.name)['reservations'] if row['name']==result['name'])
        self.assertEqual(reservation['kind'],'vehicle')
        self.assertEqual(reservation['site_id'],values['site'])
        data=resources.overview('vehicles',vehicle.name,plan.start_date,plan.end_date)
        self.assertEqual(data['rows'][0].status,'Assigned')
        self.assertEqual(resources.project_resources(event['project'])['rows'][0].name,result['name'])
        with self.assertRaises(frappe.ValidationError):resources.update_profile('vehicles',vehicle.name,{'pp_event_enabled':0})
        resources.save_booking(event['project'],'vehicle',{'status':'Cancelled'},result['name'])
        self.assertEqual(resources.overview('vehicles',vehicle.name,plan.start_date,plan.end_date)['rows'][0].status,'Available')
        resources.update_profile('vehicles',vehicle.name,{'pp_event_enabled':0})
        self.assertEqual(resources.overview('vehicles',vehicle.name)['rows'][0].status,'Inactive')

    @patch("plus_point.resources.company")
    def test_warehouse_composition_and_reservation_bounds(self,business):
        business.return_value=self.f.company
        from plus_point import resources
        frappe.db.set_single_value('PP Workspace Settings','company',self.f.company.name)
        event=self.event();plan=frappe.get_doc('PP Event Plan',event['plan']);item,warehouse,_=self.equipment(12)
        values=self.booking(event,item=item.name,warehouse=warehouse,quantity=7)
        booking=resources.save_booking(event['project'],'equipment',values)
        data=resources.overview('warehouses',warehouse,plan.start_date,plan.end_date)
        stock=next(r for r in data['stock'] if r['name']==item.name)
        self.assertEqual((stock['on_hand'],stock['reserved'],stock['available']),(12,7,5))
        with self.assertRaises(frappe.ValidationError):resources.save_booking(event['project'],'equipment',dict(values,quantity=6))
        with self.assertRaises(frappe.ValidationError):resources.save_booking(event['project'],'equipment',dict(values,start_date=add_days(plan.start_date,-1)),booking['name'])
        resources.save_booking(event['project'],'equipment',{'status':'Cancelled'},booking['name'])
        self.assertEqual(next(r for r in resources.warehouse_stock(warehouse,plan.start_date,plan.end_date) if r['name']==item.name)['available'],12)
        counted=resources.count_stock(warehouse,item.name,14,100,today())
        self.assertEqual(frappe.db.get_value('Stock Reconciliation',counted['name'],'docstatus'),1)
        self.assertEqual(next(r for r in resources.warehouse_stock(warehouse) if r['name']==item.name)['on_hand'],14)
        self.assertTrue(resources.overview('warehouses',warehouse)['history'])

    @patch("plus_point.resources.company")
    def test_agreement_requirements_cannot_reserve_resources_before_dated_event(self,business):
        business.return_value=self.f.company
        from plus_point import resources
        frappe.db.set_single_value('PP Workspace Settings','company',self.f.company.name)
        vehicle=self.vehicle();args=dict(site=self.f.site.name,vehicle=vehicle.name,purpose='Crew',crew_count=1,start_date=today(),end_date=today(),status='Planned')
        with self.assertRaises(frappe.ValidationError):resources.save_booking(self.f.project.name,'vehicle',args)
        self.assertFalse(frappe.db.exists('PP Vehicle Booking',{'project':self.f.project.name}))
        self.assertFalse(frappe.db.exists('PP Event Plan',{'project':self.f.project.name}))
        with self.assertRaises(frappe.ValidationError):resources.save_booking(self.f.project.name,'vehicle',dict(args,start_date='1900-01-01'))

    def booking(self,result,**values):
        plan=frappe.get_doc('PP Event Plan',result['plan'])
        return dict(project=plan.project,site=plan.staffing[0].site,start_date=plan.start_date,end_date=plan.end_date,status='Planned',**values)

    def preview(self,kind,row):
        out=io.StringIO();writer=csv.writer(out);writer.writerow(imports.SCHEMAS[kind]);writer.writerow([row.get(k,'') for k in imports.SCHEMAS[kind]])
        return imports.preview(kind,self.f.company.name,'events.csv',base64.b64encode(out.getvalue().encode()).decode())

    def test_exact_event_dates_crew_preview_and_no_earnings_until_attendance(self):
        result=self.event(2,start='2026-12-30',end='2027-01-02');plan=result['plan']
        preview=events.preview_crew(plan);self.assertFalse(preview['shortages']);self.assertEqual(len(preview['assignments']),2)
        self.assertFalse(frappe.db.exists('PP Work Entry',{'project':result['project']}))
        self.assertEqual(events.allocate_crew(plan)['created'],2);self.assertEqual(events.allocate_crew(plan)['created'],0)
        timeline=events.timeline(plan);self.assertEqual(timeline['duration'],4)
        self.assertEqual([r['date'] for r in timeline['sites'][0]['days']],['2026-12-30','2026-12-31','2027-01-01','2027-01-02'])
        self.assertTrue(all(r['assigned']==r['required']==2 and r['actual']=='0' for r in timeline['sites'][0]['days']))
        self.assertFalse(frappe.db.exists('PP Work Entry',{'project':result['project']}))

    def test_shortage_and_atomic_invalid_project_creation(self):
        result=self.event(3);before=frappe.db.count('PP Assignment',{'project':result['project']})
        self.assertTrue(events.preview_crew(result['plan'])['shortages'])
        with self.assertRaises(frappe.ValidationError):events.allocate_crew(result['plan'])
        self.assertEqual(frappe.db.count('PP Assignment',{'project':result['project']}),before)
        projects=frappe.db.count('Project');contracts=frappe.db.count('Contract')
        with self.assertRaises(frappe.ValidationError):self.event(0)
        self.assertEqual(frappe.db.count('Project'),projects);self.assertEqual(frappe.db.count('Contract'),contracts)

    def test_vehicle_purpose_capacity_overlap_and_profile_update_guard(self):
        result=self.event();vehicle=self.vehicle(3,100);args=self.booking(result,vehicle=vehicle.name,purpose='Crew',crew_count=3)
        booking=insert('PP Vehicle Booking',**args);self.assertEqual(booking.cargo_load,0)
        with self.assertRaises(frappe.ValidationError):insert('PP Vehicle Booking',**dict(args,crew_count=4))
        with self.assertRaises(frappe.ValidationError):insert('PP Vehicle Booking',**dict(args,purpose='Inventory',cargo_load=101))
        with self.assertRaises(frappe.ValidationError):insert('PP Vehicle Booking',**dict(args,purpose='Inventory',cargo_load=80))
        vehicle.pp_crew_seats=2
        with self.assertRaises(frappe.ValidationError):vehicle.save()
        booking.status='Cancelled';booking.save()
        cargo=insert('PP Vehicle Booking',**dict(args,purpose='Inventory',cargo_load=80))
        self.assertEqual(cargo.crew_count,0);self.assertEqual(cargo.cargo_uom,'units')
        self.assertFalse(frappe.get_meta('PP Vehicle Booking').has_field('item'))
        from plus_point.sections import overview
        data=overview('Inventory and transport',self.f.company.name)
        self.assertEqual(data['resources']['vehicles'],1);self.assertEqual(data['resources']['reservations'],1)

    def test_equipment_uses_native_stock_and_peak_reservations(self):
        item,warehouse,reconciliation=self.equipment();result=self.event();args=self.booking(result,item=item.name,warehouse=warehouse,quantity=7)
        insert('PP Equipment Booking',**args)
        available=events.stock_available(item.name,warehouse,args['start_date'],args['end_date'])
        self.assertEqual(Decimal(available['on_hand']),12);self.assertEqual(Decimal(available['reserved']),7);self.assertEqual(Decimal(available['available']),5)
        with self.assertRaises(frappe.ValidationError):insert('PP Equipment Booking',**dict(args,quantity=6))
        self.assertTrue(frappe.db.exists('GL Entry',{'voucher_type':'Stock Reconciliation','voucher_no':reconciliation.name}))
        before=frappe.db.get_value('Bin',{'item_code':item.name,'warehouse':warehouse},'actual_qty')
        reduced=frappe.get_doc(dict(doctype='Stock Reconciliation',company=self.f.company.name,purpose='Stock Reconciliation',
            posting_date=today(),items=[dict(item_code=item.name,warehouse=warehouse,qty=6,valuation_rate=100)])).insert()
        with self.assertRaises(frappe.ValidationError):reduced.submit()
        self.assertEqual(frappe.db.get_value('Bin',{'item_code':item.name,'warehouse':warehouse},'actual_qty'),before)

    def test_nonoverlapping_equipment_uses_peak_not_total_and_cancel_releases(self):
        item,warehouse,_=self.equipment();result=self.event(start=add_days(today(),2),end=add_days(today(),8));args=self.booking(result,item=item.name,warehouse=warehouse,quantity=10)
        first=insert('PP Equipment Booking',**dict(args,end_date=add_days(today(),4)))
        insert('PP Equipment Booking',**dict(args,start_date=add_days(today(),5)))
        self.assertEqual(Decimal(events.stock_available(item.name,warehouse,args['start_date'],args['end_date'])['reserved']),10)
        first.status='Cancelled';first.save()
        self.assertEqual(Decimal(events.stock_available(item.name,warehouse,args['start_date'],str(add_days(today(),4)))['available']),12)

    def test_native_stock_issue_cannot_consume_reserved_equipment(self):
        item,warehouse,_=self.equipment();result=self.event()
        insert('PP Equipment Booking',**self.booking(result,item=item.name,warehouse=warehouse,quantity=10))
        issue=insert('Stock Entry',stock_entry_type='Material Issue',company=self.f.company.name,
            posting_date=today(),items=[dict(item_code=item.name,s_warehouse=warehouse,qty=3)])
        frappe.db.savepoint('pp_rejected_stock_issue')
        with self.assertRaises(frappe.ValidationError):issue.submit()
        frappe.db.rollback(save_point='pp_rejected_stock_issue');issue.reload()
        self.assertEqual(frappe.db.get_value('Bin',{'item_code':item.name,'warehouse':warehouse},'actual_qty'),12)
        issue.items[0].qty=2;issue.save();issue.submit()
        self.assertEqual(frappe.db.get_value('Bin',{'item_code':item.name,'warehouse':warehouse},'actual_qty'),10)

    def test_unused_crew_release_and_company_boundaries(self):
        result=self.event();events.allocate_crew(result['plan'])
        self.assertEqual(events.release_crew(result['plan'])['released'],1)
        self.assertFalse(frappe.db.get_value('PP Event Plan',result['plan'],'crew_allocated'))
        self.assertEqual(events.allocate_crew(result['plan'])['created'],1)
        vehicle=self.vehicle();other=fixture('PP Other Event QA '+uuid.uuid4().hex[:6])
        vehicle.company=other.company.name;vehicle.save()
        with self.assertRaises(frappe.ValidationError):
            insert('PP Vehicle Booking',**self.booking(result,vehicle=vehicle.name,purpose='Crew',crew_count=1))

    def test_existing_full_phase_crew_is_credited_without_duplicate_assignments(self):
        result=self.event();plan=frappe.get_doc('PP Event Plan',result['plan'])
        manual=insert('PP Assignment',employee=self.worker.name,site=plan.staffing[0].site,project=plan.project,
            contract_terms=plan.contract_terms,start_date=plan.start_date,end_date=plan.end_date,wage_rate=100,client_rate=150)
        preview=events.preview_crew(plan.name)
        self.assertEqual(preview['existing_coverage'],1);self.assertFalse(preview['shortages']);self.assertFalse(preview['assignments'])
        self.assertEqual(events.allocate_crew(plan.name)['created'],0)
        self.assertEqual(events.release_crew(plan.name)['released'],0)
        self.assertTrue(frappe.db.exists('PP Assignment',manual.name))

    def test_generated_crew_can_release_only_before_recorded_work(self):
        result=self.event(start=today(),end=today());events.allocate_crew(result['plan'])
        plan=frappe.get_doc('PP Event Plan',result['plan']);plan.staffing[0].workers_required=2
        plan.save()
        self.assertEqual(frappe.db.count('PP Assignment',{'pp_event_plan':plan.name}),1)
        plan.staffing[0].workers_required=1;plan.crew_allocated=0
        with self.assertRaises(frappe.ValidationError):plan.save()
        assignment=frappe.db.get_value('PP Assignment',{'pp_event_plan':result['plan']},'name')
        work=insert('PP Work Entry',assignment=assignment,work_date=today(),units=1,status='Draft')
        with self.assertRaises(frappe.ValidationError):events.release_crew(result['plan'])
        work.status='Approved';work.save()
        self.assertEqual(Decimal(events.timeline(result['plan'])['sites'][0]['days'][0]['actual']),1)
        with self.assertRaises(frappe.ValidationError):events.release_crew(result['plan'])

    def test_catalog_template_profile_update_replay_and_stock_staleness(self):
        row=dict(external_id='car-'+uuid.uuid4().hex[:8],license_plate='QA-'+uuid.uuid4().hex[:7],make='Toyota',model='Event van',
            crew_seats='6',cargo_capacity='40',cargo_uom='units',fuel_type='Diesel',status='Active')
        preview=self.preview('vehicles',row);self.assertTrue(preview['valid']);saved=imports.apply(preview['token']);name=saved['rows'][0]['document']
        self.assertEqual(imports.apply(preview['token'])['skipped'],1)
        row['crew_seats']='8';updated=self.preview('vehicles',row);self.assertEqual(updated['rows'][0]['action'],'Update');imports.apply(updated['token'])
        self.assertEqual(frappe.db.get_value('Vehicle',name,'pp_crew_seats'),8)
        item,warehouse,_=self.equipment();result=self.event()
        stock=dict(external_id='balance-'+uuid.uuid4().hex[:8],date=today(),item_code=item.name,warehouse=warehouse,quantity='10',valuation_rate='100')
        preview=self.preview('stock_balances',stock);self.assertTrue(preview['valid'])
        insert('PP Equipment Booking',**self.booking(result,item=item.name,warehouse=warehouse,quantity=11))
        with self.assertRaises(frappe.ValidationError):imports.apply(preview['token'])
        self.assertEqual(frappe.db.get_value('Bin',{'item_code':item.name,'warehouse':warehouse},'actual_qty'),12)

    def test_company_setup_persists_each_step_without_creating_attendance(self):
        company=self.f.company.name;frappe.defaults.set_user_default(event_setup.SELECTED,company)
        frappe.db.set_value('Company',company,'pp_event_setup_state',json.dumps(dict(company=company,step='company',required=True)))
        event_setup.advance('company',{'company':company});event_setup.advance('client',{'customer':self.f.customer.name})
        state=event_setup.advance('event',dict(event_name='Guided QA '+uuid.uuid4().hex[:5],site_name='QA Venue',start_date=add_days(today(),3),end_date=add_days(today(),5)))
        project=state['project'];event_setup.advance('terms',dict(agreement='Temporary event agreement',billing_model='Daily'))
        event_setup.advance('workers',dict(employee=self.worker.name));event_setup.advance('plan',dict(wage_rate=100,client_rate=150,workers_required=1))
        event_setup.advance('vehicle',dict(no_vehicle=1));event_setup.advance('inventory',dict(no_equipment=1));final=event_setup.advance('allocate',{})
        self.assertEqual(final['step'],'done');self.assertFalse(event_setup.status()['required'])
        self.assertEqual(json.loads(frappe.db.get_value('Company',company,'pp_event_setup_state'))['project'],project)
        self.assertFalse(frappe.db.exists('PP Work Entry',{'project':project}))

    def test_guest_and_platform_are_denied_event_operations(self):
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):events.inventory(self.f.company.name)
        frappe.set_user('Administrator')
        from unittest.mock import patch
        with patch.dict(frappe.conf,{'pp_control_plane':True}):
            with self.assertRaises(frappe.PermissionError):events.inventory(self.f.company.name)

    def test_company_owner_can_create_catalog_without_staff_accounts(self):
        owner=insert('User',email='event-owner-'+uuid.uuid4().hex[:8]+'@example.invalid',first_name='Event Company QA',
            enabled=1,send_welcome_email=0,roles=[dict(role='System Manager'),dict(role='Stock Manager'),dict(role='Accounts Manager')])
        frappe.set_user(owner.name)
        for doctype in ('Customer','Vehicle','Item','Item Group','Warehouse'):
            self.assertTrue(frappe.has_permission(doctype,'create'),doctype)
        client=events.save_resource('clients',self.f.company.name,dict(customer_name='Organizer client QA',customer_type='Company',contact_name='Sana Ali',email='sana@example.invalid',country='Pakistan',city='Lahore',address_line1='12 Garden Road'))
        self.assertTrue(client['name'])
        item=events.save_resource('inventory_items',self.f.company.name,dict(item_code='QA-OWNER-'+uuid.uuid4().hex[:6],item_name='Event light QA',stock_uom='Nos',status='Active'))
        self.assertTrue(item['name'])

    def test_full_guide_posts_stock_books_transport_and_allocates_multiple_venues(self):
        company=self.f.company.name;frappe.defaults.set_user_default(event_setup.SELECTED,company)
        frappe.db.set_value('Company',company,'pp_event_setup_state',json.dumps(dict(company=company,step='company',required=True)))
        start=add_days(today(),3);end=add_days(start,2)
        event_setup.advance('company',{'company':company});event_setup.advance('client',{'customer':self.f.customer.name})
        state=event_setup.advance('event',dict(event_name='Full guide QA '+uuid.uuid4().hex[:5],site_name='Main stage QA',start_date=start,end_date=end))
        event_setup.advance('terms',dict(agreement='Temporary event agreement',billing_model='Daily'))
        event_setup.advance('workers',dict(employee=self.worker.name))
        event_setup.advance('plan',dict(wage_rate=100,client_rate=150,staffing=[
            dict(site=state['site'],phase='Setup',start_date=start,end_date=start,workers_required=1),
            dict(site_name='Second venue QA',phase='Event',start_date=add_days(start,1),end_date=end,workers_required=1)]))
        vehicle=self.vehicle()
        event_setup.advance('vehicle',dict(vehicle=vehicle.name,purpose='Crew',crew_count=1))
        code='QA-GUIDE-EQUIPMENT-'+uuid.uuid4().hex[:6]
        state=event_setup.advance('inventory',dict(item_code=code,item_name='Portable event light QA',stock_uom='Nos',
            warehouse_name='Guide equipment QA',quantity=2,set_stock_balance=1,confirm_stock_balance=1,stock_quantity=5,valuation_rate=100))
        self.assertTrue(frappe.db.exists('PP Vehicle Booking',state['vehicle_booking']))
        self.assertEqual(Decimal(events.stock_available(code,state['warehouse'],start,end)['available']),3)
        final=event_setup.advance('allocate',{})
        self.assertEqual(final['step'],'done');self.assertEqual(len(events.timeline(final['plan'])['sites']),2)
        self.assertEqual(frappe.db.count('PP Assignment',{'pp_event_plan':final['plan']}),2)
        self.assertFalse(frappe.db.exists('PP Work Entry',{'project':final['project']}))

    def inventory_step(self):
        result=self.event();plan=frappe.get_doc('PP Event Plan',result['plan']);company=self.f.company.name
        frappe.defaults.set_user_default(event_setup.SELECTED,company)
        frappe.db.set_value('Company',company,'pp_event_setup_state',json.dumps(dict(company=company,step='inventory',
            required=True,project=plan.project,site=plan.staffing[0].site,plan=plan.name,
            customer=self.f.customer.name,contract_terms=plan.contract_terms,billing_model=frappe.db.get_value('PP Contract Terms',plan.contract_terms,'billing_model'),
            start_date=str(plan.start_date),end_date=str(plan.end_date))))
        return dict(item_code='QA-NEW-STOCK-'+uuid.uuid4().hex[:7],item_name='Palm decoration QA',stock_uom='Nos',
            warehouse_name='New equipment QA '+uuid.uuid4().hex[:5],stock_quantity=5,quantity=2,valuation_rate=100,confirm_stock_balance=1)

    def test_new_setup_item_records_stock_and_reserves_without_hidden_opt_in(self):
        values=self.inventory_step()
        state=event_setup.advance('inventory',values)
        self.assertEqual(state['step'],'allocate')
        available=events.stock_available(state['item'],state['warehouse'],state['start_date'],state['end_date'])
        self.assertEqual({key:Decimal(value) for key,value in available.items()},
            dict(on_hand=Decimal(5),reserved=Decimal(2),available=Decimal(3)))
        self.assertTrue(frappe.db.exists('Stock Ledger Entry',{'item_code':values['item_code'],'warehouse':state['warehouse']}))
        reconciliation=frappe.db.get_value('Stock Reconciliation Item',{'item_code':values['item_code']},'parent')
        self.assertTrue(frappe.db.exists('GL Entry',{'voucher_type':'Stock Reconciliation','voucher_no':reconciliation}))

    def test_missing_short_or_unconfirmed_starting_stock_creates_nothing(self):
        values=self.inventory_step()
        counts={dt:frappe.db.count(dt) for dt in ('Item','Warehouse','Stock Reconciliation','Stock Ledger Entry','GL Entry','PP Equipment Booking')}
        for overrides,message in [({'stock_quantity':None},'starting warehouse quantity'),
                ({'stock_quantity':1},'this event needs'),({'confirm_stock_balance':0},'Confirm the warehouse')]:
            with self.assertRaisesRegex(frappe.ValidationError,message):event_setup.advance('inventory',{**values,**overrides})
            self.assertEqual(event_setup.current()['step'],'inventory')
            for dt,count in counts.items():self.assertEqual(frappe.db.count(dt),count,dt)

    def test_existing_setup_item_uses_stock_without_reposting_count(self):
        values=self.inventory_step();item,warehouse,_=self.equipment(5)
        count=frappe.db.count('Stock Reconciliation')
        state=event_setup.advance('inventory',dict(item=item.name,warehouse=warehouse,quantity=2))
        self.assertEqual(state['step'],'allocate');self.assertEqual(frappe.db.count('Stock Reconciliation'),count)
        self.assertEqual(Decimal(events.stock_available(item.name,warehouse,state['start_date'],state['end_date'])['available']),3)

    def test_add_new_cannot_overwrite_existing_equipment_or_stock(self):
        values=self.inventory_step();item,warehouse,_=self.equipment(5)
        with self.assertRaisesRegex(frappe.ValidationError,'code already exists'):
            event_setup.advance('inventory',{**values,'item_code':item.name,'warehouse':warehouse,'stock_quantity':10})
        item.reload();self.assertEqual(item.item_name,'Event chair QA')
        self.assertEqual(Decimal(frappe.db.get_value('Bin',{'item_code':item.name,'warehouse':warehouse},'actual_qty')),5)

    def test_quantity_only_inventory_allows_explicit_zero_value(self):
        values=self.inventory_step();values['valuation_rate']=0
        state=event_setup.advance('inventory',values)
        self.assertEqual(Decimal(events.stock_available(state['item'],state['warehouse'],state['start_date'],state['end_date'])['available']),3)
        self.assertEqual(frappe.db.get_value('Stock Reconciliation Item',{'item_code':state['item']},'allow_zero_valuation_rate'),1)

    def test_country_sets_currency_including_sar_and_accepts_manual_override(self):
        from plus_point.locations import country_defaults
        for country,currency in [('Saudi Arabia','SAR'),('Pakistan','PKR'),('United Arab Emirates','AED'),('United States','USD')]:
            self.assertEqual(country_defaults(country)['currency'],currency)
        company=self.f.company.name;frappe.defaults.set_user_default(event_setup.SELECTED,company)
        frappe.db.set_value('Company',company,'pp_event_setup_state',json.dumps(dict(company=company,step='company',required=True)))
        frappe.db.set_value('Currency','SAR','enabled',0)
        state=event_setup.advance('company',dict(company_name='Saudi events QA '+uuid.uuid4().hex[:5],abbr=uuid.uuid4().hex[:5],country='Saudi Arabia',currency='USD'))
        self.assertEqual(frappe.db.get_value('Company',state['company'],'default_currency'),'USD')
        self.assertEqual(frappe.db.get_value('Currency','USD','enabled'),1)

    def test_new_client_requires_details_and_saves_native_contact_address(self):
        from plus_point.clients import create,details
        before=frappe.db.count('Customer');companies_before=frappe.db.count('Company')
        with self.assertRaisesRegex(frappe.ValidationError,'contact person'):create(dict(customer_name='Name only QA'))
        self.assertEqual(frappe.db.count('Customer'),before)
        client=create(dict(customer_name='Cedar events QA '+uuid.uuid4().hex[:5],contact_name='Ayesha Malik',email='ayesha@example.invalid',
            phone='+966501234567',country='Saudi Arabia',state='Riyadh',city='Riyadh',address_line1='12 Exhibition Road',postal_code='12345'))
        data=details(client.name);self.assertEqual(data['email'],'ayesha@example.invalid');self.assertIn('Riyadh',data['address'])
        self.assertEqual(frappe.db.get_value('Address',client.customer_primary_address,'country'),'Saudi Arabia')
        self.assertEqual(frappe.db.count('Company'),companies_before)

    def test_unposted_company_country_change_updates_base_accounts(self):
        from plus_point.locations import set_company_country
        company=insert('Company',company_name='Country change QA '+uuid.uuid4().hex[:5],abbr=uuid.uuid4().hex[:5],country='Pakistan',default_currency='PKR')
        set_company_country(company,'Saudi Arabia')
        self.assertEqual(company.default_currency,'SAR')
        self.assertEqual(frappe.db.get_value('Account',company.default_cash_account,'account_currency'),'SAR')
        existing=frappe.get_doc('Company',self.f.company.name);original=existing.default_currency
        set_company_country(existing,'Saudi Arabia')
        self.assertEqual(existing.country,'Saudi Arabia');self.assertEqual(existing.default_currency,original)

    def test_completed_steps_can_be_revisited_without_losing_frontier(self):
        self.inventory_step();before=event_setup.current()
        state=event_setup.control('go',step='client');self.assertEqual(state['step'],'client')
        self.assertEqual(event_setup.status()['furthest'],event_setup.STEPS.index('inventory'))
        state=event_setup.control('go',step='terms');self.assertEqual(state['contract_terms'],before['contract_terms'])
        self.assertTrue(event_setup.status()['values']['agreement'])
        with self.assertRaisesRegex(frappe.ValidationError,'earlier steps'):event_setup.control('go',step='allocate')
        state=event_setup.control('go',step='inventory');self.assertEqual(state['project'],before['project'])

    def test_onboarding_edits_client_and_agreement_in_place(self):
        from plus_point.clients import create,details
        client=create(dict(customer_name='Edit client QA '+uuid.uuid4().hex[:6],contact_name='Ayesha Malik',email='first@example.invalid',
            country='Saudi Arabia',city='Riyadh',address_line1='12 Road'))
        company=self.f.company.name;frappe.defaults.set_user_default(event_setup.SELECTED,company)
        event_setup.persist(dict(company=company,step='client',required=True,customer=client.name))
        count=frappe.db.count('Customer');contacts=frappe.db.count('Contact');addresses=frappe.db.count('Address')
        event_setup.advance('client',dict(customer=client.name,edit_client=1,customer_name=client.customer_name,contact_name='Haris Khan',
            email='updated@example.invalid',phone='+966501111111',country='Saudi Arabia',city='Jeddah',address_line1='24 Road'))
        data=details(client.name);self.assertEqual(data['contact_name'],'Haris Khan');self.assertEqual(data['city'],'Jeddah')
        self.assertEqual((frappe.db.count('Customer'),frappe.db.count('Contact'),frappe.db.count('Address')),(count,contacts,addresses))
        event_setup.advance('event',dict(event_name='Editable event QA',site_name='Editable venue QA',start_date=add_days(today(),2),end_date=add_days(today(),4)))
        state=event_setup.advance('terms',dict(agreement='Original scope',billing_model='Daily'));name=state['contract_terms']
        event_setup.control('go',step='terms')
        state=event_setup.advance('terms',dict(contract_terms=name,edit_terms=1,agreement='Revised scope',billing_model='Daily'))
        self.assertEqual(state['contract_terms'],name)
        terms=frappe.get_doc('PP Contract Terms',name);self.assertEqual(frappe.db.get_value('Contract',terms.contract,'contract_terms'),'Revised scope')

    def test_structured_venue_rejects_missing_city_and_invalid_map_points(self):
        from plus_point.locations import site_values
        with self.assertRaisesRegex(frappe.ValidationError,'city'):site_values(dict(country='Saudi Arabia',address_line1='12 Road'))
        for lat,lon in [('nan','2'),('91','0'),('0','181'),('1','')]:
            with self.assertRaises(frappe.ValidationError):site_values(dict(country='Saudi Arabia',city='Riyadh',address_line1='12 Road',latitude=lat,longitude=lon))
        values=site_values(dict(country='Saudi Arabia',city='Riyadh',state='Riyadh',address_line1='12 Road',latitude='24.7136',longitude='46.6753'))
        site=insert('PP Site',project=self.f.project.name,site_name='Riyadh venue QA',**values)
        self.assertEqual(site.country,'Saudi Arabia');self.assertIn('Riyadh',site.address);self.assertEqual(float(site.latitude),24.7136)

    def test_skip_and_resume_preserve_saved_event_step(self):
        values=self.inventory_step();before=event_setup.current()
        skipped=event_setup.control('skip');self.assertTrue(skipped['skipped']);self.assertFalse(event_setup.status()['required'])
        resumed=event_setup.control('resume');self.assertFalse(resumed['skipped']);self.assertTrue(event_setup.status()['required'])
        self.assertEqual(resumed['step'],'inventory');self.assertEqual(resumed['project'],before['project'])

    def test_skip_before_business_creation_is_saved_without_creating_company(self):
        from unittest.mock import patch
        before=frappe.db.count('Company')
        frappe.db.set_single_value('PP Workspace Settings','onboarding_state',None)
        with patch('plus_point.event_setup.companies',return_value=[]):
            skipped=event_setup.control('skip');self.assertTrue(skipped['skipped']);self.assertFalse(event_setup.status()['required'])
            self.assertEqual(event_setup.control('resume')['step'],'company');self.assertTrue(event_setup.status()['required'])
        self.assertEqual(frappe.db.count('Company'),before)

    def test_customer_subscription_cannot_create_second_company(self):
        from unittest.mock import patch
        with patch('plus_point.workspace.fixture_context',return_value=False):
            frappe.db.set_single_value('PP Workspace Settings','company',self.f.company.name)
            with self.assertRaisesRegex(frappe.ValidationError,'one company workspace'):
                insert('Company',company_name='Extra company forbidden QA',abbr='EXQA',country='Pakistan',default_currency='PKR')
            self.assertEqual([c.name for c in event_setup.companies()],[self.f.company.name])

    def test_vehicle_setup_only_requires_capacity_for_its_purpose(self):
        values=self.inventory_step();company=self.f.company.name
        state=event_setup.current();state['step']='vehicle';event_setup.persist(state)
        saved=event_setup.advance('vehicle',dict(purpose='Inventory',license_plate='QA-CARGO-'+uuid.uuid4().hex[:6],make='Toyota',model='Cargo van',
            cargo_capacity=40,cargo_uom='units',cargo_load=10,fuel_type='Diesel'))
        vehicle=frappe.get_doc('Vehicle',saved['vehicle']);self.assertEqual(vehicle.pp_crew_seats,0)
        self.assertEqual(vehicle.pp_cargo_capacity,40)

    def test_available_crew_excludes_overlapping_sites_and_employment_dates(self):
        from plus_point import crew
        result=self.event();plan=frappe.get_doc('PP Event Plan',result['plan'])
        crew.assign(plan.project,plan.staffing[0].site,plan.contract_terms,plan.start_date,plan.end_date,100,150,[self.worker.name])
        rows={r['name']:r for r in crew.available(plan.company,str(plan.start_date),str(plan.end_date))['rows']}
        self.assertFalse(rows[self.worker.name]['available']);self.assertIn('overlapping',rows[self.worker.name]['reason'])
        later=crew.available(plan.company,str(add_days(plan.end_date,1)),str(add_days(plan.end_date,2)))
        self.assertTrue(next(r for r in later['rows'] if r['name']==self.worker.name)['available'])
        with self.assertRaises(frappe.ValidationError):crew.validate_selected([self.worker.name],plan.company,plan.start_date,plan.end_date)
        frappe.db.set_value('Employee',self.f.employee.name,'date_of_joining',add_days(plan.end_date,1))
        rows={r['name']:r for r in crew.available(plan.company,str(plan.start_date),str(plan.end_date))['rows']}
        self.assertFalse(rows[self.f.employee.name]['available'])

    def test_selected_pool_controls_event_assignments_and_never_fills_from_others(self):
        from plus_point import crew
        result=self.event(headcount=2);plan=frappe.get_doc('PP Event Plan',result['plan'])
        crew.save_selection(plan.name,[self.worker.name])
        self.assertTrue(events.preview_crew(plan.name)['shortages'])
        with self.assertRaises(frappe.ValidationError):events.allocate_crew(plan.name)
        self.assertFalse(frappe.db.exists('PP Assignment',{'pp_event_plan':plan.name}))
        crew.save_selection(plan.name,[self.worker.name,self.f.employee.name])
        self.assertEqual(events.allocate_crew(plan.name)['created'],2)
        self.assertEqual(set(frappe.get_all('PP Assignment',filters={'pp_event_plan':plan.name},pluck='employee')),{self.worker.name,self.f.employee.name})
        with self.assertRaises(frappe.ValidationError):crew.save_selection(plan.name,[self.worker.name])
        self.assertFalse(frappe.db.exists('PP Work Entry',{'project':plan.project}))

    def test_onboarding_saves_multiple_selected_workers_in_plan(self):
        self.inventory_step();state=event_setup.current();state['step']='workers';event_setup.persist(state)
        chosen=[self.worker.name,self.f.employee.name]
        state=event_setup.advance('workers',dict(employees=chosen));self.assertEqual(state['employees'],chosen)
        self.assertEqual(json.loads(frappe.db.get_value('PP Event Plan',state['plan'],'selected_crew')),chosen)

    def test_manual_bulk_assignment_is_atomic_and_rechecks_bookings(self):
        from plus_point import crew
        result=self.event(headcount=2);plan=frappe.get_doc('PP Event Plan',result['plan']);site=plan.staffing[0].site
        args=(plan.project,site,plan.contract_terms,plan.start_date,plan.end_date,100,150)
        result=crew.assign(*args,[self.worker.name,self.f.employee.name]);self.assertEqual(result['created'],2)
        with self.assertRaises(frappe.ValidationError):crew.assign(*args,[self.worker.name])
        self.assertEqual(frappe.db.count('PP Assignment',{'project':plan.project}),2)
        self.assertFalse(frappe.db.exists('PP Work Entry',{'project':plan.project}))

    def test_crew_selection_refuses_guest_other_company_duplicates_and_inactive(self):
        from plus_point import crew
        result=self.event();plan=frappe.get_doc('PP Event Plan',result['plan'])
        with self.assertRaises(frappe.ValidationError):crew.validate_selected([self.worker.name,self.worker.name],plan.company,plan.start_date,plan.end_date)
        other=fixture('Other crew QA '+uuid.uuid4().hex[:5])
        with self.assertRaises(frappe.ValidationError):crew.save_selection(plan.name,[other.employee.name])
        frappe.db.set_value('Employee',self.worker.name,'status','Inactive')
        with self.assertRaises(frappe.ValidationError):crew.save_selection(plan.name,[self.worker.name])
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):crew.available(plan.company,str(plan.start_date),str(plan.end_date))

    def test_crew_allocation_rechecks_selection_after_preview(self):
        from plus_point import crew
        first=self.event();plan=frappe.get_doc('PP Event Plan',first['plan'])
        crew.save_selection(plan.name,[self.worker.name]);self.assertFalse(events.preview_crew(plan.name)['shortages'])
        other=self.event();other_plan=frappe.get_doc('PP Event Plan',other['plan'])
        crew.assign(other_plan.project,other_plan.staffing[0].site,other_plan.contract_terms,other_plan.start_date,other_plan.end_date,100,150,[self.worker.name])
        with self.assertRaises(frappe.ValidationError):events.allocate_crew(plan.name)
        self.assertFalse(frappe.db.exists('PP Assignment',{'pp_event_plan':plan.name}))

    @patch('plus_point.resources.company')
    def test_item_first_warehouse_suggestions_include_date_availability_and_own_edit(self,business):
        from plus_point import resources
        business.return_value=self.f.company
        item,warehouse,_=self.equipment();result=self.event();args=self.booking(result,item=item.name,warehouse=warehouse,quantity=7)
        booking=insert('PP Equipment Booking',**args)
        choices=resources.booking_options(result['project'],'equipment',args['start_date'],args['end_date'],item.name)
        self.assertEqual(len(choices),1);self.assertEqual(Decimal(choices[0]['available']),5)
        edited=resources.booking_options(result['project'],'equipment',args['start_date'],args['end_date'],item.name,booking.name)
        self.assertEqual(Decimal(edited[0]['available']),12)
        later=resources.booking_options(result['project'],'equipment',add_days(args['end_date'],1),add_days(args['end_date'],2),item.name)
        self.assertEqual(Decimal(later[0]['available']),12)

    def test_cancelled_event_releases_bookings_without_stock_or_valuation_movement(self):
        item,warehouse,_=self.equipment();result=self.event();args=self.booking(result,item=item.name,warehouse=warehouse,quantity=7)
        equipment=insert('PP Equipment Booking',**args);vehicle=self.vehicle();transport=insert('PP Vehicle Booking',**self.booking(result,vehicle=vehicle.name,purpose='Crew',crew_count=1))
        before=frappe.db.get_value('Bin',{'item_code':item.name,'warehouse':warehouse},['actual_qty','valuation_rate','stock_value'])
        project=frappe.get_doc('Project',result['project']);project.status='Cancelled';project.save()
        self.assertEqual(frappe.db.get_value('PP Equipment Booking',equipment.name,'status'),'Cancelled')
        self.assertEqual(frappe.db.get_value('PP Vehicle Booking',transport.name,'status'),'Cancelled')
        self.assertEqual(Decimal(events.stock_available(item.name,warehouse,args['start_date'],args['end_date'])['available']),12)
        self.assertEqual(before,frappe.db.get_value('Bin',{'item_code':item.name,'warehouse':warehouse},['actual_qty','valuation_rate','stock_value']))
        with self.assertRaises(frappe.ValidationError):insert('PP Equipment Booking',**args)

    def test_date_edit_conflict_keeps_previous_equipment_booking(self):
        item,warehouse,_=self.equipment();result=self.event(start=add_days(today(),2),end=add_days(today(),7));args=self.booking(result,item=item.name,warehouse=warehouse,quantity=10)
        first=insert('PP Equipment Booking',**dict(args,end_date=add_days(today(),3)))
        insert('PP Equipment Booking',**dict(args,start_date=add_days(today(),4)))
        first.end_date=add_days(today(),4)
        with self.assertRaises(frappe.ValidationError):first.save()
        self.assertEqual(str(frappe.db.get_value('PP Equipment Booking',first.name,'end_date')),str(add_days(today(),3)))
