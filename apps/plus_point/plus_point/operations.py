"""Agreement-led operations. Composed screens retain native records and audit history."""
from collections import defaultdict
from decimal import Decimal
import json
import re
import frappe
from frappe.utils import getdate, today, add_days
from plus_point.setup_flow import require_customer, linked
from plus_point.finance import money

EVENT_ROLES = ('Event manager', 'Site supervisor', 'Crew leader', 'Event crew', 'Stagehand',
    'Electrician', 'Lighting technician', 'Sound technician', 'AV technician', 'Rigger',
    'Carpenter', 'Decorator', 'Usher', 'Security staff', 'Cleaner', 'Driver', 'Warehouse crew')


def event_roles():
    """Event choices do not inherit unrelated ERP demonstration designations."""
    custom=frappe.parse_json(frappe.defaults.get_global_default('pp_event_roles') or '[]')
    return sorted(set(EVENT_ROLES) | set(custom), key=str.casefold)


def install_event_defaults():
    """Native event roles are local reference data, not worker accounts."""
    frappe.set_user('Administrator')
    from plus_point.install import ensure_event_archive_field
    ensure_event_archive_field()
    for title in EVENT_ROLES:ensure_event_role(title)
    frappe.db.commit()
    return dict(categories=len(EVENT_ROLES))


def ensure_event_role(title):
    if not frappe.db.exists('Designation',title):
        if title not in event_roles():frappe.throw('Choose an event crew category, or add a new category first.')
        frappe.get_doc(dict(doctype='Designation',designation_name=title)).insert()


def service_item():
    """Create the application's native non-stock service when it is first needed."""
    code='PP-EVENT-SERVICE'
    frappe.db.get_value('DocType','Item','name',for_update=True)
    if frappe.db.exists('Item',code):
        item=linked('Item',code)
        if item.disabled or item.is_stock_item:frappe.throw('The Event services item must be enabled and non-stock before billing.')
        return item.name
    group=frappe.db.get_value('Item Group',{'name':'Services','is_group':0},'name') or frappe.db.get_value('Item Group',{'is_group':0},'name')
    unit=frappe.db.get_value('UOM',{'name':'Nos'},'name') or frappe.db.get_value('UOM',{},'name')
    return frappe.get_doc(dict(doctype='Item',item_code=code,item_name='Event services',
        item_group=group,stock_uom=unit,is_stock_item=0)).insert().name


@frappe.whitelist(methods=['POST'])
def prepare_billing(contract_terms):
    terms=terms_doc(contract_terms,True)
    if not terms.billing_item:
        terms.billing_item=service_item();terms.save()
    from plus_point.billing import invoice_options
    return dict(invoice_options(terms.name),item=terms.billing_item,
        service_name=frappe.db.get_value('Item',terms.billing_item,'item_name'))


def company():
    require_customer()
    from plus_point.event_setup import companies
    rows=companies()
    if not rows:frappe.throw('Complete your business setup first.')
    return linked('Company',rows[0].name)


def terms_doc(name,write=False):
    business=company();doc=linked('PP Contract Terms',name)
    linked('Project',doc.project,business.name)
    doc.check_permission('write' if write else 'read')
    return doc


@frappe.whitelist()
def catalogue():
    business=company()
    projects={r.name:r for r in frappe.get_list('Project',filters={'company':business.name,'pp_archived':0},fields=['name','project_name','customer','status'],limit_page_length=0)}
    terms=frappe.get_list('PP Contract Terms',filters={'project':['in',list(projects) or ['']]},fields=['name','project','contract','billing_model','status','fixed_amount','effective_start','effective_end','agreement_title'],order_by='modified desc',limit_page_length=0)
    clients={r.name:r.customer_name for r in frappe.get_list('Customer',filters={'disabled':0},fields=['name','customer_name'],order_by='customer_name,name',limit_page_length=0)}
    for row in terms:row.update(title=row.agreement_title or projects[row.project].project_name,customer=projects[row.project].customer,client=clients.get(projects[row.project].customer,''))
    plans=frappe.get_list('PP Event Plan',filters={'company':business.name,'project':['in',list(projects) or ['']]},fields=['name','event_name','contract_terms','project','start_date','end_date','crew_allocated'],order_by='start_date desc,event_name',limit_page_length=0)
    return dict(currency=business.default_currency,country=business.country,agreements=terms,plans=plans,
        clients=[dict(name=k,title=v) for k,v in clients.items()],
        designations=event_roles(),
        items=frappe.get_list('Item',filters={'is_stock_item':0,'disabled':0},fields=['name','item_name'],order_by='item_name,name',limit_page_length=0))


