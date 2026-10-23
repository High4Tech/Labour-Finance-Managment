"""Complete native lookups, input rules, saved defaults and guarded native deletion."""
import unittest,uuid
import frappe
from frappe.utils import today
from plus_point.tests.test_operations import fixture,insert
from plus_point import choices,form_defaults,record_actions,input_rules


class FormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user('Administrator');cls.old=frappe.flags.get('pp_test_entitlement');frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
        frappe.db.savepoint('pp_forms_suite');cls.f=fixture('Forms QA '+uuid.uuid4().hex[:7])
    @classmethod
    def tearDownClass(cls):
        frappe.set_user('Administrator');frappe.db.rollback(save_point='pp_forms_suite');frappe.flags.pp_test_entitlement=cls.old
    def setUp(self):frappe.set_user('Administrator');frappe.db.savepoint('pp_forms_case')
    def tearDown(self):frappe.set_user('Administrator');frappe.db.rollback(save_point='pp_forms_case');frappe.clear_cache()
    def test_all_country_pages_match_native_permissions_and_include_last_country(self):
        found=[];start=0
        while True:
            data=choices.page('Country',start=start);found.extend(r['value'] for r in data['rows'])
            if not data['more']:break
            self.assertGreater(data['next_start'],start);start=data['next_start']
        self.assertGreater(len(found),200);self.assertEqual(len(found),len(set(found)))
        self.assertEqual(set(found),set(frappe.get_list('Country',pluck='name',limit_page_length=0)))
        self.assertIn('Zimbabwe',found)
    def test_search_and_company_filters_remain_native(self):
        result=choices.page('Employee',filters={'company':self.f.company.name,'status':'Active'})
        self.assertEqual([r['value'] for r in result['rows']],[self.f.employee.name])
        self.assertEqual([r['value'] for r in choices.page('Country',txt='Zimbabwe')['rows']],['Zimbabwe'])
    def test_all_installed_currencies_can_be_chosen_before_enabling(self):
        frappe.db.set_value('Currency','SAR','enabled',0)
        self.assertIn('SAR',[r['value'] for r in choices.page('Currency',txt='SAR')['rows']])
    def test_native_lookup_with_smaller_page_cap_still_reaches_the_end(self):
        from unittest.mock import patch
        from frappe.desk.search import search_widget
        def small_page(*args,**kwargs):
            kwargs['page_length']=7;return search_widget(*args,**kwargs)
        found=[];start=0
        with patch('frappe.desk.search.search_widget',side_effect=small_page):
            while True:
                result=choices.page('Country',start=start);found.extend(r['value'] for r in result['rows'])
                if not result['more']:break
                start=result['next_start']
        self.assertEqual(set(found),set(frappe.get_list('Country',pluck='name',limit_page_length=0)))
    def test_event_selector_includes_more_than_twenty_plans_alphabetically(self):
        from plus_point.events import create_event,plans_for
        for letter in reversed('ABCDEFGHIJKLMNOPQRSTU'):
            create_event(self.f.company.name,self.f.customer.name,'Event '+letter,today(),today(),'Event agreement','Daily',100,150,
                sites=[dict(site_name='Hall '+letter,phase='Event',start_date=today(),end_date=today(),workers_required=1)])
        result=plans_for(company=self.f.company.name)
        self.assertEqual(len(result),21);self.assertEqual([r.event_name for r in result],['Event '+c for c in 'ABCDEFGHIJKLMNOPQRSTU'])
    def test_invalid_offset_and_guest_lookup_rejected(self):
        with self.assertRaises(frappe.ValidationError):choices.page('Country',start=-1)
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):choices.page('Country')
    def test_international_person_names_and_phone_formats(self):
        for value in ('José O’Neill','Anne-Marie Smith','محمد أحسن','Zoë D. Malik'):
            input_rules.check('first_name',value)
        for value in ('+966 (50) 123-4567','0300-1234567'):input_rules.check('phone',value)
        for value in ('Ayesha9','Sam@email','<script>','$$$'):
            with self.assertRaises(frappe.ValidationError):input_rules.check('first_name',value)
        for value in ('call me','+966abc','++123456'):
            with self.assertRaises(frappe.ValidationError):input_rules.check('phone',value)
    def test_native_employee_save_rejects_invalid_changed_name(self):
        doc=frappe.get_doc('Employee',self.f.employee.name);doc.first_name='Farhan9'
        with self.assertRaises(frappe.ValidationError):doc.save()
        self.assertNotEqual(frappe.db.get_value('Employee',doc.name,'first_name'),'Farhan9')
    def test_numeric_and_registration_rules(self):
        for value in ('12abc','NaN','Infinity'):
            with self.assertRaises(frappe.ValidationError):input_rules.check('quantity',value,'Float')
        with self.assertRaises(frappe.ValidationError):input_rules.check('workers_required','1.5','Int')
        input_rules.check('quantity','1.5','Float');input_rules.check('latitude','-24.1','Float')
        input_rules.check('license_plate','ABC-123 / X')
        with self.assertRaises(frappe.ValidationError):input_rules.check('license_plate','ABC@123')
        from plus_point.event_imports import validate
        with self.assertRaises(frappe.ValidationError):
            validate('vehicles',self.f.company.name,dict(license_plate='ABC@123',make='Toyota',model='Hiace',crew_seats='12',cargo_capacity='0',cargo_uom='units',fuel_type='Diesel',status='Active'))
    def test_saved_context_selects_unique_site_and_agreement_without_guessing_rates(self):
        data=form_defaults.context(project=self.f.project.name)
        self.assertEqual(data['site'],self.f.site.name);self.assertEqual(data['contract_terms'],self.f.terms.name)
        self.assertNotIn('wage_rate',data)
        insert('PP Site',site_name='Another hall',project=self.f.project.name,is_active=1)
        self.assertNotIn('site',form_defaults.context(project=self.f.project.name))
    def test_existing_event_plan_supplies_saved_dates_and_rates(self):
        plan=insert('PP Event Plan',event_name='Saved event QA',project=self.f.project.name,contract_terms=self.f.terms.name,
            start_date=today(),end_date=today(),wage_rate=2000,client_rate=3000,
            staffing=[dict(site=self.f.site.name,phase='Event',start_date=today(),end_date=today(),workers_required=1)])
        data=form_defaults.context(project=self.f.project.name)
        self.assertEqual(data['wage_rate'],plan.wage_rate);self.assertEqual(str(data['start_date']),today())
    def test_context_rejects_unrelated_site_and_guest(self):
        other=insert('Project',project_name='Other forms QA '+uuid.uuid4().hex[:5],company=self.f.company.name,customer=self.f.customer.name)
        with self.assertRaises(frappe.ValidationError):form_defaults.context(project=other.name,site=self.f.site.name)
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):form_defaults.context(project=self.f.project.name)
    def test_draft_work_can_be_reviewed_and_deleted_without_earnings(self):
        work=insert('PP Work Entry',assignment=self.f.assignment.name,work_date=today(),units=1,status='Draft')
        self.assertFalse(record_actions.review('PP Work Entry',work.name)['blocked'])
        record_actions.remove('PP Work Entry',work.name)
        self.assertFalse(frappe.db.exists('PP Work Entry',work.name))
    def test_approved_work_cannot_be_deleted_via_either_path(self):
        work=insert('PP Work Entry',assignment=self.f.assignment.name,work_date=today(),units=1,status='Draft');work.status='Approved';work.save()
        self.assertTrue(record_actions.review('PP Work Entry',work.name)['blocked'])
        with self.assertRaises(frappe.ValidationError):record_actions.remove('PP Work Entry',work.name)
        with self.assertRaises(frappe.ValidationError):frappe.delete_doc('PP Work Entry',work.name)
        self.assertTrue(frappe.db.exists('PP Work Entry',work.name))
    def test_batch_link_failure_rolls_back_all_selected_deletions(self):
        free=insert('Customer',customer_name='Unused forms QA '+uuid.uuid4().hex[:5],customer_type='Company',customer_group='Commercial',territory='All Territories')
        with self.assertRaises(frappe.LinkExistsError):record_actions.remove_many('Customer',[free.name,self.f.customer.name])
        self.assertTrue(frappe.db.exists('Customer',free.name));self.assertTrue(frappe.db.exists('Customer',self.f.customer.name))
    def test_unlinked_customer_can_be_deleted(self):
        free=insert('Customer',customer_name='Unused customer QA '+uuid.uuid4().hex[:5],customer_type='Company',customer_group='Commercial',territory='All Territories')
        result=record_actions.remove_many('Customer',[free.name]);self.assertEqual(result['deleted'],[free.name])
    def test_delete_preview_identifies_linked_records_before_confirmation(self):
        free=insert('Customer',customer_name='Review unused QA '+uuid.uuid4().hex[:5],customer_type='Company',customer_group='Commercial',territory='All Territories')
        rows=record_actions.review_many('Customer',[free.name,self.f.customer.name])['records']
        self.assertFalse(next(r for r in rows if r['name']==free.name)['blocked'])
        self.assertIn('Used by',next(r for r in rows if r['name']==self.f.customer.name)['blocked'])
        dependency=next(r for r in rows if r['name']==self.f.customer.name)['dependency']
        self.assertIsNotNone(dependency);self.assertNotEqual((dependency['doctype'],dependency['name']),('Customer',self.f.customer.name))
        self.assertTrue(frappe.db.exists('Customer',free.name))

    def import_receipt(self,doc,kind):
        previous=frappe.flags.get('pp_import_record');frappe.flags.pp_import_record=True
        try:return insert('PP Import Record',company=self.f.company.name,kind=kind,external_id='delete-'+uuid.uuid4().hex[:12],document_type=doc.doctype,document_name=doc.name,content_hash='a'*64)
        finally:frappe.flags.pp_import_record=previous

    def test_imported_unused_event_can_be_deleted_without_deleting_its_receipt(self):
        plan=insert('PP Event Plan',event_name='Imported deletable event',project=self.f.project.name,contract_terms=self.f.terms.name,start_date=today(),end_date=today(),wage_rate=2000,client_rate=3000,staffing=[dict(site=self.f.site.name,phase='Event',start_date=today(),end_date=today(),workers_required=1)])
        receipt=self.import_receipt(plan,'events');before=frappe.get_doc('PP Import Record',receipt.name).as_dict()
        self.assertFalse(record_actions.review(plan.doctype,plan.name)['blocked'])
        record_actions.remove(plan.doctype,plan.name)
        self.assertFalse(frappe.db.exists(plan.doctype,plan.name))
        self.assertEqual(frappe.get_doc('PP Import Record',receipt.name).as_dict(),before)
        with self.assertRaises(frappe.PermissionError):frappe.delete_doc('PP Import Record',receipt.name)

    def test_native_imported_worker_deletion_and_real_dependencies_remain_guarded(self):
        worker=insert('Employee',first_name='Unused imported worker',gender='Male',date_of_birth='1990-01-01',date_of_joining='2020-01-01',company=self.f.company.name,status='Active')
        receipt=self.import_receipt(worker,'employees')
        self.assertFalse(record_actions.review('Employee',worker.name)['blocked'])
        frappe.delete_doc('Employee',worker.name)
        self.assertTrue(frappe.db.exists('PP Import Record',receipt.name))
        self.import_receipt(self.f.employee,'employees')
        self.assertTrue(record_actions.review('Employee',self.f.employee.name)['blocked'])
        with self.assertRaises(frappe.LinkExistsError):record_actions.remove('Employee',self.f.employee.name)

    def test_import_receipt_does_not_weaken_approved_work_protection(self):
        work=insert('PP Work Entry',assignment=self.f.assignment.name,work_date=today(),units=1,status='Draft');work.status='Approved';work.save()
        receipt=self.import_receipt(work,'work')
        with self.assertRaises(frappe.ValidationError):record_actions.remove('PP Work Entry',work.name)
        with self.assertRaises(frappe.ValidationError):frappe.delete_doc('PP Work Entry',work.name)
        self.assertTrue(frappe.db.exists('PP Import Record',receipt.name))
    def test_delete_requires_native_permission_and_valid_selection(self):
        with self.assertRaises(frappe.ValidationError):record_actions.remove_many('Customer',[])
        with self.assertRaises(frappe.ValidationError):record_actions.remove_many('Customer',[self.f.customer.name]*2)
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):record_actions.remove('Customer',self.f.customer.name)
    def test_client_profile_cleanup_is_atomic_when_project_blocks_delete(self):
        from plus_point.clients import create
        client=create(dict(customer_name='Client cleanup QA '+uuid.uuid4().hex[:5],contact_name='Ayesha Malik',email='ayesha@example.invalid',country='Pakistan',city='Karachi',address_line1='12 Venue Road'))
        self.assertFalse(record_actions.review('Customer',client.name)['blocked'])
        project=insert('Project',project_name='Client cleanup QA '+uuid.uuid4().hex[:5],company=self.f.company.name,customer=client.name)
        contact,address=client.customer_primary_contact,client.customer_primary_address
        self.assertIn('unshared',record_actions.review('Customer',client.name)['message'])
        with self.assertRaises(frappe.LinkExistsError):record_actions.remove('Customer',client.name)
        self.assertTrue(frappe.db.exists('Contact',contact));self.assertTrue(frappe.db.exists('Address',address))
        frappe.delete_doc('Project',project.name);record_actions.remove('Customer',client.name)
        self.assertFalse(frappe.db.exists('Contact',contact));self.assertFalse(frappe.db.exists('Address',address))
