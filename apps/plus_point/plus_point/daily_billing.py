"""Daily billing checkpoints group approved attendance; they never recognize revenue."""
import uuid
import frappe
from frappe.utils import getdate,today,add_days,add_months,cint
from plus_point.finance import money

FREQUENCIES=('Daily','Weekly','Biweekly','Monthly','Quarterly','Completion')


@frappe.whitelist()
def periods(start,end,frequency='Weekly',payment_days=0,schedule_id=None):
    """Derive bounded, contiguous billing periods from the agreement, not a second calendar."""
    if frequency not in FREQUENCIES:frappe.throw('Choose daily, weekly, biweekly, monthly, quarterly or completion payments.')
    if not start or not end or getdate(start)>getdate(end):frappe.throw('Choose valid agreement dates before setting payments.')
    if schedule_id is not None and (not isinstance(schedule_id,str) or len(schedule_id)>80):frappe.throw('Choose a valid payment schedule reference.')
    if str(payment_days or 0) != str(cint(payment_days or 0)) or not 0<=cint(payment_days)<=90:frappe.throw('Payment terms must be a whole number from 0 to 90 days.')
    first=getdate(start);last=getdate(end);cursor=first;result=[];key=schedule_id or str(uuid.uuid4())
    while cursor<=last:
        if len(result)>=400:frappe.throw('Use a longer payment frequency. An agreement supports up to 400 billing periods.')
        index=len(result)+1
        following=getdate(add_days(last,1)) if frequency=='Completion' else getdate(add_months(first,index*(3 if frequency=='Quarterly' else 1))) if frequency in ('Monthly','Quarterly') else getdate(add_days(first,index*({'Daily':1,'Weekly':7,'Biweekly':14}[frequency])))
        through=min(last,getdate(add_days(following,-1)))
        result.append(dict(id=key+':'+str(cursor),schedule_id=key,title='Pay after completion' if frequency=='Completion' else frequency+' payment '+str(index),frequency=frequency,
            from_date=str(cursor),to_date=str(through),due_date=str(add_days(through,cint(payment_days))),payment_days=cint(payment_days),automatic=1))
        cursor=following
    return result


def validate(terms):
    rows=frappe.parse_json(terms.get('pp_daily_checkpoints') or '[]')
    if not isinstance(rows,list) or len(rows)>400:frappe.throw('Use at most 400 daily billing periods.')
    old=terms.get_doc_before_save();previous={r['id']:r for r in frappe.parse_json(old.get('pp_daily_checkpoints') or '[]')} if old else {}
    if terms.billing_model!='Daily' and rows:frappe.throw('Daily billing checkpoints require Daily pricing.')
    seen=set();occupied=[];schedules={}
    for row in rows:
        if not isinstance(row,dict):frappe.throw('Choose valid daily billing checkpoints.')
        row['id']=row.get('id') or str(uuid.uuid4())
        if row['id'] in seen:frappe.throw('Each billing checkpoint must be unique.')
        seen.add(row['id']);before=previous.get(row['id'],{})
        if row.get('invoice')!=before.get('invoice'):frappe.throw('Invoice references are managed by billing.')
        if row.get('supplemental_invoices')!=before.get('supplemental_invoices'):frappe.throw('Invoice references are managed by billing.')
        if (before.get('invoice') or before.get('supplemental_invoices')) and row!=before:frappe.throw('An invoiced checkpoint cannot be changed.')
        if not str(row.get('title') or '').strip() or len(str(row['title']))>140:frappe.throw('Name each billing checkpoint in 140 characters or less.')
        if row.get('frequency') not in FREQUENCIES+('Custom',):frappe.throw('Choose a valid payment frequency.')
        if row.get('schedule_id'):
            key=(row['schedule_id'],row['frequency'],row.get('payment_days',0))
            if key not in schedules:schedules[key]={r['id']:r for r in periods(terms.effective_start,terms.effective_end,row['frequency'],row.get('payment_days',0),row['schedule_id'])}
            expected=schedules[key].get(row['id'])
            if not expected or any(row.get(k)!=expected[k] for k in ('from_date','to_date','due_date')):frappe.throw('The payment schedule no longer matches the agreement dates. Set the payment schedule again.')
        start=getdate(row.get('from_date'));end=getdate(row.get('to_date'))
        if not row.get('from_date') or not row.get('to_date') or start>end:frappe.throw('Choose a valid attendance period for each billing checkpoint.')
        if start<getdate(terms.effective_start) or terms.effective_end and end>getdate(terms.effective_end):frappe.throw('Billing periods must be within the agreement dates.')
        if not row.get('due_date') or getdate(row['due_date'])<end:frappe.throw('Payment due must be on or after the attendance period ends.')
        if any(a<=end and b>=start for a,b in occupied):frappe.throw('Daily billing periods cannot overlap. Edit the existing checkpoint instead.')
        occupied.append((start,end))
    if any((r.get('invoice') or r.get('supplemental_invoices')) and key not in seen for key,r in previous.items()):frappe.throw('Keep invoiced daily billing checkpoints for financial history.')
    terms.pp_daily_checkpoints=frappe.as_json(rows)