def validate_agreement(doc):
    if not doc.get('staffing'):return
    project=linked('Project',doc.project)
    from plus_point.events import span,positive
    seen=set()
    for row in doc.staffing:
        site=linked('PP Site',row.site);linked('Designation',row.designation)
        if site.project!=project.name:frappe.throw('Agreement venues must belong to this event.')
        span(row.start_date,row.end_date)
        if getdate(row.start_date)<getdate(doc.effective_start) or doc.effective_end and getdate(row.end_date)>getdate(doc.effective_end):frappe.throw('Staffing dates must fall within the agreement dates.')
        positive(row.workers_required,'Workers per day',whole=True)
        if row.workers_required>500:frappe.throw('Use at most 500 workers per role/site/day.')
        positive(row.wage_rate,'Daily wage');positive(row.client_rate,'Client rate',allow_zero=doc.billing_model=='Fixed')
        if doc.billing_model=='Fixed' and money(row.client_rate):frappe.throw('Fixed agreements use milestones rather than worker-day client charges.')
        key=(row.site,row.designation)
        for previous in doc.staffing:
            if previous==row:break
            if (previous.site,previous.designation)==key and getdate(previous.start_date)<=getdate(row.end_date) and getdate(previous.end_date)>=getdate(row.start_date):frappe.throw('Combine overlapping requirements for the same venue and role.')
        seen.add(key)
    old=doc.get_doc_before_save()
    fields=('site','designation','start_date','end_date','workers_required','wage_rate','client_rate','phase')
    signature=lambda d:[tuple(str(money(r.get(f) or 0)) if f in ('wage_rate','client_rate') else str(int(r.get(f) or 0)) if f=='workers_required' else str(r.get(f) or '') for f in fields) for r in d.get('staffing',[])]
    if old and signature(old)!=signature(doc) and frappe.db.exists('PP Assignment',{'contract_terms':doc.name}):
        frappe.throw('This agreement has allocations. Keep contracted staffing as the baseline; manage additional crew and dated transfers in Event plans.')
    if doc.get('auto_invoice') and not doc.get('billing_item'):frappe.throw('Choose a billing service item for automatic milestone invoices.')


@frappe.whitelist(methods=['POST'])
def save_agreement(values,name=None):
    business=company();values=frappe._dict(frappe.parse_json(values) or {})
    frappe.db.savepoint('pp_agreement_save')
    try:
        if name:
            doc=terms_doc(name,True);project=linked('Project',doc.project);contract=linked('Contract',doc.contract)
            customer=project.customer
            if values.get('customer') and values.customer!=customer:frappe.throw('The client of an existing agreement cannot change.')
        else:
            if values.get('customer'):customer=linked('Customer',values.customer).name
            else:
                from plus_point.clients import create
                customer=create(values.get('client') or {}).name
            title=str(values.get('agreement_title') or '').strip()
            if not title:frappe.throw('Enter an agreement name.')
            project=frappe.get_doc(dict(doctype='Project',project_name=title,company=business.name,customer=customer,
                expected_start_date=values.effective_start,expected_end_date=values.effective_end)).insert()
            contract=frappe.new_doc('Contract');contract.update(dict(party_type='Customer',party_name=customer,
                start_date=values.effective_start,end_date=values.effective_end,contract_terms=values.get('scope') or title));contract.insert()
            doc=frappe.new_doc('PP Contract Terms');doc.update(dict(project=project.name,contract=contract.name,currency=business.default_currency))
        if values.get('client') and (name or values.get('customer')):
            from plus_point.clients import save
            save(values.client,customer)
        for key in ('agreement_title','billing_model','effective_start','effective_end','fixed_amount','billing_item','auto_invoice','status'):
            if key in values:doc.set(key,values[key])
        if not doc.billing_item:doc.billing_item=service_item()
        if values.get('scope') is not None:
            contract.check_permission('write');contract.contract_terms=values.scope;contract.save()
        if 'staffing' in values:
            locations={r.site_name:r.name for r in frappe.get_list('PP Site',filters={'project':project.name},fields=['name','site_name'],limit_page_length=0)}
            rows=[]
            for raw in values.staffing:
                raw=frappe._dict(raw);site=raw.get('site')
                if raw.get('designation'):ensure_event_role(raw.designation)
                if site:
                    venue=linked('PP Site',site)
                    if venue.project!=project.name:frappe.throw('Choose a venue in this agreement.')
                else:
                    title=str(raw.get('site_name') or '').strip()
                    if not title:frappe.throw('Enter each venue name.')
                    site=locations.get(title)
                    if not site:
                        venue=frappe.get_doc(dict(doctype='PP Site',project=project.name,site_name=title,is_active=1,
                            **{key:raw.get(key) for key in ('country','state','city','address_line1','address_line2','postal_code','latitude','longitude')})).insert()
                        site=locations[title]=venue.name
                rows.append(dict(site=site,**{key:raw.get(key) for key in ('designation','start_date','end_date','workers_required','wage_rate','client_rate','phase')}))
            if not rows:frappe.throw('Add at least one venue and worker category.')
            doc.set('staffing',rows)
        doc.save()
        return dict(name=doc.name,project=project.name)
    except Exception:
        frappe.db.rollback(save_point='pp_agreement_save');raise


