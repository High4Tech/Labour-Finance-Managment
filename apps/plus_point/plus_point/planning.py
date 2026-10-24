"""Reusable client site plans and explicit, event-specific worker pay."""
from decimal import Decimal
import frappe
from frappe.utils import getdate, add_days, cint
from plus_point.finance import money
from plus_point.setup_flow import linked


def install():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({
        'Employee': [dict(fieldname='pp_daily_rate', label='Daily pay rate', fieldtype='Currency'),
                     dict(fieldname='pp_monthly_rate', label='Monthly pay rate', fieldtype='Currency')],
        'PP Assignment': [dict(fieldname='pp_pay_basis', label='Event pay basis', fieldtype='Select', options='\nDaily\nMonthly'),
                          dict(fieldname='pp_pay_amount', label='Event pay amount', fieldtype='Currency'),
                          dict(fieldname='pp_cost_override', label='Confirmed pay above client price', fieldtype='Check', no_copy=1)]})
    frappe.reload_doc('plus_point','doctype','pp_agreement_staffing')
    frappe.reload_doc('plus_point','doctype','pp_event_plan')
    if not frappe.defaults.get_global_default('pp_separate_pay_rates_installed'):
        for worker in frappe.get_all('Employee',fields=['name','pp_salary_basis','pp_salary_amount','pp_daily_rate','pp_monthly_rate']):
            field='pp_monthly_rate' if worker.pp_salary_basis=='Monthly' else 'pp_daily_rate'
            if worker.pp_salary_amount and not worker.get(field):frappe.db.set_value('Employee',worker.name,field,worker.pp_salary_amount,update_modified=False)
        frappe.defaults.set_global_default('pp_separate_pay_rates_installed',1)


def worker_rates(worker):
    legacy=money(worker.get('pp_salary_amount') or 0)
    daily=worker.get('pp_daily_rate');monthly=worker.get('pp_monthly_rate')
    return dict(daily=str(money(daily if daily is not None else legacy if worker.get('pp_salary_basis')!='Monthly' else 0)),
                monthly=str(money(monthly if monthly is not None else legacy if worker.get('pp_salary_basis')=='Monthly' else 0)))


@frappe.whitelist()
def recent_sites(customer, exclude=None):
    from plus_point.operations import company
    business=company();linked('Customer',customer)
    projects=frappe.get_list('Project',filters={'company':business.name,'customer':customer,'pp_archived':0},pluck='name',limit_page_length=0)
    terms=frappe.get_list('PP Contract Terms',filters={'project':['in',projects or ['']],'name':['!=',exclude or '']},
        fields=['name','project','agreement_title','modified','pp_agreement_currency','currency'],order_by='modified desc,name desc',limit_page_length=40)
    result=[]
    for record in terms:
        linked('PP Contract Terms',record.name)
        sites=frappe.get_list('PP Site',filters={'project':record.project,'is_active':1},fields=['name','site_name'],order_by='site_name,name',limit_page_length=12)
        for site in sites:
            if frappe.db.exists('PP Agreement Staffing',{'parent':record.name,'site':site.name}):
                result.append(dict(agreement=record.name,title=record.agreement_title,site=site.name,site_name=site.site_name,
                    modified=str(record.modified),currency=record.pp_agreement_currency or record.currency))
            if len(result)>=20:return result
    return result


@frappe.whitelist()
def copy_site(customer, agreement, site, start_date, end_date, currency, exclude=None):
    from plus_point.operations import company,terms_doc
    from plus_point.events import span
    business=company();source=terms_doc(agreement);project=linked('Project',source.project,business.name)
    linked('Customer',customer)
    if project.customer!=customer or agreement==exclude:frappe.throw('Choose a previous site belonging to this client.')
    venue=linked('PP Site',site)
    if venue.project!=source.project or not venue.is_active:frappe.throw('Choose an active site in the source agreement.')
    span(start_date,end_date)
    rows=[r for r in source.staffing if r.site==site]
    vehicles=[r for r in frappe.parse_json(source.get('pp_transport_requirements') or '[]') if not r.get('site_name') or r.get('site_name')==venue.site_name]
    if not rows and not vehicles:frappe.throw('This site has no crew or vehicle requirements to copy.')
    from plus_point.workflows import rate_values
    rate=Decimal(str(rate_values(business,dict(agreement_currency=currency),terms_doc(exclude) if exclude else None).pp_agreement_rate))
    copied=[]
    for row in rows:
        copied.append(dict(site_name=venue.site_name,designation=row.designation,phase=row.phase,
            start_date=str(getdate(start_date)),end_date=str(getdate(end_date)),workers_required=row.workers_required,wage_rate=0,
            client_rate=float(money(Decimal(str(row.client_rate or 0))/rate))))
    transport=[dict(vehicle_type=r['vehicle_type'],quantity=r['quantity'],site_name=venue.site_name,
                    start_date=str(getdate(start_date)),end_date=str(getdate(end_date)),notes=r.get('notes') or '') for r in vehicles]
    return dict(site_name=venue.site_name,rows=copied,transport_requirements=transport,source_currency=source.get('pp_agreement_currency') or source.currency)


