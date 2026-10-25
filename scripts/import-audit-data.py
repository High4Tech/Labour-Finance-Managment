"""Seed and verify only the owned, disposable upload-audit database."""
import json
from pathlib import Path
import re
import sys
import frappe


def main():
    action,run=sys.argv[1:3]
    if not re.fullmatch('[a-f0-9]{12}',run):raise RuntimeError('Exact audit run required')
    site='upload-audit-'+run+'.localhost'
    marker=Path(site)/'private/pp-upload-audit.json'
    if not marker.exists() or json.loads(marker.read_text())['run']!=run:raise RuntimeError('Owned audit site required')
    frappe.init(site=site);frappe.connect();frappe.set_user('Administrator')
    try:
        if action=='seed':
            from plus_point.tests.test_operations import fixture,insert
            from plus_point.event_setup import SELECTED
            from frappe.utils import today,add_days
            from plus_point import imports
            f=fixture('Upload Audit '+run)
            fixed_contract=insert('Contract',party_type='Customer',party_name=f.customer.name,contract_terms='Fixed audit contract',start_date=today())
            fixed=insert('PP Contract Terms',contract=fixed_contract.name,project=f.project.name,billing_model='Fixed',fixed_amount=10000,currency='PKR',status='Active',effective_start=today())
            supplier=insert('Supplier',supplier_name='Audit supplier '+run,supplier_group='All Supplier Groups',supplier_type='Company')
            frappe.db.set_single_value('PP Workspace Settings',dict(company=f.company.name,onboarding_state=json.dumps(dict(step='done',company=f.company.name))))
            for key in ('Company',SELECTED):frappe.defaults.set_user_default(key,f.company.name)
            stamp=today();start=add_days(stamp,2);end=add_days(stamp,4)
            client=dict(contact_name='Ayesha Malik',email='upload-audit@example.invalid',phone='+923001234567',country='Pakistan',city='Karachi',address_line1='12 Audit Road')
            rows={
              'employees':dict(external_id='worker-new',employee='Sana Audit',first_name='Sana',last_name='Audit',gender='Female',date_of_birth='1990-01-01',date_of_joining='2020-01-01',cell_number='+923001234567',status='Active',designation='Event crew',pp_salary_basis='Daily',pp_daily_rate='100',pp_monthly_rate='3000',pp_leaves_per_month='2',pp_loan_allowed='1',pp_loan_wait_months='3',pp_loan_deduction_percent='10'),
              'clients':dict(external_id='client-new',customer='New audit client '+run,customer_name='New audit client '+run,customer_type='Company',**client),
              'warehouses':dict(external_id='warehouse-new',warehouse_name='Audit warehouse '+run,warehouse_type='Rented',status='Active'),
              'inventory_items':dict(external_id='item-new',item_code='AUDIT-'+run,item_name='Audit chair '+run,stock_uom='Nos',status='Active'),
              'vehicles':dict(external_id='vehicle-new',license_plate='AUDIT-'+run,make='Toyota',model='Crew van',crew_seats='10',cargo_capacity='20',cargo_uom='kg',fuel_type='Diesel',status='Active'),
              'events':dict(external_id='event-new',event_name='Audit event '+run,customer='New event client '+run,start_date=start,end_date=end,site_name='Audit stage',workers_per_day='1',billing_model='Daily',client_rate='250',agreement='Crew and optional transport',designation='Event crew',agreement_currency='PKR',customer_type='Company',**{'client_'+k:v for k,v in client.items()}),
              'agreements':dict(external_id='agreement-new',agreement_title='Audit agreement '+run,customer='New agreement client '+run,start_date=start,end_date=end,status='Active',billing_model='Fixed',agreement_currency='PKR',fixed_amount='5000',scope='Crew and vehicle requirements',conditions='Arrive on time|Use protective equipment',site_name='Audit agreement site',designation='Event crew',workers_per_day='1',vehicle_type='Crew van',vehicle_quantity='2',customer_type='Company',**{'client_'+k:v for k,v in client.items()}),
              'event_sites':dict(external_id='site-new',site='New audit venue '+run,site_name='New audit venue '+run,project='import:event-new',address='12 Audit Road',status='Active',country='Pakistan',city='Karachi',address_line1='12 Audit Road'),
              'stock_balances':dict(external_id='stock-new',item_code='import:item-new',warehouse='import:warehouse-new',quantity='10'),
              'work':dict(external_id='work-new',assignment=f.assignment.name,work_date=stamp,units='1'),
              'milestones':dict(external_id='milestone-new',contract_terms=fixed.name,title='Audit completed milestone',date=stamp,amount='500'),
              'expenses':dict(external_id='expense-new',date=stamp,project=f.project.project_name,supplier=supplier.supplier_name,item_code=f.item.item_name,amount='200',description='Audit historical supplier cost'),
              'invoices':dict(external_id='invoice-new',date=stamp,project=f.project.project_name,customer=f.customer.customer_name,item_code=f.item.item_name,amount='3000',source_type='PP Work Entry',source_name='import:work-new',description='Audit approved work invoice'),
              'receipts':dict(external_id='receipt-new',date=stamp,invoice='import:invoice-new',amount='500',bank_account=f.company.default_cash_account),
              'worker_payments':dict(external_id='payment-new',date=stamp,project=f.project.project_name,employee=f.employee.employee_name,amount='500',bank_account=f.company.default_cash_account),
            }
            rows['employees'].update(department='Audit crew '+run,employment_type='Audit contract '+run,branch='Audit branch '+run)
            data=dict(site=site,run=run,company=f.company.name,project=f.project.name,worker=f.employee.name,rows=rows,schemas=imports.SCHEMAS,
                required=dict(employees='first_name',clients='customer_name',warehouses='warehouse_name',inventory_items='item_name',vehicles='license_plate',events='event_name',agreements='agreement_title',event_sites='site_name',stock_balances='quantity',work='units',milestones='title',expenses='amount',invoices='amount',receipts='amount',worker_payments='amount'))
            (marker.parent/'pp-upload-data.json').write_text(json.dumps(data))
            frappe.db.commit();frappe.clear_cache();print(json.dumps(data))
        elif action=='files':
            import base64,io
            from datetime import datetime
            from openpyxl import Workbook
            from plus_point import imports
            data=json.loads((marker.parent/'pp-upload-data.json').read_text());data['schemas']=imports.SCHEMAS
            data['workbooks']={}
            for kind,row in data['rows'].items():
                book=Workbook();sheet=book.active;sheet.title='Import'
                sheet.append(imports.SCHEMAS[kind]);sheet.append([datetime.strptime(row[key],'%Y-%m-%d') if row.get(key) and key in ('date','work_date','date_of_birth','date_of_joining','start_date','end_date') else row.get(key,'') for key in imports.SCHEMAS[kind]])
                for cell in sheet[2]:
                    if isinstance(cell.value,datetime):cell.number_format='yyyy-mm-dd'
                content=io.BytesIO();book.save(content);book.close();data['workbooks'][kind]=base64.b64encode(content.getvalue()).decode()
            print(json.dumps(data))
        elif action=='verify':
            from plus_point.api import project_summary
            from plus_point.imports import record_key
            data=json.loads((marker.parent/'pp-upload-data.json').read_text())
            receipts=[]
            for kind,row in data['rows'].items():
                receipt=frappe.db.get_value('PP Import Record',record_key(data['company'],kind,row['external_id']),['name','document_type','document_name'],as_dict=True)
                if receipt:
                    doc=frappe.get_doc(receipt.document_type,receipt.document_name)
                    receipts.append(dict(kind=kind,exists=True,doctype=doc.doctype,name=doc.name,docstatus=doc.docstatus))
            summary=project_summary(data['project'])
            print(json.dumps(dict(records=receipts,summary=summary,gl_entries=frappe.db.count('GL Entry',{'company':data['company']})),default=str))
        else:raise RuntimeError('Use seed or verify')
    finally:frappe.destroy()


if __name__=='__main__':main()
