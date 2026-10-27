"""Agreement commitments and event commercial snapshots, using the existing engines.

Legacy terms retain their project and history. New occurrences use an independent
native project and PP Contract Terms snapshot, never a copy of the full fixed value.
"""
import frappe
from frappe.utils import getdate, today
from plus_point.finance import money


def install():
    """Additive, repeatable metadata installation. Does not recreate business rows."""
    for name in ('pp_contract_terms','pp_event_plan','pp_agreement_share'):
        frappe.reload_doc('plus_point','doctype',name)
    frappe.db.sql("UPDATE `tabPP Contract Terms` SET validity_mode=IF(effective_end IS NULL,'Ongoing','Fixed period') WHERE IFNULL(validity_mode,'')=''")
    frappe.db.sql("UPDATE `tabPP Event Plan` SET planning_state='Ready' WHERE IFNULL(planning_state,'')=''")
    frappe.db.add_index('PP Contract Terms',['governing_agreement','event_basis'],'pp_agreement_events')
    frappe.clear_cache()


def validate_terms(doc):
    mode=doc.get('validity_mode') or ('Fixed period' if doc.effective_end else 'Ongoing')
    if mode not in ('Fixed period','Ongoing'):frappe.throw('Choose fixed period or ongoing validity.')
    if mode=='Fixed period' and not doc.effective_end:frappe.throw('Enter the end date for a fixed-period agreement.')
    doc.validity_mode=mode
    if mode=='Ongoing':doc.effective_end=None
    if doc.get('resource_mode') not in (None,'','Fixed quantities','Estimated quantities','Minimum quantities','Rate card','Per event'):
        frappe.throw('Choose a valid resource commitment.')
    if not doc.is_new() and not doc.get('event_basis') and doc.billing_model=='Fixed':
        allocated=sum((money(r.fixed_amount) for r in frappe.get_all('PP Contract Terms',filters={'governing_agreement':doc.name,'event_basis':1},fields=['fixed_amount'])),money(0))
        approved=sum((money(r.amount) for r in frappe.get_all('PP Milestone',filters={'contract_terms':doc.name,'status':['in',['Approved','Invoiced']]},fields=['amount'])),money(0))
        if allocated+approved>money(doc.fixed_amount):frappe.throw('Preserve approved payments and amounts already allocated to linked events.')
    rates=frappe.parse_json(doc.get('rate_card') or '[]')
    if not isinstance(rates,list) or len(rates)>100:frappe.throw('Use at most 100 category rates.')
    seen=set()
    for row in rates:
        if not isinstance(row,dict) or row.get('designation') in seen:frappe.throw('Use one negotiated rate for each category.')
        from plus_point.setup_flow import linked
        linked('Designation',row.get('designation'))
        from plus_point.events import positive
        positive(row.get('client_rate'),'Client rate',allow_zero=doc.billing_model=='Fixed')
        seen.add(row['designation'])
    # A formal rate-card agreement has one price per category. Event snapshots
    # deliberately keep their agreed prices when the parent is amended later.
    if not doc.get('event_basis') and doc.get('resource_mode')=='Rate card' and doc.billing_model=='Daily':
        negotiated={r['designation']:money(r['client_rate']) for r in rates}
        for row in doc.get('staffing') or []:
            if row.designation not in negotiated:
                frappe.throw(f'Add {row.designation} to the rate card before adding its crew requirement.')
            if money(row.client_rate)!=negotiated[row.designation] and doc.get_doc_before_save():
                from plus_point.agreement_updates import guard
                guard(doc.get_doc_before_save())
            row.client_rate=negotiated[row.designation]
    if doc.get('event_basis') and doc.get('governing_agreement'):
        from plus_point.operations import terms_doc
        parent=terms_doc(doc.governing_agreement)
        project=frappe.get_doc('Project',doc.project);master=frappe.get_doc('Project',parent.project)
        if parent.get('event_basis') or project.company!=master.company or project.customer!=master.customer:
            frappe.throw('Choose a formal agreement for the same client and company.')