@frappe.whitelist()
def agreement(name):
    doc=terms_doc(name);project=linked('Project',doc.project);contract=linked('Contract',doc.contract)
    from plus_point.clients import details
    result=doc.as_dict();result.update(client_company=project.company,scope=contract.contract_terms,customer=project.customer,client=details(project.customer),is_signed=contract.get('is_signed'),
        files=frappe.get_list('File',filters={'attached_to_doctype':'Contract','attached_to_name':contract.name},fields=['name','file_name','file_url'],limit_page_length=0),
        venues=frappe.get_list('PP Site',filters={'project':project.name},fields=['name','site_name','country','city','address_line1'],order_by='site_name',limit_page_length=0),
        milestones=frappe.get_list('PP Milestone',filters={'contract_terms':name},fields=['name','milestone_title','due_date','amount','status','sales_invoice'],order_by='due_date,name',limit_page_length=0))
    return result


@frappe.whitelist(methods=['POST'])
def create_plan(contract_terms,event_name,notes=None):
    doc=terms_doc(contract_terms)
    if doc.status!='Active':frappe.throw('Activate this agreement before planning the event.')
    from plus_point.budget import lock_project
    lock_project(doc.project)
    existing=frappe.db.get_value('PP Event Plan',{'project':doc.project},'name')
    if existing:return dict(name=existing,existing=True)
    if not doc.staffing:frappe.throw('Add venue and worker-category requirements in the agreement first.')
    if not str(event_name or '').strip():frappe.throw('Enter the event name.')
    rows=[{key:r.get(key) for key in ('site','phase','start_date','end_date','workers_required','designation','wage_rate','client_rate')} for r in doc.staffing]
    plan=frappe.get_doc(dict(doctype='PP Event Plan',event_name=event_name,project=doc.project,company=company().name,
        contract_terms=doc.name,start_date=min(r['start_date'] for r in rows),end_date=max(r['end_date'] for r in rows),
        wage_rate=rows[0]['wage_rate'],client_rate=rows[0]['client_rate'],staffing=rows,notes=notes or '')).insert()
    return dict(name=plan.name,existing=False)


@frappe.whitelist()
def plan(name):
    from plus_point.events import plan_doc,timeline,crew_proposal
    doc=plan_doc(name);terms_doc(doc.contract_terms)
    result=doc.as_dict();result.update(timeline=timeline(name),agreement=agreement(doc.contract_terms))
    workers={r.name:r for r in frappe.get_list('Employee',filters={'company':doc.company},fields=['name','employee_name','designation','image'],limit_page_length=0)}
    allocations=frappe.get_list('PP Assignment',filters={'project':doc.project},fields=['name','employee','site','start_date','end_date','wage_rate','client_rate'],order_by='start_date,employee',limit_page_length=0)
    for row in allocations:
        person=workers.get(row.employee);row.update(worker=person.employee_name if person else row.employee,designation=person.designation if person else '')
    project=linked('Project',doc.project)
    result['allocations']=allocations;result['coverage']=coverage(doc)
    result.update(budget=project.estimated_costing,enforce_budget=project.pp_enforce_spending_budget)
    result['reservations']=[]
    for kind,label in [('PP Vehicle Booking','vehicle'),('PP Equipment Booking','item')]:
        for row in frappe.get_list(kind,filters={'project':doc.project,'status':'Planned'},fields=['name',label,'site','start_date','end_date'],limit_page_length=0):
            result['reservations'].append(dict(name=row.name,title=row[label],site=frappe.db.get_value('PP Site',row.site,'site_name'),start=str(row.start_date),end=str(row.end_date)))
    return result


