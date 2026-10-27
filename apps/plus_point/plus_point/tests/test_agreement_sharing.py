"""Agreement sharing, private documents and requirement availability, rollback-only."""
import unittest,json,io
from pypdf import PdfWriter
from unittest.mock import patch
import frappe
from frappe.utils import today,add_days
from plus_point import agreement_documents as docs,operations as op,people,resources,signing
from plus_point.tests import test_hierarchy as hierarchy
from plus_point.tests.test_operations import insert

class AgreementSharingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):hierarchy.HierarchyTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):hierarchy.HierarchyTests.tearDownClass.__func__(cls)
    agreement=hierarchy.HierarchyTests.agreement
    event=hierarchy.HierarchyTests.event
    def setUp(self):
        hierarchy.HierarchyTests.setUp(self);self.files=set(frappe.get_all('File',pluck='name'))
        stream=io.BytesIO();writer=PdfWriter();writer.add_blank_page(width=595.28,height=841.89);writer.write(stream);self.pdf_bytes=stream.getvalue()
        self.pdf=patch('plus_point.agreement_documents.pdf_content',return_value=self.pdf_bytes);self.pdf.start()
    def tearDown(self):
        for name in set(frappe.get_all('File',pluck='name'))-self.files:frappe.delete_doc('File',name,force=1)
        self.pdf.stop();hierarchy.HierarchyTests.tearDown(self)
    def test_recipient_cc_validation_dedup_and_injection(self):
        self.assertEqual(docs.recipients('sara@example.com','ali@example.com, sara@example.com,ali@example.com'),(['sara@example.com'],['ali@example.com']))
        for to,cc in [('bad',''),('a@example.com,b@example.com',''),('a@example.com','bad'),('a@example.com','b@example.com\nBcc: other@example.com'),('a@example.com',','.join(f'a{i}@example.com' for i in range(11)))]:
            with self.subTest(to=to,cc=cc),self.assertRaises(frappe.ValidationError):docs.recipients(to,cc)
    def test_current_agreement_demand_reduces_category_remaining(self):
        rows=[dict(designation=self.role,start_date=today(),end_date=add_days(today(),4),workers_required=1)]*2
        result=people.capacity(today(),add_days(today(),4),rows,designation=self.role,pending_index=1)['category']
        self.assertEqual((result['total'],result['available'],result['planned'],result['remaining']),(1,1,1,0))
        self.assertEqual(people.capacity(today(),add_days(today(),4),rows[:1],designation=self.role,pending_index=0)['category']['remaining'],1)
    def test_vehicle_options_are_company_scoped_and_report_actual_fleet(self):
        vehicle=insert('Vehicle',license_plate='QA-'+self.f.company.abbr,make='Toyota',model='Hiace',last_odometer=0,acquisition_date=today(),uom='Litre',company=self.f.company.name,pp_event_enabled=1,pp_crew_seats=12)
        fleet=resources.agreement_vehicle_options(today(),add_days(today(),4))
        row=next(v for v in fleet if v['name']==vehicle.name);self.assertEqual(row['vehicle_type'],'Toyota Hiace');self.assertTrue(row['available'])
        a=self.agreement();op.create_plan(a['name'],'Dated fleet event');site=op.agreement(a['name'])['venues'][0]['name']
        resources.save_booking(a['project'],'vehicle',dict(vehicle=vehicle.name,site=site,purpose='Crew',crew_count=1,start_date=today(),end_date=add_days(today(),4),status='Planned'))
        self.assertFalse(next(v for v in resources.agreement_vehicle_options(today(),add_days(today(),4)) if v['name']==vehicle.name)['available'])
        self.assertTrue(next(v for v in resources.agreement_vehicle_options(today(),add_days(today(),4),a['name']) if v['name']==vehicle.name)['available'])
    def test_site_location_is_saved_even_without_a_crew_row(self):
        a=self.agreement();op.save_agreement(dict(staffing=op.agreement(a['name'])['staffing'],sites=['Main venue','Entrance'],site_details={'Entrance':{'city':'Lahore','address_line1':'24 Hall Road'}}),a['name'])
        row=next(v for v in op.agreement(a['name'])['venues'] if v['site_name']=='Entrance');self.assertEqual((row['city'],row['address_line1']),('Lahore','24 Hall Road'))
    def test_pdf_is_private_attached_deduplicated_and_snapshot_preserved(self):
        a=self.agreement();result=docs.finalize(a['name']);file=frappe.get_doc('File',result['pdf']['name']);self.assertEqual(file.is_private,1);self.assertEqual(file.attached_to_name,frappe.get_doc('PP Contract Terms',a['name']).contract)
        self.assertEqual(docs.agreement_pdf(a['name'])['name'],file.name,repr(frappe.get_doc('PP Agreement Share',result['share']['name']).snapshot)+' VS '+repr(signing.snapshot(a['name'])))
        share=frappe.get_doc('PP Agreement Share',result['share']['name']);original=share.snapshot
        __import__('plus_point.agreement_updates',fromlist=['propose']).propose(a['name'],{'scope':'Updated scope for a later document version'},'New document version',method='Company attested')
        self.assertNotEqual(docs.agreement_pdf(a['name'])['name'],file.name)
        self.assertEqual(docs.agreement_pdf(a['name'],share.name)['name'],file.name);self.assertEqual(frappe.get_doc('PP Agreement Share',share.name).snapshot,original)
        self.assertTrue(docs.data(file.name)['content']);self.assertEqual(len(docs.documents(a['name'])),3);self.assertNotIn('<th>Dates</th>',original)
    def test_signed_snapshot_is_in_documents_and_its_pdf_retains_acceptance(self):
        from urllib.parse import urlparse,parse_qs
        a=self.agreement();result=docs.finalize(a['name']);token=parse_qs(urlparse(result['share']['url']).query)['token'][0]
        signing.accept(token,'Sara Khan','sara@example.invalid',1)
        row=next(r for r in docs.documents(a['name']) if r.get('share'))
        file=docs.agreement_pdf(a['name'],row.share)
        self.assertIn('Signed agreement',file['file_name']);self.assertTrue(docs.data(file['name'])['content'])
        self.assertFalse(any(r.get('share') for r in docs.documents(a['name'])))
        self.assertEqual(len(docs.documents(a['name'])),2)

    def test_email_is_explicit_and_attaches_private_pdf_with_cc(self):
        a=self.agreement();original=frappe.db.exists
        def exists(dt,*args,**kwargs):return True if dt=='Email Account' else original(dt,*args,**kwargs)
        with patch.object(frappe.db,'exists',side_effect=exists),patch('frappe.sendmail') as send:
            result=docs.finalize(a['name'],1,'sara@example.com','ali@example.com',1)
            self.assertTrue(result['email_queued']);self.assertEqual(send.call_args.kwargs['cc'],['ali@example.com']);self.assertEqual(send.call_args.kwargs['recipients'],['sara@example.com']);self.assertEqual(len(send.call_args.kwargs['attachments']),1)
    def test_invoice_action_requires_approval_creates_one_draft_and_stores_document(self):
        a=self.agreement(fixed=True);op.save_agreement({'auto_invoice':0},a['name'])
        milestone=insert('PP Milestone',contract_terms=a['name'],milestone_title='Final delivery',due_date=today(),amount=10000,status='Planned')
        with self.assertRaises(frappe.ValidationError):docs.milestone_document(milestone.name)
        milestone.status='Approved';milestone.save()
        with patch('plus_point.operations.invoice_pdf_content',return_value=self.pdf_bytes):
            result=docs.milestone_document(milestone.name);again=docs.milestone_document(milestone.name)
            from plus_point.experience import pdf_data
            self.assertTrue(pdf_data(result['invoice'])['content'])
        self.assertEqual(result,again);self.assertEqual(frappe.db.count('Sales Invoice',{'project':a['project']}),1);self.assertEqual(frappe.db.get_value('Sales Invoice',result['invoice'],'docstatus'),0);self.assertFalse(frappe.db.exists('GL Entry',{'voucher_no':result['invoice']}))
        self.assertIn(result['pdf']['name'],[r.name for r in docs.documents(a['name'])])
        frappe.delete_doc('Sales Invoice',result['invoice'])
        self.assertFalse(frappe.db.get_value('PP Milestone',milestone.name,'sales_invoice'));self.assertEqual(docs.documents(a['name']),[])
    def test_created_invoice_appears_in_documents_before_first_pdf_open(self):
        a=self.agreement(fixed=True);result=op.save_milestone(a['name'],dict(milestone_title='Delivery',due_date=today(),amount=10000,status='Approved'))
        rows=docs.documents(a['name']);self.assertEqual(len(rows),1);self.assertEqual(rows[0].invoice,result['sales_invoice'])
        with patch('plus_point.operations.invoice_pdf_content',return_value=self.pdf_bytes):file=docs.invoice_pdf(result['sales_invoice'])
        rows=docs.documents(a['name']);self.assertEqual(len(rows),1);self.assertEqual(rows[0].name,file['name']);self.assertFalse(rows[0].get('invoice'))

    def test_custom_category_can_be_created_inside_worker_department(self):
        role=op.create_category('Custom guest support QA')['name'];department=people.work_options()['departments'][0]['value']
        worker=frappe.get_doc('Employee',self.worker.name);worker.department=department;worker.designation=role;worker.save()
        self.assertIn(role,people.work_options(worker.name)['roles'][department])

    def test_document_endpoints_reject_other_company(self):
        a=self.agreement()
        file=docs.agreement_pdf(a['name'])
        with patch('plus_point.event_setup.companies',return_value=[]):
            with self.assertRaises((frappe.PermissionError,frappe.ValidationError)):docs.data(file['name'])
            for fn in (docs.agreement_pdf,docs.documents,docs.finalize):
                with self.assertRaises((frappe.PermissionError,frappe.ValidationError)):fn(a['name'])