def rebase(terms):
    rows=frappe.parse_json(terms.get('pp_daily_checkpoints') or '[]')
    if not terms.effective_end:
        if rows:frappe.throw('For an ongoing agreement, define payment schedules on each dated event.')
        return
    recurring=next((r for r in rows if r.get('schedule_id')),None)
    if not recurring:return
    generated=periods(terms.effective_start,terms.effective_end,recurring['frequency'],recurring.get('payment_days',0),recurring['schedule_id'])
    old={r['id']:r for r in rows}
    if any((r.get('invoice') or r.get('supplemental_invoices')) and r['id'] not in {p['id'] for p in generated} for r in rows):frappe.throw('Keep invoiced payment periods within the agreement dates.')
    terms.pp_daily_checkpoints=frappe.as_json([old[r['id']] if old.get(r['id'],{}).get('invoice') or old.get(r['id'],{}).get('supplemental_invoices') else dict(r,title=old.get(r['id'],{}).get('title') or r['title']) for r in generated])


def event_terms(terms):
    return [terms.name]+frappe.get_list('PP Contract Terms',filters={'governing_agreement':terms.name,'event_basis':1},pluck='name',limit_page_length=200)


def create_period_invoice(terms,row,limit=50):
    from plus_point.billing import create_invoice
    result=[]
    for name in event_terms(terms):
        if len(result)>=limit:break
        if not frappe.db.exists('PP Work Entry',{'contract_terms':name,'status':'Approved','sales_invoice':['is','not set'],'billable_amount':['>',0],'work_date':['between',[row['from_date'],row['to_date']]]}):continue
        item=create_invoice(name,from_date=row['from_date'],to_date=row['to_date'])
        invoice=frappe.get_doc('Sales Invoice',item['name']);invoice.posting_date=row['to_date'];invoice.due_date=row['due_date']
        for payment in invoice.get('payment_schedule',[]):payment.due_date=row['due_date']
        invoice.save();result.append(item['name'])
    if not result:frappe.throw('No approved, commercially confirmed unbilled work in this period.')
    return dict(name=result[0],invoices=result,sources=len(result),status='Draft')


@frappe.whitelist()
def overview(agreement):
    from plus_point.operations import terms_doc
    terms=terms_doc(agreement);rate=float(terms.get('pp_agreement_rate') or 1);result=[]
    for row in frappe.parse_json(terms.get('pp_daily_checkpoints') or '[]'):
        work=frappe.get_list('PP Work Entry',filters={'contract_terms':['in',event_terms(terms)],'status':'Approved','work_date':['between',[row['from_date'],row['to_date']]],'sales_invoice':['is','not set']},fields=['name','billable_amount'],limit_page_length=0)
        result.append(dict(row,amount=float(sum((money(r.billable_amount) for r in work),money(0)))/rate,
            sources=len(work),status='Invoiced' if row.get('invoice') else 'Ready to invoice' if work and row['to_date']<=today() else 'Planned'))
    return result


