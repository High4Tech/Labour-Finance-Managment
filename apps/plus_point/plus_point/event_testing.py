"""Local operator fixtures for browser verification; never whitelisted."""
import json,re
from pathlib import Path
import frappe
from plus_point.tests.test_operations import insert
from plus_point.event_setup import SELECTED


def guard(site):
    if getattr(frappe.local,'request',None) or not frappe.conf.get('allow_tests') or frappe.local.site!=site:
        raise RuntimeError('Local test-enabled operator required')
    frappe.set_user('Administrator')


def browser_fixture(action,run_id):
    guard('qa.localhost')
    if not re.fullmatch('[a-f0-9]{12}',run_id):raise RuntimeError('Exact browser run required')
    from frappe.installer import update_site_config
    prefix='Event Browser QA '+run_id
    backup=Path(frappe.get_site_path('private','backups','pp-event-browser-'+run_id+'.json'))
    if action=='begin':
        if backup.exists() or frappe.db.exists('Company',prefix):raise RuntimeError('Restore this run first')
        from plus_point.testing import _finish_demo_setup
        _finish_demo_setup()
        saved=dict(defaults={key:frappe.defaults.get_user_default(key) for key in ('Company',SELECTED)},entitlement=frappe.conf.get('pp_entitlement'),workspace=frappe.db.get_single_value('PP Workspace Settings','company'),draft=frappe.db.get_single_value('PP Workspace Settings','onboarding_state'),currencies={r.name:r.enabled for r in frappe.get_all('Currency',fields=['name','enabled'])})
        backup.parent.mkdir(parents=True,exist_ok=True);backup.write_text(json.dumps(saved))
        update_site_config('pp_entitlement',dict(valid_until='2099-12-31',limits={}))
        frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
        company=insert('Company',company_name=prefix,abbr=run_id[:5],country='Pakistan',default_currency='PKR')
        frappe.db.set_single_value('PP Workspace Settings','company',company.name)
        worker=insert('Employee',first_name='Sana Browser QA',gender='Female',date_of_birth='1990-01-01',date_of_joining='2020-01-01',company=company.name,status='Active')
        for key in ('Company',SELECTED):frappe.defaults.set_user_default(key,company.name)
        frappe.clear_cache();frappe.db.commit()
        return dict(company=company.name,worker=worker.name,prefix=prefix)
    if action!='end' or not backup.exists():raise RuntimeError('Exact fixture backup required')
    saved=json.loads(backup.read_text());frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
    frappe.db.set_single_value('PP Workspace Settings',dict(company=saved.get('workspace'),onboarding_state=saved.get('draft')))
    projects=frappe.get_all('Project',filters={'company':prefix},pluck='name')
    work=frappe.get_all('PP Work Entry',filters={'project':['in',projects]},fields=['name','status','sales_invoice']) if projects else []
    if frappe.db.exists('GL Entry',{'company':prefix}) or any(r.status!='Draft' or r.sales_invoice for r in work):
        raise RuntimeError('Fixture has recorded history; automatic cleanup refused')
    if projects:
        for row in frappe.get_all('PP Daily Register',filters={'project':['in',projects]},fields=['name','docstatus']):
            if row.docstatus:raise RuntimeError('Fixture has approved attendance; automatic cleanup refused')
            frappe.delete_doc('PP Daily Register',row.name)
    for row in work:frappe.delete_doc('PP Work Entry',row.name)
    receipts=frappe.get_all('PP Import Record',filters={'company':prefix},fields=['name','kind','external_id','document_type','document_name'])
    for receipt in receipts:
        worker=(receipt.kind=='employees' and receipt.document_type=='Employee'
                and re.fullmatch('UX-'+run_id+r'-\d+',receipt.external_id)
                and frappe.db.get_value('Employee',receipt.document_name,'company')==prefix)
        event=(receipt.kind=='events' and receipt.document_type=='PP Event Plan'
                and re.fullmatch('EVT-'+run_id+r'-\d+',receipt.external_id)
                and frappe.db.get_value('PP Event Plan',receipt.document_name,'company')==prefix)
        if not (worker or event):
            raise RuntimeError('Unrecognized imported fixture; automatic cleanup refused')
    # Exact disposable, nonfinancial worker/event receipts only. Production
    # receipts remain immutable; the recorded-history check above still applies.
    for receipt in receipts:frappe.db.delete('PP Import Record',{'name':receipt.name})
    if projects:
        for doctype in ('PP Vehicle Booking','PP Equipment Booking','PP Assignment','PP Event Plan','PP Contract Terms','PP Site','Project'):
            filters={'name':['in',projects]} if doctype=='Project' else {'project':['in',projects]}
            for name in frappe.get_all(doctype,filters=filters,pluck='name'):frappe.delete_doc(doctype,name)
    for doctype in ('Vehicle','Employee'):
        for name in frappe.get_all(doctype,filters={'company':prefix},pluck='name'):frappe.delete_doc(doctype,name)
    customer=frappe.db.get_value('Customer',{'customer_name':prefix+' Client'},'name')
    if customer:
        frappe.db.set_value('Customer',customer,dict(customer_primary_contact=None,customer_primary_address=None))
        for dt in ('Address','Contact'):
            for name in frappe.get_all('Dynamic Link',filters={'link_doctype':'Customer','link_name':customer,'parenttype':dt},pluck='parent'):
                frappe.delete_doc(dt,name)
        for name in frappe.get_all('Contract',filters={'party_type':'Customer','party_name':customer},pluck='name'):frappe.delete_doc('Contract',name)
        frappe.delete_doc('Customer',customer)
    # HRMS creates company-specific account rows on shared claim-type parents.
    for parent in frappe.get_all('Expense Claim Type',pluck='name'):
        doc=frappe.get_doc('Expense Claim Type',parent)
        removed=[row for row in doc.get('accounts',[]) if row.company==prefix]
        if removed:
            for row in removed:doc.remove(row)
            doc.save()
    if frappe.db.exists('Company',prefix):frappe.delete_doc('Company',prefix)
    for key,value in saved['defaults'].items():frappe.defaults.set_user_default(key,value)
    for code,enabled in saved.get('currencies',{}).items():frappe.db.set_value('Currency',code,'enabled',enabled)
    update_site_config('pp_entitlement',saved['entitlement']);frappe.clear_cache();frappe.db.commit();backup.unlink()
    return dict(restored=True)