@frappe.whitelist(methods=['POST'])
def save_project(name,values):
    from plus_point.events import plan_doc
    doc=plan_doc(name,True);terms_doc(doc.contract_terms)
    data=frappe._dict(frappe.parse_json(values) or {})
    project=linked('Project',doc.project);project.check_permission('write')
    project.estimated_costing=data.get('budget',0);project.pp_enforce_spending_budget=frappe.utils.cint(data.get('enforce_budget'));project.save()
    doc.notes=data.get('notes') or '';doc.save();return dict(name=doc.name)


def coverage(doc):
    """Compare actual allocations to the agreed category/day baseline, including extras."""
    terms=terms_doc(doc.contract_terms)
    baseline=terms.staffing or doc.staffing
    assignments=frappe.get_list('PP Assignment',filters={'project':doc.project},fields=['employee','site','start_date','end_date'],limit_page_length=0)
    roles={r.name:r.designation for r in frappe.get_list('Employee',filters={'company':doc.company},fields=['name','designation'],limit_page_length=0)}
    sites={r.name:r.site_name for r in frappe.get_list('PP Site',filters={'project':doc.project},fields=['name','site_name'],limit_page_length=0)}
    rows=[]
    from plus_point.events import span
    for day in span(doc.start_date,doc.end_date):
        required=defaultdict(int);actual=defaultdict(int);planned=defaultdict(int)
        for r in baseline:
            if getdate(r.start_date)<=getdate(day)<=getdate(r.end_date):required[(r.site,r.get('designation') or '')]+=int(r.workers_required)
        for r in doc.staffing:
            if getdate(r.start_date)<=getdate(day)<=getdate(r.end_date):planned[(r.site,r.get('designation') or '')]+=int(r.workers_required)
        for r in assignments:
            if getdate(r.start_date)<=getdate(day)<=getdate(r.end_date or doc.end_date):
                key=(r.site,roles.get(r.employee) or '')
                if (r.site,'') in required:key=(r.site,'')
                actual[key]+=1
        for key in sorted(set(required)|set(actual)|set(planned)):
            wanted=required[key];count=actual[key];target=planned[key]
            rows.append(dict(date=day,site=key[0],venue=sites.get(key[0],key[0]),designation=key[1] or 'All crew',required=wanted,planned=target,assigned=count,planned_extra=max(0,target-wanted),extra=max(0,count-wanted),missing=max(0,target-count)))
    return rows


@frappe.whitelist(methods=['POST'])
def auto_assign(name):
    from plus_point.events import plan_doc,crew_proposal,validate_plan
    doc=plan_doc(name,True);terms_doc(doc.contract_terms)
    from plus_point.budget import lock_project
    lock_project(doc.project)
    frappe.db.get_value('PP Event Plan',name,'name',for_update=True);doc.reload()
    # Select only matching available categories; existing allocations count as cover.
    doc.selected_crew='';proposal=crew_proposal(doc,lock=True)
    if proposal['shortages']:
        detail='; '.join(f"{r['designation']}: {r['missing']} missing ({r['from_date']} to {r['to_date']})" for r in proposal['shortages'])
        frappe.throw('Not enough available crew. '+detail+'. Add workers or revise the requirements.')
    frappe.db.savepoint('pp_auto_staff')
    try:
        for row in proposal['assignments']:
            frappe.get_doc(dict(doctype='PP Assignment',employee=row['employee'],project=doc.project,site=row['site'],contract_terms=doc.contract_terms,
                start_date=row['start_date'],end_date=row['end_date'],wage_rate=row['wage_rate'],client_rate=row['client_rate'],pp_event_plan=name)).insert()
        frappe.db.set_value('PP Event Plan',name,'crew_allocated',1)
        return dict(created=len(proposal['assignments']))
    except Exception:
        frappe.db.rollback(save_point='pp_auto_staff');raise