def pay_values(worker, basis=None, amount=None, fallback=0):
    from plus_point.events import positive
    rates=worker_rates(worker);basis=basis or 'Daily'
    if basis not in ('Daily','Monthly'):frappe.throw('Choose Daily or Monthly pay for this event.')
    if amount in (None,''):
        amount=rates['monthly' if basis=='Monthly' else 'daily']
        if not money(amount) and basis=='Daily':amount=fallback
    amount=money(positive(amount,f'{worker.employee_name}: {basis.lower()} pay'))
    return dict(pp_pay_basis=basis,pp_pay_amount=float(amount),wage_rate=float(money(amount/30) if basis=='Monthly' else amount))


def cost_warning(terms, proposals, exclude=None):
    """Projection only; attendance remains the source of actual labour cost."""
    if terms.billing_model=='Daily':
        if any(money(r['wage_rate'])>money(r['client_rate']) for r in proposals):
            return 'Worker daily pay exceeds the client rate. This work can make a loss. Confirm to continue with these rates.'
        return ''
    rows=frappe.db.sql('''SELECT name,start_date,end_date,wage_rate FROM `tabPP Assignment`
        WHERE contract_terms=%s ORDER BY name FOR UPDATE''',terms.name,as_dict=True)
    rows=[r for r in rows if r.name!=exclude]+proposals
    total=sum((Decimal((getdate(r.get('end_date') or terms.effective_end or r['start_date'])-getdate(r['start_date'])).days+1)*money(r['wage_rate']) for r in rows),Decimal(0))
    if money(total)>money(terms.fixed_amount):
        rate=Decimal(str(terms.get('pp_agreement_rate') or 1));currency=terms.get('pp_agreement_currency') or terms.currency
        return f'Projected labour cost {money(total/rate)} {currency} exceeds the fixed client price {money(Decimal(str(terms.fixed_amount))/rate)} {currency}. Confirm to continue. Actual cost follows approved attendance.'
    return ''


def validate_assignment(doc, terms):
    from plus_point.budget import lock_project
    lock_project(doc.project)
    old=doc.get_doc_before_save()
    pay_keys=('pp_pay_basis','pp_pay_amount')
    if old and frappe.db.exists('PP Work Entry',{'assignment':doc.name}) and any(old.get(k)!=doc.get(k) for k in pay_keys):
        frappe.throw('Recorded attendance locks this worker’s pay basis and amount. Create a new dated assignment to change pay.')
    if doc.get('pp_pay_basis'):
        amount=money(doc.get('pp_pay_amount') or 0)
        if amount<=0:frappe.throw('Enter a positive event pay amount.')
        expected=money(amount/30) if doc.pp_pay_basis=='Monthly' else amount
        if doc.pp_pay_basis not in ('Daily','Monthly') or money(doc.wage_rate)!=expected:
            frappe.throw('Event daily wage must match the selected daily amount or monthly amount divided by 30.')
    changed=not old or any(str(old.get(k) or '')!=str(doc.get(k) or '') for k in ('wage_rate','client_rate','start_date','end_date',*pay_keys))
    # Closing a deployment never adds cost and must remain available for transfers.
    closing=old and money(doc.wage_rate)==money(old.wage_rate) and doc.end_date and (not old.end_date or getdate(doc.end_date)<=getdate(old.end_date)) and all(doc.get(k)==old.get(k) for k in ('start_date','client_rate',*pay_keys))
    if changed and not closing:
        warning=cost_warning(terms,[doc.as_dict()],doc.name)
        if warning and not cint(doc.get('pp_cost_override')):frappe.throw(warning+' Review and confirm pay above client price first.')


