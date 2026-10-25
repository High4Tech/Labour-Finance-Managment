"""Actual native records; test transaction rolls back every imported fixture."""
import base64
import csv
import io
import json
import unittest
import uuid

import frappe
from frappe.utils import today

from plus_point import imports, setup_flow
from plus_point.api import project_summary
from plus_point.tests.test_operations import fixture, insert


class SetupImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user('Administrator')
        cls.original_override=frappe.flags.get('pp_test_entitlement')
        frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
        frappe.db.savepoint('pp_import_suite')
        cls.f = fixture('PP Import QA ' + uuid.uuid4().hex[:8])

    @classmethod
    def tearDownClass(cls):
        frappe.set_user('Administrator')
        frappe.db.rollback(save_point='pp_import_suite')
        frappe.flags.pp_test_entitlement=cls.original_override

    def setUp(self):
        frappe.set_user('Administrator')
        frappe.db.savepoint('pp_import_test')
        self.tokens = []

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback(save_point='pp_import_test')
        for token in self.tokens:
            frappe.cache.delete_value('pp-import:' + token)
        frappe.cache.delete_value('defaults:Administrator')

    def preview(self, kind, rows, company=None):
        stream = io.StringIO(newline='')
        from plus_point.event_imports import PREVIOUS_SCHEMAS
        # Legacy payload tests keep their original columns; current template tests use the new schema.
        legacy=kind in PREVIOUS_SCHEMAS and any(set(row)-set(imports.SCHEMAS[kind]) for row in rows)
        writer = csv.DictWriter(stream, fieldnames=PREVIOUS_SCHEMAS[kind] if legacy else imports.SCHEMAS[kind])
        writer.writeheader()
        writer.writerows(rows)
        result = imports.preview(kind,company or self.f.company.name,'records.csv',
            base64.b64encode(stream.getvalue().encode()).decode())
        if result['token']:
            self.tokens.append(result['token'])
        return result

    def apply(self, kind, rows):
        preview = self.preview(kind, rows)
        self.assertTrue(preview['valid'], preview)
        return imports.apply(preview['token'])

    def employee(self, **overrides):
        return dict.fromkeys(imports.EMPLOYEE_OPTIONAL_COLUMNS,'') | dict(external_id='worker-001',employee='',first_name='Imported worker',last_name='',
            gender='Male',date_of_birth='1990-01-01',date_of_joining='2020-01-01',cell_number='+923001234567',status='Active',**overrides)

    def work(self):
        return dict(external_id='work-001',assignment=self.f.assignment.name,work_date=today(),units='1')

    def invoice(self):
        return dict(external_id='invoice-001',date=today(),project=self.f.project.name,customer=self.f.customer.name,
            item_code=self.f.item.name,amount='3000',source_type='PP Work Entry',source_name='import:work-001',description='Historical client charge')

    def event_row(self, **changes):
        from frappe.utils import add_days
        return dict(external_id='event-001',event_name='Imported event '+uuid.uuid4().hex[:8],customer='New Event Client '+uuid.uuid4().hex[:8],
            start_date=add_days(today(),2),end_date=add_days(today(),3),site_name='Exhibition Hall',workers_per_day='2',
            billing_model='Daily',fixed_amount='0',wage_rate='100',client_rate='150',agreement='Event staffing agreement')|changes

    def test_fifteen_legacy_events_create_missing_clients_without_preview_writes(self):
        from plus_point.event_imports import LEGACY_SCHEMAS
        rows=[self.event_row(external_id=f'EVT-{i}',customer=f'New Import Client {uuid.uuid4().hex[:8]}') for i in range(15)]
        stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=LEGACY_SCHEMAS['events']);writer.writeheader();writer.writerows(rows)
        count=frappe.db.count('Customer')
        preview=imports.preview('events',self.f.company.name,'old-events.csv',base64.b64encode(stream.getvalue().encode()).decode())
        self.tokens.append(preview['token']);self.assertTrue(preview['valid'],preview)
        self.assertEqual(frappe.db.count('Customer'),count)
        self.assertTrue(all('Create client:' in r['notes'][0] for r in preview['rows']))
        saved=imports.apply(preview['token']);self.assertEqual(saved['created'],15)
        self.assertEqual(frappe.db.count('Customer'),count+15)
        for result,row in zip(saved['rows'],rows):
            plan=frappe.get_doc('PP Event Plan',result['document'])
            customer=frappe.db.get_value('Project',plan.project,'customer')
            self.assertEqual(frappe.db.get_value('Customer',customer,'customer_name'),row['customer'])
            self.assertFalse(frappe.db.exists('PP Assignment',{'project':plan.project}))
            self.assertFalse(frappe.db.exists('PP Work Entry',{'project':plan.project}))
        self.assertEqual(self.apply('events',rows)['skipped'],15)

    def agreement_row(self,**changes):
        from frappe.utils import add_days
        return dict(external_id='agreement-new',agreement_title='Imported agreement '+uuid.uuid4().hex[:8],customer='New agreement client '+uuid.uuid4().hex[:8],
            start_date=add_days(today(),2),end_date=add_days(today(),3),status='Active',billing_model='Fixed',agreement_currency='PKR',fixed_amount='5000',
            scope='Stage crew and transport',conditions='Arrive on time|Wear safety equipment',site_name='Main stage',designation='Event crew',workers_per_day='1',client_rate='',
            customer_type='Company',client_contact_name='Ayesha Malik',client_email='qa@example.invalid',client_phone='+923001234567',client_country='Pakistan',client_city='Karachi',client_address_line1='12 QA Road',
            phase='Setup',vehicle_type='Crew van',vehicle_quantity='2')|changes

    def test_agreement_template_creates_new_client_profile_category_and_transport_after_review(self):
        from plus_point import operations
        old_company=operations.company
        operations.company=lambda:self.f.company
        try:
            category='Audit crew '+uuid.uuid4().hex[:8]
            row=self.agreement_row(designation=category)
            before=frappe.db.count('Customer');preview=self.preview('agreements',[row])
            self.assertTrue(preview['valid'],preview);self.assertEqual(preview['rows'][0]['action'],'Create')
            self.assertEqual(frappe.db.count('Customer'),before);self.assertFalse(frappe.db.exists('Designation',category))
            self.assertTrue(any('Create client:' in note for note in preview['rows'][0]['notes']))
            saved=imports.apply(preview['token']);doc=frappe.get_doc('PP Contract Terms',saved['rows'][0]['document'])
            client=frappe.get_doc('Customer',frappe.db.get_value('Project',doc.project,'customer'))
            self.assertEqual(client.customer_name,row['customer']);self.assertTrue(client.customer_primary_contact);self.assertTrue(client.customer_primary_address)
            self.assertEqual(doc.staffing[0].designation,category);self.assertEqual(doc.staffing[0].phase,'Setup')
            self.assertEqual(json.loads(doc.pp_transport_requirements)[0]['quantity'],2)
            self.assertEqual(json.loads(doc.pp_conditions),['Arrive on time','Wear safety equipment'])
            self.assertEqual(self.apply('agreements',[row])['skipped'],1)
        finally:operations.company=old_company

    def test_site_name_in_target_column_creates_new_site_and_preserves_legacy_address(self):
        row=dict(external_id='site-name-new',site='New named venue',site_name='New named venue',project=self.f.project.name,address='Legacy address',status='Active',country='Pakistan',city='Karachi',address_line1='12 QA Road')
        result=self.apply('event_sites',[row]);doc=frappe.get_doc('PP Site',result['rows'][0]['document'])
        self.assertEqual(doc.site_name,row['site_name']);self.assertEqual(doc.city,'Karachi');self.assertEqual(doc.address_line1,'12 QA Road')
        self.assertEqual(self.apply('event_sites',[row])['skipped'],1)
        self.assertEqual(self.apply('event_sites',[dict(row,city='Lahore')])['updated'],1)

    def test_blank_stock_count_is_not_treated_as_zero(self):
        code='COUNT-'+uuid.uuid4().hex[:8];warehouse='Count QA '+uuid.uuid4().hex[:8]
        self.apply('inventory_items',[dict(external_id='count-item',item_code=code,item_name=code,stock_uom='Nos',status='Active')])
        self.apply('warehouses',[dict(external_id='count-warehouse',warehouse_name=warehouse)])
        row=dict(external_id='count-empty',item_code=code,warehouse=warehouse,quantity='')
        preview=self.preview('stock_balances',[row]);self.assertFalse(preview['valid']);self.assertIn('quantity',preview['rows'][0]['error']);self.assertIsNone(preview['token'])

    def test_worker_organization_references_are_reviewed_then_created_and_old_templates_preserve_them(self):
        suffix=uuid.uuid4().hex[:8];row=self.employee()
        row.update(department='Import crew '+suffix,employment_type='Import contract '+suffix,branch='Import branch '+suffix,pp_loan_allowed='Yes',pp_loan_wait_months='3')
        count=frappe.db.count('Department');preview=self.preview('employees',[row]);self.assertTrue(preview['valid'],preview)
        self.assertEqual(frappe.db.count('Department'),count);self.assertTrue(any('Create department:' in note for note in preview['rows'][0]['notes']))
        result=imports.apply(preview['token']);doc=frappe.get_doc('Employee',result['rows'][0]['document'])
        self.assertEqual(frappe.db.get_value('Department',doc.department,'company'),self.f.company.name)
        self.assertEqual(doc.employment_type,row['employment_type']);self.assertEqual(doc.branch,row['branch']);self.assertEqual(doc.pp_loan_allowed,1)
        self.assertEqual(self.apply('employees',[row])['skipped'],1)
        stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=imports.EMPLOYEE_PRE_ORG_COLUMNS)
        writer.writeheader();writer.writerow({key:row.get(key,'') for key in imports.EMPLOYEE_PRE_ORG_COLUMNS})
        legacy=imports.preview('employees',self.f.company.name,'old-workers.csv',base64.b64encode(stream.getvalue().encode()).decode());self.tokens.append(legacy['token'])
        self.assertTrue(legacy['valid'],legacy);imports.apply(legacy['token']);doc.reload();self.assertTrue(doc.department);self.assertEqual(doc.branch,row['branch'])

    def test_worker_fractional_loan_months_and_unsupported_boolean_are_blocked_in_review(self):
        for changes,key in [({'pp_loan_wait_months':'1.5'},'whole months'),({'pp_loan_allowed':'sometimes'},'pp_loan_allowed')]:
            row=self.employee();row.update(changes);preview=self.preview('employees',[row]);self.assertFalse(preview['valid']);self.assertIn(key,preview['rows'][0]['error'])

    def test_agreement_reference_typo_and_invalid_vehicle_details_do_not_create_dependencies(self):
        row=self.agreement_row(customer='import:missing-client')
        preview=self.preview('agreements',[row]);self.assertFalse(preview['valid']);self.assertIn('Import the clients template first',preview['rows'][0]['error'])
        count=frappe.db.count('Customer');preview=self.preview('agreements',[self.agreement_row(vehicle_quantity='')])
        self.assertFalse(preview['valid']);self.assertIn('vehicle_quantity',preview['rows'][0]['error']);self.assertEqual(frappe.db.count('Customer'),count)

    def test_missing_installed_fields_block_review_before_a_ready_preview(self):
        from unittest.mock import patch
        original=frappe.db.has_column;before=frappe.db.count('Customer')
        with patch.object(frappe.db,'has_column',side_effect=lambda dt,key:False if (dt,key)==('PP Contract Terms','pp_conditions') else original(dt,key)):
            with self.assertRaisesRegex(frappe.ValidationError,'app update is incomplete'):
                self.preview('agreements',[self.agreement_row()])
        self.assertEqual(frappe.db.count('Customer'),before)

    def test_schema_change_after_review_blocks_apply_without_writes(self):
        from unittest.mock import patch
        original=frappe.db.has_column;row=self.agreement_row();preview=self.preview('agreements',[row]);self.assertTrue(preview['valid'],preview)
        before=frappe.db.count('Customer')
        with patch.object(frappe.db,'has_column',side_effect=lambda dt,key:False if (dt,key)==('PP Contract Terms','pp_conditions') else original(dt,key)):
            with self.assertRaisesRegex(frappe.ValidationError,'app update is incomplete'):imports.apply(preview['token'])
        self.assertEqual(frappe.db.count('Customer'),before)
        self.assertFalse(frappe.db.exists('PP Import Record',imports.record_key(self.f.company.name,'agreements',row['external_id'])))

    def test_shared_new_event_client_full_profile_and_conflicting_rows(self):
        row=self.event_row(client_contact_name='Ayesha Malik',client_email='client@example.invalid',client_phone='+966501234567',
            client_country='Saudi Arabia',client_city='Riyadh',client_address_line1='12 Exhibition Road',client_default_currency='USD')
        second=dict(row,external_id='event-002',event_name='Second '+row['event_name'])
        conflict=dict(second,client_email='different@example.invalid')
        self.assertFalse(self.preview('events',[row,conflict])['valid'])
        count=frappe.db.count('Customer');saved=self.apply('events',[row,second])
        self.assertEqual(frappe.db.count('Customer'),count+1)
        customer=frappe.get_doc('Customer',frappe.db.get_value('Project',frappe.db.get_value('PP Event Plan',saved['rows'][0]['document'],'project'),'customer'))
        self.assertTrue(customer.customer_primary_contact);self.assertTrue(customer.customer_primary_address)
        self.assertEqual(customer.default_currency,'USD')
        self.assertEqual(frappe.db.get_value('Address',customer.customer_primary_address,'city'),'Riyadh')

    def test_event_dependency_rolls_back_when_a_later_native_save_fails(self):
        from unittest.mock import patch
        from plus_point import event_imports
        rows=[self.event_row(),self.event_row(external_id='event-002')]
        preview=self.preview('events',rows);self.assertTrue(preview['valid'],preview)
        count=frappe.db.count('Customer');save=event_imports.save;calls=[]
        def failing(*args,**kwargs):
            calls.append(True)
            if len(calls)==2:frappe.throw('Simulated second-row validation failure')
            return save(*args,**kwargs)
        with patch.object(event_imports,'save',side_effect=failing):
            with self.assertRaises(frappe.ValidationError):imports.apply(preview['token'])
        self.assertEqual(frappe.db.count('Customer'),count)
        self.assertFalse(frappe.db.exists('PP Import Record',imports.record_key(self.f.company.name,'events',rows[0]['external_id'])))

    def test_clients_complete_profile_name_updates_and_legacy_preserves_contact(self):
        row=dict(external_id='client-001',customer='',customer_name='Imported Company '+uuid.uuid4().hex[:8],customer_type='Company',
            contact_name='Sana Malik',email='sana@example.invalid',phone='+923001234567',country='Pakistan',city='Lahore',address_line1='10 Hall Road')
        saved=self.apply('clients',[row]);name=saved['rows'][0]['document'];contact=frappe.db.get_value('Customer',name,'customer_primary_contact')
        second=dict(row,external_id='client-002',customer=row['customer_name'],phone='+923009999999')
        self.assertEqual(self.apply('clients',[second])['updated'],1)
        from plus_point.event_imports import LEGACY_SCHEMAS
        stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=LEGACY_SCHEMAS['clients']);writer.writeheader()
        writer.writerow(dict(external_id='client-003',customer=name,customer_name=row['customer_name'],customer_type='Company'))
        preview=imports.preview('clients',self.f.company.name,'legacy.csv',base64.b64encode(stream.getvalue().encode()).decode())
        self.tokens.append(preview['token']);self.assertTrue(preview['valid'],preview);imports.apply(preview['token'])
        self.assertEqual(frappe.db.get_value('Customer',name,'customer_primary_contact'),contact)

    def test_every_catalog_type_and_stock_names_replay(self):
        company=self.f.company.name
        warehouse='Import warehouse '+uuid.uuid4().hex[:8]
        rows={
            'warehouses':dict(external_id='warehouse-001',warehouse_name=warehouse),
            'inventory_items':dict(external_id='item-001',item_code='IMPORT-'+uuid.uuid4().hex[:8],item_name='Imported event chairs',stock_uom='Nos',status='Active'),
            'vehicles':dict(external_id='vehicle-001',license_plate='IMPORT-'+uuid.uuid4().hex[:8],make='Toyota',model='Crew van',crew_seats='10',cargo_capacity='0',cargo_uom='units',fuel_type='Diesel',status='Active'),
            'event_sites':dict(external_id='site-001',site='',site_name='Imported venue',project=self.f.project.project_name,address='10 Hall Road',status='Active'),
        }
        docs={}
        for kind,row in rows.items():
            docs[kind]=self.apply(kind,[row])['rows'][0]['document']
            self.assertEqual(self.apply(kind,[row])['skipped'],1,kind)
        self.assertEqual(self.apply('warehouses',[dict(rows['warehouses'],external_id='warehouse-002')])['updated'],1)
        stock=dict(external_id='stock-001',date=today(),item_code=rows['inventory_items']['item_name'],warehouse=warehouse,quantity='10',valuation_rate='100')
        saved=self.apply('stock_balances',[stock]);self.assertEqual(frappe.db.get_value('Stock Reconciliation',saved['rows'][0]['document'],'docstatus'),1)
        self.assertEqual(self.apply('stock_balances',[stock])['skipped'],1)
        self.assertEqual(frappe.db.get_value('Bin',{'item_code':docs['inventory_items'],'warehouse':docs['warehouses']},'actual_qty'),10)

    def test_financial_templates_accept_names_and_import_ids_without_inventing_sources(self):
        project='Event project label '+uuid.uuid4().hex[:8];customer='Client display label '+uuid.uuid4().hex[:8];service='Event service label '+uuid.uuid4().hex[:8]
        frappe.db.set_value('Project',self.f.project.name,'project_name',project)
        frappe.db.set_value('Customer',self.f.customer.name,'customer_name',customer)
        frappe.db.set_value('Item',self.f.item.name,'item_name',service)
        self.apply('work',[self.work()])
        invoice=self.invoice()|dict(project=project,customer=customer,item_code=service)
        self.apply('invoices',[invoice])
        bank=frappe.db.get_value('Account',self.f.company.default_cash_account,'account_name')
        self.apply('receipts',[dict(external_id='receipt-001',date=today(),invoice='import:invoice-001',amount='500',bank_account=bank)])
        self.apply('worker_payments',[dict(external_id='payment-001',date=today(),project=project,employee=self.f.employee.employee_name,amount='500',bank_account=bank)])
        supplier=insert('Supplier',supplier_name='Import supplier '+uuid.uuid4().hex[:8],supplier_group='All Supplier Groups',supplier_type='Company')
        label='Supplier display label '+uuid.uuid4().hex[:8];frappe.db.set_value('Supplier',supplier.name,'supplier_name',label)
        self.apply('expenses',[dict(external_id='expense-001',date=today(),project=project,supplier=label,item_code=service,amount='200',description='Historical cost')])
        bad=self.preview('worker_payments',[dict(external_id='missing-worker',date=today(),project=project,employee='Missing Worker',amount='100',bank_account=bank)])
        self.assertFalse(bad['valid']);self.assertIn('Import employees first',bad['rows'][0]['error'])
        self.assertFalse(frappe.db.exists('Employee',{'employee_name':'Missing Worker'}))

    def test_ambiguous_labels_and_foreign_company_ids_are_refused(self):
        from plus_point.import_links import find
        employee=insert('Employee',first_name=self.f.employee.first_name,gender='Male',date_of_birth='1991-01-01',date_of_joining='2020-01-01',status='Active',company=self.f.company.name)
        with self.assertRaises(frappe.ValidationError):find('Employee',employee.employee_name,self.f.company.name,'employee')
        other=fixture('Other import company '+uuid.uuid4().hex[:6])
        for doctype,value in [('Employee',other.employee.name),('Project',other.project.name),('Account',other.company.default_cash_account),('PP Site',other.site.name)]:
            with self.assertRaises(frappe.ValidationError,msg=doctype):find(doctype,value,self.f.company.name)

    def test_event_project_import_reference_and_missing_reference_instructions(self):
        event=self.apply('events',[self.event_row(customer=self.f.customer.customer_name)])
        site=dict(external_id='site-001',site='',site_name='Another venue',project='import:event-001',address='Hall Road',status='Active')
        saved=self.apply('event_sites',[site]);project=frappe.db.get_value('PP Event Plan',event['rows'][0]['document'],'project')
        self.assertEqual(frappe.db.get_value('PP Site',saved['rows'][0]['document'],'project'),project)
        site['external_id']='site-002';site['project']='import:missing-event'
        bad=self.preview('event_sites',[site]);self.assertFalse(bad['valid']);self.assertIn('Import the events template first',bad['rows'][0]['error'])

    def test_event_invalid_details_are_caught_before_creating_a_client(self):
        for changes in [dict(workers_per_day='501'),dict(start_date='10/22/2026'),
                dict(client_phone='+966501234567')]:
            row=self.event_row(**changes);preview=self.preview('events',[row])
            self.assertFalse(preview['valid'],preview)
            self.assertFalse(frappe.db.exists('Customer',{'customer_name':row['customer']}))

    def test_spreadsheet_event_labels_and_unused_fixed_rates_save_correctly(self):
        rows=[self.event_row(external_id=f'event-label-{i}',customer_type=client_type,billing_model=model,
            fixed_amount='5000' if model.strip().casefold() in ('fixed','fixed-price') else '',client_rate='150')
            for i,(client_type,model) in enumerate([('company','fixed'),('company','per_worker'),
                ('individual','fixed'),(' Business ','PER-WORKER'),('PERSON','fixed-price')])]
        preview=self.preview('events',rows);self.assertTrue(preview['valid'],preview)
        self.assertTrue(any('client_rate is unused' in note for note in preview['rows'][0]['notes']))
        saved=imports.apply(preview['token'])
        for index,result in enumerate(saved['rows']):
            plan=frappe.get_doc('PP Event Plan',result['document']);terms=frappe.get_doc('PP Contract Terms',plan.contract_terms)
            self.assertEqual(terms.billing_model,'Daily' if index in (1,3) else 'Fixed')
            self.assertEqual(float(plan.client_rate),150 if index in (1,3) else 0)
            self.assertEqual(float(plan.wage_rate),100)
            if terms.billing_model=='Fixed':self.assertEqual(float(terms.fixed_amount),5000)
            client=frappe.db.get_value('Project',plan.project,'customer')
            self.assertEqual(frappe.db.get_value('Customer',client,'customer_type'),'Individual' if index in (2,4) else 'Company')
        self.assertEqual(self.apply('events',rows)['skipped'],5)

    def test_client_types_are_normalized_and_invalid_labels_show_the_value(self):
        row=dict(external_id='client-label',customer='',customer_name='Label client '+uuid.uuid4().hex[:8],customer_type='individual')
        result=self.apply('clients',[row]);name=result['rows'][0]['document']
        self.assertEqual(frappe.db.get_value('Customer',name,'customer_type'),'Individual')
        row.update(customer=name,customer_type='')
        self.apply('clients',[row]);self.assertEqual(frappe.db.get_value('Customer',name,'customer_type'),'Individual')
        bad=self.preview('events',[self.event_row(customer_type='wedding')]);self.assertFalse(bad['valid'])
        self.assertIn('wedding',bad['rows'][0]['error']);self.assertIn('Company or Individual',bad['rows'][0]['error'])
        bad=self.preview('events',[self.event_row(billing_model='per guest')]);self.assertFalse(bad['valid'])
        self.assertIn('per guest',bad['rows'][0]['error'])

    def test_other_template_choice_labels_ignore_capitalization(self):
        worker=self.employee();worker.update(gender='male',status='active')
        result=self.apply('employees',[worker]);name=result['rows'][0]['document']
        self.assertEqual(frappe.db.get_value('Employee',name,'gender'),'Male')
        self.assertEqual(frappe.db.get_value('Employee',name,'status'),'Active')
        row=dict(external_id='vehicle-label',license_plate='LABEL-'+uuid.uuid4().hex[:8],make='Toyota',model='Cargo van',
            crew_seats='0',cargo_capacity='10',cargo_uom='M3',fuel_type='diesel',status='ACTIVE')
        result=self.apply('vehicles',[row]);doc=frappe.get_doc('Vehicle',result['rows'][0]['document'])
        self.assertEqual(doc.fuel_type,'Diesel');self.assertEqual(doc.pp_cargo_uom,'m³')

    def test_reference_download_includes_approved_sources_and_account_names(self):
        self.apply('work',[self.work()])
        original=dict(frappe.response)
        try:
            imports.references(self.f.company.name)
            content=frappe.response['filecontent'].decode('utf-8-sig')
            self.assertIn('PP Work Entry',content);self.assertIn(self.f.assignment.name,content)
            self.assertIn(self.f.company.default_cash_account,content)
        finally:
            frappe.response.clear();frappe.response.update(original)

    def test_changed_name_match_requires_a_fresh_review(self):
        row=self.event_row(customer=self.f.customer.name)
        # A planned new dependency appeared after preview. Do not silently
        # replace the approved creation with a different existing profile.
        row['customer']='New client after preview '+uuid.uuid4().hex[:8]
        preview=self.preview('events',[row]);self.assertTrue(preview['valid'],preview)
        insert('Customer',customer_name=row['customer'],customer_type='Company',customer_group='Commercial',territory='All Territories')
        with self.assertRaises(frappe.ValidationError):imports.apply(preview['token'])
        self.assertFalse(frappe.db.exists('PP Import Record',imports.record_key(self.f.company.name,'events',row['external_id'])))

    def test_deleted_imported_event_keeps_receipt_and_cannot_be_silently_replayed(self):
        from plus_point import record_actions
        row=self.event_row(customer=self.f.customer.name)
        created=self.apply('events',[row])['rows'][0]['document']
        receipt=imports.record_key(self.f.company.name,'events',row['external_id'])
        self.assertFalse(record_actions.review('PP Event Plan',created)['blocked'])
        record_actions.remove('PP Event Plan',created)
        self.assertTrue(frappe.db.exists('PP Import Record',receipt))
        self.assertFalse(frappe.db.exists('PP Event Plan',created))
        preview=self.preview('events',[row]);self.assertFalse(preview['valid'])
        self.assertIn('deleted',preview['rows'][0]['error'])
        self.assertFalse(frappe.db.exists('PP Event Plan',created))

    def test_employee_preview_create_update_and_replay(self):
        row = self.employee()
        count = frappe.db.count('Employee')
        preview = self.preview('employees',[row])
        self.assertEqual(frappe.db.count('Employee'),count)
        created = imports.apply(preview['token'])
        name = created['rows'][0]['document']
        self.assertEqual(created['created'],1)
        self.assertFalse(frappe.db.get_value('Employee',name,'user_id'))
        self.assertEqual(self.apply('employees',[row])['skipped'],1)
        row['first_name'] = 'Updated worker'
        result = self.apply('employees',[row])
        self.assertEqual(result['updated'],1)
        self.assertEqual(result['rows'][0]['document'],name)
        self.assertEqual(frappe.db.get_value('Employee',name,'first_name'),'Updated worker')
        self.assertEqual(frappe.db.count('Employee'),count+1)

    def test_existing_employee_update_requires_explicit_same_company_id(self):
        row=self.employee()
        row['employee']=self.f.employee.name
        self.assertEqual(self.apply('employees',[row])['updated'],1)
        other=fixture('PP Import other '+uuid.uuid4().hex[:6])
        row['employee']=other.employee.name
        self.assertFalse(self.preview('employees',[row])['valid'])

    def test_new_worker_names_in_employee_column_create_profiles_and_replay(self):
        rows=[]
        for number in range(15):
            row=self.employee();row.update(external_id=f'EMP{number+1:03}',employee=f'Imported Person {chr(65+number)}',
                first_name='Imported',last_name=f'Person {chr(65+number)}',personal_email=f'worker{number}@example.invalid',
                current_address='12 Exhibition Road, Riyadh',person_to_be_contacted='Ayesha Malik',emergency_phone_number='+966501234567')
            rows.append(row)
        preview=self.preview('employees',rows)
        self.assertTrue(preview['valid'],preview);self.assertTrue(all(r['action']=='Create' for r in preview['rows']))
        saved=imports.apply(preview['token']);self.assertEqual(saved['created'],15)
        doc=frappe.get_doc('Employee',saved['rows'][0]['document'])
        self.assertEqual(doc.personal_email,'worker0@example.invalid');self.assertIn('Riyadh',doc.current_address)
        self.assertEqual(doc.person_to_be_contacted,'Ayesha Malik');self.assertFalse(doc.user_id)
        self.assertEqual(self.apply('employees',rows)['skipped'],15)
        rows[0]['cell_number']='+966555555555'
        updated=self.apply('employees',rows);self.assertEqual(updated['updated'],1)
        self.assertEqual(updated['rows'][0]['document'],doc.name)

    def test_unique_existing_worker_name_matches_birthdate_and_refuses_ambiguity(self):
        row=self.employee();row.update(employee=self.f.employee.employee_name,date_of_birth=str(self.f.employee.date_of_birth))
        result=self.apply('employees',[row]);self.assertEqual(result['updated'],1)
        self.assertEqual(result['rows'][0]['document'],self.f.employee.name)
        row['external_id']='other';row['employee']='Imported worker';row['date_of_birth']='1989-01-01'
        self.assertFalse(self.preview('employees',[row])['valid'])

    def test_legacy_employee_template_preserves_new_profile_columns(self):
        row=self.employee();row['personal_email']='existing@example.invalid'
        saved=self.apply('employees',[row]);name=saved['rows'][0]['document']
        legacy={key:row[key] for key in imports.LEGACY_EMPLOYEE_COLUMNS};legacy['cell_number']='+966501111111'
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=imports.LEGACY_EMPLOYEE_COLUMNS)
        writer.writeheader();writer.writerow(legacy)
        preview=imports.preview('employees',self.f.company.name,'old.csv',base64.b64encode(stream.getvalue().encode()).decode())
        self.tokens.append(preview['token']);self.assertTrue(preview['valid'],preview)
        imports.apply(preview['token']);self.assertEqual(frappe.db.get_value('Employee',name,'personal_email'),'existing@example.invalid')

    def test_import_category_is_reviewed_created_and_legacy_preserves_it(self):
        role='Imported event role '+uuid.uuid4().hex[:7];row=self.employee(designation=role)
        preview=self.preview('employees',[row]);self.assertTrue(preview['valid'],preview)
        self.assertFalse(frappe.db.exists('Designation',role));self.assertIn('Create worker category '+role,preview['rows'][0]['notes'])
        result=imports.apply(preview['token']);worker=result['rows'][0]['document']
        self.assertEqual(frappe.db.get_value('Employee',worker,'designation'),role)
        self.assertTrue(frappe.db.exists('Designation',role))
        old={key:row[key] for key in imports.EMPLOYEE_PROFILE_COLUMNS};old['cell_number']='+923001111111'
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=imports.EMPLOYEE_PROFILE_COLUMNS);writer.writeheader();writer.writerow(old)
        preview=imports.preview('employees',self.f.company.name,'previous-profile.csv',base64.b64encode(stream.getvalue().encode()).decode());self.tokens.append(preview['token'])
        self.assertTrue(preview['valid'],preview);imports.apply(preview['token'])
        self.assertEqual(frappe.db.get_value('Employee',worker,'designation'),role)
        self.assertNotIn('image',imports.SCHEMAS['employees'])

    def test_duplicate_new_person_with_different_external_ids_is_refused(self):
        row=self.employee();duplicate=dict(row,external_id='different')
        self.assertFalse(self.preview('employees',[row,duplicate])['valid'])

    def test_preview_lists_duplicate_missing_and_invalid_data_rows(self):
        row=self.employee()
        duplicate=dict(row)
        bad=dict(row,external_id='worker-002',date_of_birth='not a date')
        result=self.preview('employees',[row,duplicate,bad])
        self.assertFalse(result['valid'])
        self.assertEqual([r['row'] for r in result['rows'] if r.get('error')],[3,4])
        self.assertIsNone(result['token'])

    def test_xlsx_values_and_formula_rejection(self):
        from frappe.utils.xlsxutils import make_xlsx
        row=self.employee()
        data=[imports.SCHEMAS['employees'],[row.get(k,'') for k in imports.SCHEMAS['employees']]]
        content=base64.b64encode(make_xlsx(data,'Employees').getvalue()).decode()
        result=imports.preview('employees',self.f.company.name,'employees.xlsx',content)
        self.assertTrue(result['valid'],result)
        self.tokens.append(result['token'])
        # Native export escapes formulas. Put an actual formula into this
        # disposable test workbook to exercise the import rejection instead.
        from openpyxl import load_workbook
        book=load_workbook(io.BytesIO(base64.b64decode(content)))
        book.active['C2']='=1+1'
        stream=io.BytesIO()
        book.save(stream)
        book.close()
        content=base64.b64encode(stream.getvalue()).decode()
        with self.assertRaises(frappe.ValidationError):
            imports.preview('employees',self.f.company.name,'employees.xlsx',content)

    def test_approved_work_and_worker_payment_update_real_summaries(self):
        self.apply('work',[self.work()])
        company=frappe.get_doc('Company',self.f.company.name)
        row=dict(external_id='pay-001',date=today(),project=self.f.project.name,employee=self.f.employee.name,
            amount='1000',bank_account=company.default_cash_account)
        result=self.apply('worker_payments',[row])
        settlement=frappe.get_doc('PP Wage Settlement',result['rows'][0]['document'])
        self.assertEqual(settlement.docstatus,1)
        self.assertEqual(frappe.db.get_value('Payment Entry',settlement.payment_entry,'docstatus'),1)
        self.assertTrue(frappe.db.exists('GL Entry',{'voucher_no':settlement.payment_entry,'is_cancelled':0}))
        summary=project_summary(self.f.project.name)
        self.assertEqual(summary['labour_cost'],'2000.00')
        self.assertEqual(summary['wages_paid'],'1000.00')
        self.assertEqual(self.apply('worker_payments',[row])['skipped'],1)

    def test_linked_invoice_receipt_and_duplicate_protection(self):
        self.apply('work',[self.work()])
        invoice=self.invoice()
        result=self.apply('invoices',[invoice])
        name=result['rows'][0]['document']
        self.assertEqual(frappe.db.get_value('Sales Invoice',name,'docstatus'),1)
        self.assertEqual(self.apply('invoices',[invoice])['skipped'],1)
        company=frappe.get_doc('Company',self.f.company.name)
        receipt=dict(external_id='receipt-001',date=today(),invoice='import:invoice-001',amount='1250',bank_account=company.default_cash_account)
        self.apply('receipts',[receipt])
        summary=project_summary(self.f.project.name)
        self.assertEqual(summary['cash_collected_gross'],'1250.00')
        self.assertEqual(summary['client_outstanding_gross'],'1750.00')
        self.assertEqual(summary['earned_revenue'],'3000.00')
        self.assertEqual(self.apply('receipts',[receipt])['skipped'],1)
        invoice['amount']='3001'
        self.assertFalse(self.preview('invoices',[invoice])['valid'])

    def test_project_expense_posting_and_spending_limit(self):
        supplier=insert('Supplier',supplier_name='PP import supplier '+uuid.uuid4().hex[:6],supplier_group='All Supplier Groups',supplier_type='Company')
        row=dict(external_id='expense-001',date=today(),project=self.f.project.name,supplier=supplier.name,
            item_code=self.f.item.name,amount='500',description='Actual historical net expense')
        self.apply('expenses',[row])
        self.assertEqual(project_summary(self.f.project.name)['other_project_costs'],'500.00')
        project=frappe.get_doc('Project',self.f.project.name)
        project.update(dict(estimated_costing=600,pp_enforce_spending_budget=1))
        project.save()
        row['external_id']='expense-002'
        preview=self.preview('expenses',[row])
        self.assertFalse(preview['valid'])
        self.assertTrue(preview['budgets'][0]['blocked'])
        self.assertEqual(project_summary(self.f.project.name)['other_project_costs'],'500.00')

    def test_batch_failure_rolls_back_all_work_and_receipts(self):
        # Both rows pass individual preview, but together duplicate one worker-day.
        first=self.work()
        second=dict(first,external_id='work-002')
        preview=self.preview('work',[first,second])
        self.assertTrue(preview['valid'])
        with self.assertRaises(frappe.ValidationError):
            imports.apply(preview['token'])
        self.assertEqual(frappe.db.count('PP Work Entry',{'project':self.f.project.name}),0)
        self.assertFalse(frappe.db.exists('PP Import Record',imports.record_key(self.f.company.name,'work','work-001')))

    def test_stale_budget_and_suspended_subscription_stop_atomic_apply(self):
        preview=self.preview('work',[self.work()])
        project=frappe.get_doc('Project',self.f.project.name)
        project.update(dict(estimated_costing=1000,pp_enforce_spending_budget=1))
        project.save()
        with self.assertRaises(frappe.ValidationError):
            imports.apply(preview['token'])
        self.assertEqual(frappe.db.count('PP Work Entry',{'project':self.f.project.name}),0)
        preview=self.preview('employees',[self.employee()])
        original=frappe.flags.get('pp_test_entitlement')
        try:
            frappe.flags.pp_test_entitlement={'suspended':1,'valid_until':'2099-12-31'}
            with self.assertRaises(frappe.ValidationError):
                imports.apply(preview['token'])
            self.assertFalse(frappe.db.exists('PP Import Record',imports.record_key(self.f.company.name,'employees','worker-001')))
        finally:
            frappe.flags.pp_test_entitlement=original

    def test_fixed_milestone_import_and_contract_cap(self):
        contract=insert('Contract',party_type='Customer',party_name=self.f.customer.name,
            contract_terms='Actual fixed agreement',start_date=today())
        terms=insert('PP Contract Terms',contract=contract.name,project=self.f.project.name,
            billing_model='Fixed',fixed_amount=5000,currency='PKR',status='Active',effective_start=today())
        row=dict(external_id='milestone-001',contract_terms=terms.name,title='Completed historical work',date=today(),amount='3000')
        self.apply('milestones',[row])
        self.assertEqual(project_summary(self.f.project.name)['earned_revenue'],'3000.00')
        row['external_id']='milestone-002'
        with self.assertRaises(frappe.ValidationError):
            self.apply('milestones',[row])
        self.assertEqual(project_summary(self.f.project.name)['earned_revenue'],'3000.00')

    def test_import_token_ownership_guest_and_platform_denial(self):
        user=insert('User',email=f'pp-import-{uuid.uuid4().hex[:8]}@example.invalid',first_name='Import QA',send_welcome_email=0,
                    roles=[dict(role='System Manager')])
        preview=self.preview('employees',[self.employee()])
        self.assertIsNotNone(frappe.cache.get_value('pp-import:'+preview['token']))
        frappe.set_user(user.name)
        with self.assertRaises(frappe.ValidationError):
            imports.apply(preview['token'])
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            imports.preview('employees',self.f.company.name,'file.csv','')
        frappe.set_user('Administrator')
        original=frappe.conf.get('pp_control_plane')
        try:
            frappe.conf.pp_control_plane=1
            with self.assertRaises(frappe.PermissionError):
                setup_flow.status()
            with self.assertRaises(frappe.PermissionError):
                imports.apply(preview['token'])
        finally:
            frappe.conf.pp_control_plane=original

    def test_onboarding_resume_skip_and_real_assignment(self):
        old=setup_flow.state()
        try:
            setup_flow.save_state(dict(step='company',skipped=False))
            saved=setup_flow.advance('company',dict(company=self.f.company.name))
            self.assertEqual(saved['step'],'worker')
            setup_flow.control('skip')
            self.assertTrue(setup_flow.status()['state']['skipped'])
            self.assertFalse(setup_flow.status()['auto_start'])
            self.assertEqual(setup_flow.control('resume')['step'],'worker')
            worker=setup_flow.advance('worker',dict(first_name='Wizard worker',gender='Male',date_of_birth='1990-01-01',date_of_joining=today()))
            self.assertEqual(worker['step'],'site')
            site=setup_flow.advance('site',dict(site_name='Wizard site',project=self.f.project.name))
            self.assertEqual(site['step'],'terms')
            setup_flow.advance('terms',dict(contract_terms=self.f.terms.name))
            assigned=setup_flow.advance('assignment',dict(start_date=today(),wage_rate=2000,client_rate=3000))
            self.assertEqual(assigned['step'],'import')
            self.assertEqual(frappe.db.get_value('PP Assignment',assigned['assignment'],'employee'),worker['employee'])
            self.assertEqual(frappe.db.count('PP Work Entry',{'employee':worker['employee']}),0)
            self.assertEqual(setup_flow.advance('import',{})['step'],'done')
        finally:
            setup_flow.save_state(old)

    def test_onboarding_new_job_and_billing_terms(self):
        old=setup_flow.state()
        try:
            setup_flow.save_state(dict(step='site',company=self.f.company.name,employee=self.f.employee.name))
            saved=setup_flow.advance('site',dict(site_name='New job location',project_name='Wizard new job '+uuid.uuid4().hex[:6],customer=self.f.customer.name))
            self.assertEqual(frappe.db.get_value('Project',saved['project'],'customer'),self.f.customer.name)
            saved=setup_flow.advance('terms',dict(agreement='Actual daily labour agreement',billing_model='Daily',effective_start=today()))
            self.assertEqual(frappe.db.get_value('PP Contract Terms',saved['contract_terms'],'status'),'Active')
            with self.assertRaises(frappe.ValidationError):
                setup_flow.advance('worker',{})
        finally:
            setup_flow.save_state(old)