@frappe.whitelist(methods=['POST'])
def invoice(agreement,checkpoint):
    from plus_point.operations import terms_doc
    terms=terms_doc(agreement,True);frappe.db.get_value('PP Contract Terms',agreement,'name',for_update=True)
    rows=frappe.parse_json(terms.get('pp_daily_checkpoints') or '[]');row=next((r for r in rows if r['id']==checkpoint),None)
    if not row:frappe.throw('Reopen the agreement to select its billing checkpoint.')
    if row.get('invoice'):return dict(name=row['invoice'],existing=True)
    if row['to_date']>today():frappe.throw('Wait until this attendance period ends before generating its invoice.')
    result=create_period_invoice(terms,row)
    row['invoice']=result['name']
    if len(result.get('invoices',[]))>1:row['supplemental_invoices']=result['invoices'][1:]
    # The reference is derived from the locked invoice action, never accepted from the browser.
    frappe.db.set_value('PP Contract Terms',agreement,'pp_daily_checkpoints',frappe.as_json(rows))
    return result


def run_recurring():
    """At most 25 agreements and 50 invoice drafts per run; never submit or email."""
    if not frappe.get_meta('PP Contract Terms').has_field('pp_daily_checkpoints'):return
    previous_user=frappe.session.user
    try:
        frappe.set_user('Administrator')
        # Rotate through candidates so a bad agreement cannot starve later ones.
        filters={'billing_model':'Daily','status':['in',['Active','Closed']],'pp_daily_checkpoints':['is','set']}
        cursor=frappe.cache.get_value('pp_recurring_cursor')
        if cursor:filters['name']=['>',cursor]
        candidates=frappe.get_all('PP Contract Terms',filters=filters,fields=['name','project'],order_by='name',limit_page_length=25)
        frappe.cache.set_value('pp_recurring_cursor',candidates[-1].name if candidates else '',expires_in_sec=86400)
        created=0
        for candidate in candidates:
            if frappe.db.get_value('Project',candidate.project,'pp_archived'):continue
            try:
                frappe.db.savepoint('pp_recurring_invoice')
                terms=frappe.get_doc('PP Contract Terms',candidate.name,for_update=True)
                rows=frappe.parse_json(terms.pp_daily_checkpoints or '[]');changed=False
                if not any(r.get('automatic') for r in rows):continue
                pending_dates={str(r.work_date) for r in frappe.get_all('PP Work Entry',filters={'contract_terms':['in',event_terms(terms)],'status':'Approved','billable_amount':['>',0],'sales_invoice':['is','not set']},fields=['work_date'],group_by='work_date',order_by='work_date',limit_page_length=1000)}
                for row in rows:
                    if created>=50:break
                    if not row.get('automatic') or row.get('to_date','9999')>=today():continue
                    if not any(row['from_date']<=date<=row['to_date'] for date in pending_dates):continue
                    result=create_period_invoice(terms,row,limit=50-created)
                    if row.get('invoice'):row.setdefault('supplemental_invoices',[]).append(result['name'])
                    else:row['invoice']=result['name']
                    row.setdefault('supplemental_invoices',[]).extend(result.get('invoices',[])[1:])
                    changed=True;created+=len(result.get('invoices') or [result['name']])
                if changed:frappe.db.set_value('PP Contract Terms',terms.name,'pp_daily_checkpoints',frappe.as_json(rows))
            except Exception:
                frappe.db.rollback(save_point='pp_recurring_invoice');frappe.log_error(title='Recurring attendance invoice',message=frappe.get_traceback())
    finally:frappe.set_user(previous_user)