def describe_demo():
    guard('demo.localhost')
    company='PLUS POINT Demo'
    projects=frappe.get_all('Project',filters={'company':company},fields=['name','project_name','customer','expected_start_date','expected_end_date'])
    frappe.set_user('example@email.com')
    permissions={name:{kind:bool(frappe.has_permission(name,kind)) for kind in ('read','create','write','submit')} for name in ('Customer','Contract','Project','Vehicle','Item','Warehouse','Stock Reconciliation')}
    return dict(permissions=permissions,projects=projects,sites=frappe.get_all('PP Site',fields=['name','project','site_name']),
        terms=frappe.get_all('PP Contract Terms',fields=['name','project','billing_model','effective_start','effective_end']),
        work=frappe.db.sql('select project,min(work_date) first_day,max(work_date) last_day,count(*) rows_count from `tabPP Work Entry` group by project',as_dict=True))


def attendance_browser_fixture(action,run_id):
    """Approve real QA attendance, then remove only its exact unbilled test history."""
    guard('qa.localhost')
    if not re.fullmatch('[a-f0-9]{12}',run_id):raise RuntimeError('Exact browser run required')
    if action=='begin':return browser_fixture(action,run_id)
    prefix='Event Browser QA '+run_id
    backup=Path(frappe.get_site_path('private','backups','pp-event-browser-'+run_id+'.json'))
    if action!='end' or not backup.exists() or not frappe.db.exists('Company',prefix):raise RuntimeError('Exact disposable attendance fixture required')
    frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
    projects=frappe.get_all('Project',filters={'company':prefix},pluck='name')
    if frappe.db.exists('GL Entry',{'company':prefix}):raise RuntimeError('Financial postings present; cleanup refused')
    if projects and frappe.db.exists('PP Wage Settlement',{'project':['in',projects]}):raise RuntimeError('Payments present; cleanup refused')
    work=frappe.get_all('PP Work Entry',filters={'project':['in',projects or ['']]},fields=['name','sales_invoice'])
    names=[r.name for r in work]
    if any(r.sales_invoice for r in work) or names and frappe.db.exists('Sales Invoice Item',{'pp_source_name':['in',names]}):raise RuntimeError('Billed source present; cleanup refused')
    # Only operator-created, exact QA fixtures may be returned to Draft for
    # normal native deletion. Real attendance remains immutable everywhere.
    for name in frappe.get_all('PP Daily Register',filters={'project':['in',projects or ['']]},pluck='name'):
        frappe.db.set_value('PP Daily Register',name,'docstatus',0)
        frappe.delete_doc('PP Daily Register',name)
    for row in work:
        frappe.db.set_value('PP Work Entry',row.name,'status','Draft')
        frappe.delete_doc('PP Work Entry',row.name)
    return browser_fixture('end',run_id)