def assert_confirmed(terms):
    if terms.get('event_basis') and terms.billing_model=='Fixed' and money(terms.fixed_amount)<=0:frappe.throw('Set and confirm this event’s fixed-price allocation under Commercial terms before invoicing.')
    if terms.get('event_basis') and terms.get('commercial_status') not in ('Confirmed','Company attested'):
        frappe.throw('Confirm this event’s client pricing and record its confirmation source before invoicing.')


def governing(terms):
    return terms.get('governing_agreement') if terms.get('event_basis') else terms.name


def create_event(agreement=None,event_name=None,start_date=None,end_date=None,customer=None,
                 billing_model='Daily',fixed_amount=0,commercial_status='Pending',commercial_source='',
                 notes='',budget=0,enforce_budget=0,**unused):
    from plus_point.operations import company,terms_doc,service_item
    from plus_point.setup_flow import linked
    from plus_point.events import span
    business=company();parent=terms_doc(agreement) if agreement else None
    if not str(event_name or '').strip():frappe.throw('Enter the event name.')
    if not start_date or not end_date:frappe.throw('Enter the actual event start and end dates.')
    span(start_date,end_date)
    from plus_point.events import positive
    budget=float(positive(budget,'Spending budget',allow_zero=True))
    if parent:
        if parent.get('event_basis') or parent.status!='Active':frappe.throw('Choose an active formal agreement.')
        frappe.db.get_value('PP Contract Terms',parent.name,'name',for_update=True)
        if getdate(start_date)<getdate(parent.effective_start) or parent.effective_end and getdate(end_date)>getdate(parent.effective_end):
            frappe.throw('Choose event dates within the agreement validity.')
        customer=frappe.db.get_value('Project',parent.project,'customer');billing_model=parent.billing_model
    else:linked('Customer',customer)
    if billing_model not in ('Daily','Fixed'):frappe.throw('Choose daily or fixed client pricing.')
    if commercial_status not in ('Pending','Confirmed','Company attested'):frappe.throw('Choose a valid commercial confirmation.')
    if not parent and commercial_status!='Pending' and not str(commercial_source or '').strip():
        frappe.throw('Record where the client confirmed these charges.')
    allocation=money(positive(fixed_amount,'Event fixed-price allocation',allow_zero=True)) if billing_model=='Fixed' else money(0)
    if allocation<0:frappe.throw('Event fixed-price allocation cannot be negative.')
    if parent and billing_model=='Fixed':
        children=frappe.get_list('PP Contract Terms',filters={'governing_agreement':parent.name,'event_basis':1},fields=['fixed_amount'],limit_page_length=0)
        # The legacy project may already deliver part/all of the agreement.
        legacy=sum((money(r.amount) for r in frappe.get_list('PP Milestone',filters={'contract_terms':parent.name,'status':['in',['Approved','Invoiced']]},fields=['amount'],limit_page_length=0)),money(0))
        if sum((money(r.fixed_amount) for r in children),legacy)+allocation>money(parent.fixed_amount):
            frappe.throw('Event allocations exceed the agreement fixed value. Reduce this allocation or approve an agreement update.')
    project_title=event_name.strip()
    if frappe.db.exists('Project',{'project_name':project_title}):project_title=project_title[:110]+' · '+str(start_date)+' · '+frappe.generate_hash(length=6)
    project=frappe.get_doc(dict(doctype='Project',project_name=project_title,company=business.name,customer=customer,
        expected_start_date=start_date,expected_end_date=end_date,estimated_costing=budget,
        pp_enforce_spending_budget=frappe.utils.cint(enforce_budget))).insert()
    if parent:contract=parent.contract
    else:
        contract=frappe.get_doc(dict(doctype='Contract',party_type='Customer',party_name=customer,start_date=start_date,
            end_date=end_date,contract_terms='Event commercial confirmation: '+(commercial_source or 'Pending client confirmation'))).insert().name
    terms=frappe.get_doc(dict(doctype='PP Contract Terms',project=project.name,contract=contract,event_basis=1,
        governing_agreement=parent.name if parent else None,agreement_title=event_name.strip(),currency=business.default_currency,
        billing_model=billing_model,fixed_amount=allocation,effective_start=start_date,effective_end=end_date,
        validity_mode='Fixed period',resource_mode='Per event',status='Active',
        commercial_status='Confirmed' if parent else commercial_status,commercial_source=('Inherited from '+parent.name) if parent else commercial_source,
        billing_item=parent.billing_item if parent else service_item(),
        pp_agreement_currency=parent.get('pp_agreement_currency') if parent else business.default_currency,
        pp_agreement_rate=parent.get('pp_agreement_rate') if parent else 1,
        commercial_snapshot=frappe.as_json(dict(agreement=parent.name,modified=str(parent.modified),scope=frappe.db.get_value('Contract',parent.contract,'contract_terms'),conditions=parent.get('pp_conditions'))) if parent else None,
        pp_conditions=parent.get('pp_conditions') if parent else '[]',rate_card=parent.get('rate_card') if parent else '[]')).insert()
    rows=[];sites={}
    for old in parent.staffing if parent else []:
        if not old.workers_required:continue
        if old.site not in sites:
            source=linked('PP Site',old.site)
            sites[old.site]=frappe.get_doc(dict(doctype='PP Site',project=project.name,site_name=source.site_name,is_active=1,
                **{k:source.get(k) for k in ('country','city','address_line1','state','address_line2','postal_code')})).insert().name
        rows.append(dict(site=sites[old.site],designation=old.designation,phase=old.phase,start_date=start_date,end_date=end_date,
            workers_required=old.workers_required,wage_rate=0,client_rate=old.client_rate if billing_model=='Daily' else 0))
    terms.set('staffing',rows)
    # Fixed snapshots with no allocation are legitimate operational plans, but cannot invoice.
    terms.save()
    plan=frappe.get_doc(dict(doctype='PP Event Plan',project=project.name,company=business.name,event_name=event_name.strip(),
        contract_terms=terms.name,start_date=start_date,end_date=end_date,wage_rate=0,
        client_rate=rows[0]['client_rate'] if rows else 0,staffing=rows,notes=notes)).insert()
    return dict(name=plan.name,existing=False,project=project.name,contract_terms=terms.name)