@frappe.whitelist()
def pay_preview(name, requirement, employees, payments=None):
    from plus_point.events import plan_doc
    from plus_point.operations import terms_doc
    from plus_point.crew import selection
    event=plan_doc(name);terms=terms_doc(event.contract_terms)
    from plus_point.budget import lock_project
    lock_project(event.project)
    row=next((r for r in event.staffing if r.name==requirement),None)
    if not row:frappe.throw('Reload the event crew category.')
    payments=frappe.parse_json(payments) or {};proposals=[]
    for employee in selection(frappe.parse_json(employees)):
        worker=linked('Employee',employee,event.company);v=payments.get(employee,{})
        pay=pay_values(worker,v.get('basis'),v.get('amount'),row.wage_rate or event.wage_rate)
        proposals.append(dict(employee=employee,start_date=str(row.start_date),end_date=str(row.end_date),client_rate=row.client_rate or event.client_rate,**pay))
    return dict(warning=cost_warning(terms,proposals),rows=proposals,currency=terms.currency)


@frappe.whitelist(methods=['POST'])
def save_pay(assignment, basis, amount, confirm_over_budget=0):
    from plus_point.operations import terms_doc
    doc=linked('PP Assignment',assignment);doc.check_permission('write');terms_doc(doc.contract_terms,True)
    if frappe.db.exists('PP Work Entry',{'assignment':assignment}):frappe.throw('Attendance already exists. Create a new dated assignment to change this worker’s pay.')
    worker=linked('Employee',doc.employee,doc.company if doc.get('company') else linked('Project',doc.project).company)
    doc.update(pay_values(worker,basis,amount));doc.pp_cost_override=cint(confirm_over_budget);doc.save()
    return dict(name=doc.name)


def ensure_unused_event(event):
    """Detaching must not orphan payroll, accounting or resource history."""
    for dt in ('PP Assignment','PP Work Entry','PP Daily Register','PP Vehicle Booking','PP Equipment Booking','Sales Invoice','Purchase Invoice','Payment Entry','PP Wage Settlement'):
        if frappe.db.exists(dt,{'project':event.project}):
            frappe.throw('This event has worker assignments, attendance, reservations or financial records. Keep its original agreement to preserve history. Remove unused dependencies first, or close the agreement for completed work.')


@frappe.whitelist()
def event_agreements(plan):
    from plus_point.events import plan_doc
    from plus_point.operations import catalogue
    event=plan_doc(plan);project=linked('Project',event.project)
    return dict(current=event.contract_terms,rows=[r for r in catalogue()['agreements'] if r.customer==project.customer and r.status=='Active' and
        not frappe.db.exists('PP Event Plan',{'project':r.project,'name':['!=',event.name]})])


@frappe.whitelist(methods=['POST'])
def change_event_agreement(plan,contract_terms=None):
    from plus_point.events import plan_doc
    from plus_point.operations import terms_doc
    from plus_point.benefits import atomic
    from plus_point.budget import lock_project
    event=plan_doc(plan,True)
    terms=terms_doc(contract_terms) if contract_terms else None
    for project in sorted({event.project}|({terms.project} if terms else set())):lock_project(project)
    event.reload();ensure_unused_event(event)
    @atomic
    def save():
        if terms:
            old_project=linked('Project',event.project);new_project=linked('Project',terms.project,event.company)
            if old_project.customer!=new_project.customer:frappe.throw('Choose a replacement agreement for the same client.')
            if terms.status!='Active' or not terms.staffing:frappe.throw('Choose an active agreement with a site and crew plan.')
            if frappe.db.exists('PP Event Plan',{'project':terms.project,'name':['!=',event.name]}):frappe.throw('That agreement already has an event. Choose another agreement.')
            event.project=terms.project;event.contract_terms=terms.name
            event.set('staffing',[{k:r.get(k) for k in ('site','designation','phase','start_date','end_date','workers_required','client_rate')} for r in terms.staffing])
            event.start_date=min(getdate(r.start_date) for r in terms.staffing);event.end_date=max(getdate(r.end_date) for r in terms.staffing)
            event.wage_rate=0;event.client_rate=terms.staffing[0].client_rate
        else:event.contract_terms=None
        event.selected_crew='';event.save()
        return dict(name=event.name,unlinked=not bool(event.contract_terms))
    return save()