@frappe.whitelist()
def available_crew(name,requirement):
    from plus_point.events import plan_doc
    from plus_point.crew import available
    doc=plan_doc(name);terms_doc(doc.contract_terms)
    row=next((r for r in doc.staffing if r.name==requirement),None)
    if not row:frappe.throw('Reload the site requirements.')
    result=available(doc.company,row.start_date,row.end_date)
    assigned={r.employee:r.name for r in frappe.get_list('PP Assignment',filters={
        'project':doc.project,'site':row.site,'start_date':['<=',row.end_date]},
        fields=['name','employee','end_date'],limit_page_length=0)
        if not r.end_date or getdate(r.end_date)>=getdate(row.start_date)}
    roles={r.name:r.designation for r in frappe.get_list('Employee',filters={'company':doc.company},fields=['name','designation'],limit_page_length=0)}
    result['rows']=[dict(r,designation=roles.get(r['name']) or '',assigned=r['name'] in assigned,
        assignment=assigned.get(r['name'])) for r in result['rows'] if not row.designation or roles.get(r['name'])==row.designation]
    return result


@frappe.whitelist(methods=['POST'])
def assign_crew(name,requirement,employees):
    from plus_point.events import plan_doc
    from plus_point.crew import assign,selection
    doc=plan_doc(name,True);terms_doc(doc.contract_terms)
    row=next((r for r in doc.staffing if r.name==requirement),None)
    if not row:frappe.throw('Reload the site requirements.')
    names=selection(frappe.parse_json(employees))
    for employee in names:
        worker=linked('Employee',employee,doc.company)
        if row.designation and worker.designation!=row.designation:frappe.throw('Select workers in the required category.')
    from plus_point.budget import lock_project
    lock_project(doc.project)
    existing={r.employee for r in frappe.get_list('PP Assignment',filters={'project':doc.project,'site':row.site,
        'start_date':['<=',row.end_date]},fields=['employee','end_date'],limit_page_length=0)
        if not r.end_date or getdate(r.end_date)>=getdate(row.start_date)}
    names=[n for n in names if n not in existing]
    result=assign(doc.project,row.site,doc.contract_terms,row.start_date,row.end_date,row.wage_rate or doc.wage_rate,row.client_rate or doc.client_rate,names) if names else dict(created=0)
    frappe.db.set_value('PP Event Plan',name,'crew_allocated',int(all(not r['missing'] for r in coverage(doc))))
    return result


@frappe.whitelist(methods=['POST'])
def add_requirement(name,values):
    from plus_point.events import plan_doc
    doc=plan_doc(name,True);terms_doc(doc.contract_terms)
    raw=frappe._dict(frappe.parse_json(values) or {})
    doc.append('staffing',{key:raw.get(key) for key in ('site','designation','start_date','end_date','workers_required','wage_rate','client_rate','phase')})
    doc.save();return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
def update_headcount(name,requirement,workers_required):
    from plus_point.events import plan_doc
    doc=plan_doc(name,True);terms_doc(doc.contract_terms)
    row=next((r for r in doc.staffing if r.name==requirement),None)
    if not row:frappe.throw('Reload the event requirements.')
    row.workers_required=workers_required;doc.save()
    # Changing a target never silently allocates/releases a person or changes a rate.
    return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