@frappe.whitelist(methods=['POST'])
def create(values):
    from plus_point.benefits import atomic
    data=frappe.parse_json(values) or {}
    allowed=('agreement','event_name','start_date','end_date','customer','billing_model','fixed_amount','commercial_status','commercial_source','notes','budget','enforce_budget')
    return atomic(lambda:create_event(**{k:data[k] for k in allowed if k in data}))()


@frappe.whitelist()
def linked_events(name):
    from plus_point.operations import terms_doc
    terms=terms_doc(name)
    ids=[name]+frappe.get_list('PP Contract Terms',filters={'governing_agreement':name,'event_basis':1},pluck='name',limit_page_length=0)
    rows=frappe.get_list('PP Event Plan',filters={'contract_terms':['in',ids]},fields=['name','pp_reference','event_name','project','start_date','end_date','planning_state'],order_by='start_date desc',limit_page_length=200)
    from plus_point.events import lifecycle
    for row in rows:row.status=lifecycle(row,frappe.db.get_value('Project',row.project,'pp_archived'),frappe.db.get_value('Project',row.project,'status')=='Cancelled')
    return rows


@frappe.whitelist()
def financial_summary(name):
    from plus_point.operations import terms_doc
    from plus_point.api import project_summary
    terms=terms_doc(name);events=linked_events(name);projects={r.project for r in events}
    # Agreement milestones are recognized once on their original project.
    projects.add(terms.project)
    summaries=[project_summary(p) for p in sorted(projects)]
    keys=('earned_revenue','labour_cost','invoiced_net','invoiced_gross','cash_collected_gross','client_outstanding_gross','other_project_costs','operational_profit')
    return dict(contract_value=str(money(terms.fixed_amount)),events=len(events),
        **{key:str(sum((money(row[key]) for row in summaries),money(0))) for key in keys})