def hierarchy_browser_fixture(action,run_id):
    """Only exact local QA draft invoices/milestones/files may be cleaned up."""
    guard('qa.localhost')
    if not re.fullmatch('[a-f0-9]{12}',run_id):raise RuntimeError('Exact browser run required')
    if action=='begin':return browser_fixture(action,run_id)
    prefix='Event Browser QA '+run_id
    backup=Path(frappe.get_site_path('private','backups','pp-event-browser-'+run_id+'.json'))
    if action!='end' or not backup.exists() or not frappe.db.exists('Company',prefix):raise RuntimeError('Exact disposable hierarchy fixture required')
    if frappe.db.exists('GL Entry',{'company':prefix}):raise RuntimeError('Posted financial history; cleanup refused')
    invoices=frappe.get_all('Sales Invoice',filters={'company':prefix},fields=['name','docstatus'])
    if any(r.docstatus for r in invoices):raise RuntimeError('Submitted invoices; cleanup refused')
    for row in invoices:frappe.delete_doc('Sales Invoice',row.name)
    projects=frappe.get_all('Project',filters={'company':prefix},pluck='name')
    terms=frappe.get_all('PP Contract Terms',filters={'project':['in',projects or ['']]},pluck='name')
    for name in frappe.get_all('PP Milestone',filters={'contract_terms':['in',terms or ['']]},pluck='name'):
        frappe.db.set_value('PP Milestone',name,'status','Planned');frappe.delete_doc('PP Milestone',name)
    people=frappe.get_all('Employee',filters={'company':prefix},pluck='name')
    for name in frappe.get_all('File',filters={'attached_to_doctype':'Employee','attached_to_name':['in',people or ['']]},pluck='name'):frappe.delete_doc('File',name)
    result=attendance_browser_fixture('end',run_id)
    for dt,filters in [('Designation',{'name':['like','QA role '+run_id+'%']}),('Item',{'item_code':prefix+' Service'})]:
        for name in frappe.get_all(dt,filters=filters,pluck='name'):frappe.delete_doc(dt,name)
    roles=frappe.parse_json(frappe.defaults.get_global_default('pp_event_roles') or '[]')
    frappe.defaults.set_global_default('pp_event_roles',json.dumps([r for r in roles if not r.startswith('QA role '+run_id)]))
    frappe.db.commit();return result