def move_worker(assignment,effective_date,target_plan=None,site=None,end_date=None):
    """End the old commitment before a new one; never rewrite attendance or rates."""
    business=company();old=linked('PP Assignment',assignment);old.check_permission('write');linked('Project',old.project,business.name)
    target=linked('PP Event Plan',target_plan) if target_plan else None
    from plus_point.budget import lock_project
    for name in sorted({old.project}|({target.project} if target else set())):lock_project(name)
    old=frappe.get_doc('PP Assignment',assignment,for_update=True)
    frappe.db.get_value('Employee',old.employee,'name',for_update=True)
    first=getdate(effective_date)
    if first<getdate(today()):frappe.throw('Use today or a future date for transfers. Past attendance stays unchanged.')
    if first<getdate(old.start_date) or old.end_date and first>getdate(old.end_date):frappe.throw('Choose a date within the current allocation.')
    if frappe.db.exists('PP Work Entry',{'assignment':old.name,'work_date':['>=',first]}):frappe.throw('Attendance already exists on or after this date. Choose a date after the last recorded work.')
    frappe.db.savepoint('pp_move_worker')
    try:
        lines=frappe.get_all('PP Register Line',filters={'assignment':old.name},fields=['name','parent','attendance_status','work_entry'])
        for row in lines:
            register=linked('PP Daily Register',row.parent)
            if getdate(register.work_date)<first:continue
            register.check_permission('write')
            if register.docstatus or row.work_entry or row.attendance_status!='Not marked':frappe.throw('Clear unapproved marks after the transfer date before moving this worker.')
            register.remove(next(r for r in register.entries if r.name==row.name));register.save()
        if first==getdate(old.start_date):frappe.delete_doc('PP Assignment',old.name)
        else:old.end_date=add_days(first,-1);old.save()
        if old.get('pp_event_plan'):frappe.db.set_value('PP Event Plan',old.pp_event_plan,'crew_allocated',0)
        if target:
            linked('Project',target.project,business.name);terms=terms_doc(target.contract_terms)
            role=frappe.db.get_value('Employee',old.employee,'designation')
            last=getdate(end_date or target.end_date)
            matching=[r for r in target.staffing if r.site==site and (not r.designation or r.designation==role) and getdate(r.start_date)<=first and getdate(r.end_date)>=last]
            if not matching:frappe.throw('The destination needs a matching worker category and dates. Add the category to the plan first.')
            row=matching[0]
            from plus_point.crew import validate_selected
            validate_selected([old.employee],business.name,first,last,lock=True)
            new=frappe.get_doc(dict(doctype='PP Assignment',employee=old.employee,site=site,project=target.project,contract_terms=terms.name,
                start_date=first,end_date=last,wage_rate=row.wage_rate or target.wage_rate,client_rate=(row.client_rate or target.client_rate) if terms.billing_model=='Daily' else 0,pp_event_plan=target.name)).insert()
            return dict(name=new.name,transferred=True)
        return dict(transferred=False,released=True)
    except Exception:
        frappe.db.rollback(save_point='pp_move_worker');raise


@frappe.whitelist(methods=['POST'])
def save_milestone(contract_terms,values,name=None):
    terms=terms_doc(contract_terms,True);values=frappe._dict(frappe.parse_json(values) or {})
    doc=linked('PP Milestone',name) if name else frappe.new_doc('PP Milestone')
    if name and doc.contract_terms!=terms.name:frappe.throw('Choose a milestone in this agreement.')
    doc.update(dict(contract_terms=terms.name,**{k:values.get(k) for k in ('milestone_title','due_date','amount','status')}));doc.save()
    return dict(name=doc.name,sales_invoice=frappe.db.get_value('PP Milestone',doc.name,'sales_invoice'))


def milestone_invoice(doc,method=None):
    if doc.status!='Approved' or doc.sales_invoice or frappe.flags.in_migrate:return
    terms=frappe.get_doc('PP Contract Terms',doc.contract_terms)
    if not terms.get('auto_invoice'):return
    if not terms.billing_item:
        terms.billing_item=service_item();frappe.db.set_value('PP Contract Terms',terms.name,'billing_item',terms.billing_item)
    from plus_point.billing import create_invoice
    create_invoice(terms.name,terms.billing_item,source_names=[doc.name])


@frappe.whitelist()
def billing(contract_terms):
    terms=terms_doc(contract_terms)
    from plus_point.api import project_summary
    source_type='PP Milestone' if terms.billing_model=='Fixed' else 'PP Work Entry'
    return dict(agreement=agreement(terms.name),totals=project_summary(terms.project),
        unbilled_count=frappe.db.count(source_type,{'contract_terms':terms.name,'status':'Approved','sales_invoice':['is','not set'],
            ('amount' if source_type=='PP Milestone' else 'billable_amount'):['>',0]}),
        invoices=frappe.get_list('Sales Invoice',filters={'project':terms.project},fields=['name','posting_date','due_date','grand_total','outstanding_amount','currency','docstatus','status'],order_by='posting_date desc,name desc',limit_page_length=0))