@frappe.whitelist(methods=['POST'])
def confirm_event(name,status,source,fixed_amount=None):
    from plus_point.events import plan_doc
    from plus_point.operations import terms_doc
    event=plan_doc(name,True);terms=terms_doc(event.contract_terms,True)
    if not terms.get('event_basis'):frappe.throw('This legacy event retains its original agreement confirmation.')
    if status not in ('Confirmed','Company attested') or not str(source or '').strip():frappe.throw('Choose confirmation and record its source.')
    if terms.billing_model=='Fixed' and money(fixed_amount if fixed_amount is not None else terms.fixed_amount)<=0:frappe.throw('Confirm a positive fixed-price allocation for this event.')
    if fixed_amount is not None and money(fixed_amount)!=money(terms.fixed_amount):
        if frappe.db.exists('PP Milestone',{'contract_terms':terms.name}):frappe.throw('Preserve existing milestones; approve a commercial update instead.')
        if terms.governing_agreement:
            parent=terms_doc(terms.governing_agreement);frappe.db.get_value('PP Contract Terms',parent.name,'name',for_update=True)
            others=frappe.get_list('PP Contract Terms',filters={'governing_agreement':parent.name,'name':['!=',terms.name]},fields=['fixed_amount'],limit_page_length=0)
            legacy=sum((money(r.amount) for r in frappe.get_list('PP Milestone',filters={'contract_terms':parent.name,'status':['in',['Approved','Invoiced']]},fields=['amount'],limit_page_length=0)),money(0))
            if sum((money(r.fixed_amount) for r in others),legacy)+money(fixed_amount)>money(parent.fixed_amount):frappe.throw('Event allocations exceed the agreement fixed value.')
        terms.fixed_amount=fixed_amount
    terms.commercial_status=status;terms.commercial_source=source;terms.status='Active';terms.save()
    terms.add_comment('Comment',frappe.utils.escape_html(f'Commercial terms: {status}. Source: {source}. Recorded by {frappe.session.user}.'))
    return dict(name=terms.name)


def validate_milestone_group(doc,terms):
    if doc.status not in ('Approved','Invoiced'):return
    root=terms.get('governing_agreement') or (None if terms.get('event_basis') else terms.name)
    if not root:return
    frappe.db.get_value('PP Contract Terms',root,'name',for_update=True)
    ids=[root]+frappe.get_all('PP Contract Terms',filters={'governing_agreement':root,'event_basis':1},pluck='name')
    rows=frappe.get_all('PP Milestone',filters={'contract_terms':['in',ids],'status':['in',['Approved','Invoiced']],'name':['!=',doc.name or '']},fields=['amount'])
    total=sum((money(r.amount) for r in rows),money(doc.amount))
    if terms.name==root:
        allocated=sum((money(r.fixed_amount) for r in frappe.get_all('PP Contract Terms',filters={'governing_agreement':root,'event_basis':1},fields=['fixed_amount'])),money(0))
        root_rows=frappe.get_all('PP Milestone',filters={'contract_terms':root,'status':['in',['Approved','Invoiced']],'name':['!=',doc.name or '']},fields=['amount'])
        total=max(total,sum((money(r.amount) for r in root_rows),money(doc.amount))+allocated)
    if total>money(frappe.db.get_value('PP Contract Terms',root,'fixed_amount')):
        frappe.throw('Approved payments across all events exceed the agreement fixed value.')


@frappe.whitelist(methods=['POST'])
def save_schedule(name,rows):
    from plus_point.events import plan_doc
    from plus_point.operations import terms_doc
    event=plan_doc(name,True);terms=terms_doc(event.contract_terms,True)
    if not terms.get('event_basis') or terms.billing_model!='Daily':frappe.throw('Use this control for a daily event commercial snapshot.')
    terms.pp_daily_checkpoints=frappe.as_json(frappe.parse_json(rows) or []);terms.save()
    return dict(name=terms.name)