def seed_demo():
    """Adapt only labelled local dummy records; retain all financial history."""
    guard('demo.localhost')
    from frappe.utils import today,add_days
    from plus_point.event_imports import save
    company='PLUS POINT Demo';frappe.get_doc('Company',company)
    titles=[('DHA Homes — Phase 1 (Demo)','Lumen wedding showcase (Demo)','Grand ballroom (Demo)'),
        ('Garden housing project (Demo)','Garden wedding reception (Demo)','Garden marquee (Demo)'),
        ('Canal road works (Demo)','Cedar cultural festival (Demo)','Festival main stage (Demo)'),
        ('Warehouse expansion (Demo)','Orion trade exhibition (Demo)','Exhibition hall (Demo)')]
    for old,title,venue in titles:
        project=frappe.db.get_value('Project',{'company':company,'project_name':['in',[old,title]]},'name')
        if not project:continue
        frappe.db.set_value('Project',project,'project_name',title)
        site=frappe.db.get_value('PP Site',{'project':project},'name')
        if not site:continue
        frappe.db.set_value('PP Site',site,'site_name',venue)
        terms=frappe.db.get_value('PP Contract Terms',{'project':project,'billing_model':'Daily','status':'Active'},['name','effective_start'],as_dict=True)
        if not terms or frappe.db.exists('PP Event Plan',{'project':project}):continue
        first=str(terms.effective_start or today());last=add_days(today(),7)
        assignment=frappe.db.get_value('PP Assignment',{'project':project},['wage_rate','client_rate'],as_dict=True)
        workers=frappe.db.count('PP Assignment',{'project':project}) or 1
        insert('PP Event Plan',event_name=title,project=project,company=company,contract_terms=terms.name,
            start_date=first,end_date=last,wage_rate=assignment.wage_rate if assignment else 2000,
            client_rate=assignment.client_rate if assignment else 3000,
            staffing=[dict(site=site,phase='Event',start_date=first,end_date=last,workers_required=workers)],
            notes='Illustrative event plan over the existing demo records. Existing attendance remains the only source of earned wages.')
        frappe.db.set_value('Project',project,dict(expected_start_date=first,expected_end_date=last))
    for customer,title in [('PLUS POINT Demo','Lumen Celebrations (Demo)'),('Pak Logistics (Demo)','Orion Exhibitions (Demo)'),('Cedar Infrastructure (Demo)','Cedar Events (Demo)')]:
        if frappe.db.exists('Customer',customer):frappe.db.set_value('Customer',customer,'customer_name',title)
    warehouse=frappe.db.get_value('Warehouse',{'company':company,'warehouse_name':'Event equipment (Demo)'},'name')
    if not warehouse:warehouse=save('warehouses',company,dict(warehouse_name='Event equipment (Demo)')).name
    for code,title,qty,rate in [('DEMO-EVENT-CHAIR','Banquet chair (Demo)',120,1500),('DEMO-EVENT-TABLE','Round event table (Demo)',20,8000),
            ('DEMO-EVENT-LIGHT','LED stage light (Demo)',12,12000)]:
        if not frappe.db.exists('Item',code):save('inventory_items',company,dict(item_code=code,item_name=title,stock_uom='Nos',status='Active'))
        if not frappe.db.exists('Stock Ledger Entry',{'item_code':code,'warehouse':warehouse}):
            save('stock_balances',company,dict(date=today(),item_code=code,warehouse=warehouse,quantity=str(qty),valuation_rate=str(rate)))
    for plate,model,seats,capacity in [('DEMO-CREW-01','Crew van (Demo)',12,0),('DEMO-CARGO-01','Equipment truck (Demo)',0,1000)]:
        if not frappe.db.exists('Vehicle',plate):save('vehicles',company,dict(license_plate=plate,make='Toyota' if seats else 'Isuzu',model=model,
            crew_seats=str(seats),cargo_capacity=str(capacity),cargo_uom='kg',fuel_type='Diesel',status='Active'))
    plan=frappe.get_doc('PP Event Plan',frappe.db.get_value('PP Event Plan',{'event_name':'Lumen wedding showcase (Demo)'},'name'))
    args=dict(company=company,project=plan.project,site=plan.staffing[0].site,start_date=today(),end_date=plan.end_date,status='Planned')
    if not frappe.db.exists('PP Vehicle Booking',{'project':plan.project}):
        insert('PP Vehicle Booking',**args,vehicle='DEMO-CREW-01',purpose='Crew',crew_count=6)
        insert('PP Vehicle Booking',**args,vehicle='DEMO-CARGO-01',purpose='Inventory',cargo_load=500)
    if not frappe.db.exists('PP Equipment Booking',{'project':plan.project}):
        insert('PP Equipment Booking',**args,item='DEMO-EVENT-CHAIR',warehouse=warehouse,quantity=60)
    frappe.clear_cache();frappe.db.commit()
    return dict(plan=plan.name,warehouse=warehouse,history_preserved=True,signup='demo')