@frappe.whitelist(methods=['POST'])
def extra_invoice(contract_terms,item_code,description,amount):
    terms=terms_doc(contract_terms);project=linked('Project',terms.project)
    from plus_point.events import positive
    positive(amount,'Invoice amount');linked('Item',item_code)
    if not str(description or '').strip():frappe.throw('Describe the extra charge.')
    doc=frappe.get_doc(dict(doctype='Sales Invoice',company=project.company,project=project.name,customer=project.customer,
        currency=terms.currency,conversion_rate=1,items=[dict(item_code=item_code,description=description,qty=1,rate=amount,project=project.name)])).insert()
    return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
def update_invoice(name,values):
    business=company();doc=linked('Sales Invoice',name);linked('Project',doc.project,business.name);doc.check_permission('write')
    if doc.docstatus:frappe.throw('Only draft invoices can be edited. Posted invoices retain their history.')
    data=frappe._dict(frappe.parse_json(values) or {})
    currency=data.get('currency') or doc.currency
    linked('Currency',currency)
    from plus_point.events import positive
    base=frappe.db.get_value('Company',doc.company,'default_currency')
    rate=Decimal(1) if currency==base else positive(data.get('exchange_rate') or doc.conversion_rate,'Exchange rate')
    old_rate=Decimal(str(doc.conversion_rate))
    if currency!=doc.currency or rate!=old_rate:
        from plus_point.billing import receivable_account
        doc.debit_to=receivable_account(doc.company,currency)
        doc.currency=currency;doc.conversion_rate=float(rate)
        for row in doc.items:
            if row.get('pp_source_name'):
                source=linked(row.pp_source_type,row.pp_source_name)
                amount=source.amount if row.pp_source_type=='PP Milestone' else source.billable_amount
                row.rate=float(money(Decimal(str(amount))/rate))
            else:row.rate=float(money(Decimal(str(row.rate))*old_rate/rate))
    if data.get('due_date'):doc.due_date=data.due_date
    if 'remarks' in data:doc.remarks=data.remarks
    items={r.name:r for r in doc.items}
    for row in data.get('items',[]):
        if row.get('name') not in items:frappe.throw('Reload the invoice before editing its items.')
        item=items[row['name']]
        if 'description' in row:item.description=row['description']
        if not item.get('pp_source_name'):
            if 'rate' in row:
                from plus_point.events import positive
                positive(row['rate'],'Rate');item.rate=row['rate']
    doc.save();return dict(name=doc.name)


@frappe.whitelist()
def invoice(name):
    business=company();doc=linked('Sales Invoice',name);linked('Project',doc.project,business.name)
    return dict(name=doc.name,docstatus=doc.docstatus,due_date=doc.due_date,remarks=doc.remarks,currency=doc.currency,exchange_rate=doc.conversion_rate,
        items=[dict(name=r.name,description=r.description,rate=r.rate,qty=r.qty,amount=r.amount,locked=bool(r.get('pp_source_name'))) for r in doc.items])


@frappe.whitelist(methods=['POST'])
def post_invoice(name):
    invoice(name);doc=linked('Sales Invoice',name);doc.submit();return dict(name=doc.name)


@frappe.whitelist()
def email_options(name):
    invoice(name);doc=linked('Sales Invoice',name)
    from plus_point.clients import details
    recipient=details(doc.customer)['email']
    return dict(recipient=recipient,configured=bool(frappe.db.exists('Email Account',{'enable_outgoing':1})))


def invoice_pdf_content(doc):
    doc.check_permission('print')
    from frappe.utils.pdf import get_pdf
    html=frappe.get_print('Sales Invoice',doc.name,print_format='Standard',doc=doc)
    options={}
    # Chromium resolves *.localhost on Windows; wkhtmltopdf inside Linux does not.
    # Rebase this local render only, retaining the tenant Host for public assets.
    # Native private-image inlining and file-access protections remain in force.
    if frappe.local.site.endswith('.localhost'):
        from frappe.utils import scrub_urls,get_url
        html=scrub_urls(html).replace(get_url().rstrip('/'),'http://127.0.0.1:8000')
        options={'custom-header':[('Host',frappe.local.site+':8000')],'custom-header-propagation':None}
    return get_pdf(html,options=options)


@frappe.whitelist()
def download_invoice(name):
    invoice(name);doc=linked('Sales Invoice',name)
    content=invoice_pdf_content(doc)
    frappe.local.response.update(filename=re.sub(r'[^A-Za-z0-9_.-]','_',name)+'.pdf',filecontent=content,type='pdf',http_status_code=200)
    from frappe.utils.response import build_response
    response=build_response('pdf')
    response.headers.set('Content-Disposition','attachment',filename=frappe.local.response.filename)
    return response


@frappe.whitelist(methods=['POST'])
def email_invoice(name,recipient,subject,body):
    options=email_options(name)
    if not options['configured']:frappe.throw('Connect an outgoing email account before sending invoices.')
    recipient=frappe.utils.validate_email_address(recipient,throw=True)
    if not recipient:frappe.throw('Enter the client email address.')
    if not str(subject or '').strip() or len(subject)>140:frappe.throw('Enter an email subject of up to 140 characters.')
    doc=linked('Sales Invoice',name);doc.check_permission('read')
    frappe.sendmail(recipients=[recipient],subject=subject,message=frappe.utils.escape_html(body or '').replace('\n','<br>'),
        attachments=[dict(fname=re.sub(r'[^A-Za-z0-9_.-]','_',name)+'.pdf',fcontent=invoice_pdf_content(doc))],
        reference_doctype='Sales Invoice',reference_name=name)
    return dict(queued=True)


@frappe.whitelist(methods=['POST'])
def set_photo(employee,file_url=None):
    business=company();worker=linked('Employee',employee,business.name);worker.check_permission('write')
    if file_url:
        files=frappe.get_list('File',filters={'file_url':file_url,'attached_to_doctype':'Employee','attached_to_name':employee},fields=['name','file_name'],limit_page_length=1)
        if not files or files[0].file_name.rsplit('.',1)[-1].lower() not in ('png','jpg','jpeg','webp','gif'):frappe.throw('Upload a PNG, JPG, WebP or GIF attached to this worker profile.')
    worker.image=file_url or '';worker.save();return dict(image=worker.image)


@frappe.whitelist()
def worker_states():
    business=company();day=getdate(today());result={}
    projects=frappe.get_list('Project',filters={'company':business.name,'status':'Open'},pluck='name',limit_page_length=0)
    for row in frappe.get_list('PP Assignment',filters={'project':['in',projects or ['']]},fields=['employee','start_date','end_date'],limit_page_length=0):
        if row.end_date and getdate(row.end_date)<day:continue
        state='Assigned' if getdate(row.start_date)<=day else 'Scheduled'
        if result.get(row.employee)!='Assigned':result[row.employee]=state
    return result


@frappe.whitelist(methods=['POST'])
def create_category(title):
    company();title=str(title or '').strip()
    if not title or len(title)>100:frappe.throw('Enter a worker category of up to 100 characters.')
    if not frappe.db.exists('Designation',title):frappe.get_doc(dict(doctype='Designation',designation_name=title)).insert()
    frappe.defaults.set_global_default('pp_event_roles',json.dumps(sorted(set(event_roles())|{title})))
    return dict(name=title)


def activity_doc(doctype,name):
    if doctype=='PP Contract Terms':return terms_doc(name)
    if doctype=='PP Event Plan':
        doc=linked(doctype,name);terms_doc(doc.contract_terms);return doc
    frappe.throw('Choose an agreement or event for comments.')


@frappe.whitelist()
def activity(doctype,name):
    doc=activity_doc(doctype,name)
    return dict(comments=frappe.get_list('Comment',filters={'reference_doctype':doctype,'reference_name':name,'comment_type':'Comment'},fields=['name','content','comment_by','creation'],order_by='creation desc',limit_page_length=50),
        versions=frappe.get_list('Version',filters={'ref_doctype':doctype,'docname':name},fields=['name','owner','creation'],order_by='creation desc',limit_page_length=20),
        created=doc.creation,modified=doc.modified,owner=doc.owner,modified_by=doc.modified_by)


@frappe.whitelist(methods=['POST'])
def add_comment(doctype,name,content):
    doc=activity_doc(doctype,name);doc.check_permission('write')
    text=str(content or '').strip()
    if not text or len(text)>5000:frappe.throw('Write a comment of up to 5,000 characters.')
    doc.add_comment('Comment','<p>'+frappe.utils.escape_html(text).replace('\n','<br>')+'</p>')
    return dict(saved=True)
