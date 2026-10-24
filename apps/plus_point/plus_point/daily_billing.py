"""Daily billing checkpoints group approved attendance; they never recognize revenue."""
import uuid
import frappe
from frappe.utils import getdate,today
from plus_point.finance import money


def validate(terms):
    rows=frappe.parse_json(terms.get('pp_daily_checkpoints') or '[]')
    if not isinstance(rows,list) or len(rows)>60:frappe.throw('Use at most 60 daily billing checkpoints.')
    old=terms.get_doc_before_save();previous={r['id']:r for r in frappe.parse_json(old.get('pp_daily_checkpoints') or '[]')} if old else {}
    if terms.billing_model!='Daily' and rows:frappe.throw('Daily billing checkpoints require Daily pricing.')
    seen=set();periods=[]
    for row in rows:
        if not isinstance(row,dict):frappe.throw('Choose valid daily billing checkpoints.')
        row['id']=row.get('id') or str(uuid.uuid4())
        if row['id'] in seen:frappe.throw('Each billing checkpoint must be unique.')
        seen.add(row['id']);before=previous.get(row['id'],{})
        if row.get('invoice')!=before.get('invoice'):frappe.throw('Invoice references are managed by billing.')
        if before.get('invoice') and row!=before:frappe.throw('An invoiced checkpoint cannot be changed.')
        if not str(row.get('title') or '').strip() or len(str(row['title']))>140:frappe.throw('Name each billing checkpoint in 140 characters or less.')
        if row.get('frequency') not in ('Daily','Weekly','Monthly','Custom'):frappe.throw('Choose Daily, Weekly, Monthly or Custom billing.')
        start=getdate(row.get('from_date'));end=getdate(row.get('to_date'))
        if not row.get('from_date') or not row.get('to_date') or start>end:frappe.throw('Choose a valid attendance period for each billing checkpoint.')
        if start<getdate(terms.effective_start) or end>getdate(terms.effective_end):frappe.throw('Billing periods must be within the agreement dates.')
        if not row.get('due_date') or getdate(row['due_date'])<end:frappe.throw('Payment due must be on or after the attendance period ends.')
        if any(a<=end and b>=start for a,b in periods):frappe.throw('Daily billing periods cannot overlap. Edit the existing checkpoint instead.')
        periods.append((start,end))
    if any(r.get('invoice') and key not in seen for key,r in previous.items()):frappe.throw('Keep invoiced daily billing checkpoints for financial history.')
    terms.pp_daily_checkpoints=frappe.as_json(rows)


@frappe.whitelist()
def overview(agreement):
    from plus_point.operations import terms_doc
    terms=terms_doc(agreement);rate=float(terms.get('pp_agreement_rate') or 1);result=[]
    for row in frappe.parse_json(terms.get('pp_daily_checkpoints') or '[]'):
        work=frappe.get_list('PP Work Entry',filters={'contract_terms':terms.name,'status':'Approved','work_date':['between',[row['from_date'],row['to_date']]],'sales_invoice':['is','not set']},fields=['name','billable_amount'],limit_page_length=0)
        result.append(dict(row,amount=float(sum((money(r.billable_amount) for r in work),money(0)))/rate,
            sources=len(work),status='Invoiced' if row.get('invoice') else 'Ready to invoice' if work and row['to_date']<=today() else 'Planned'))
    return result


@frappe.whitelist(methods=['POST'])
def invoice(agreement,checkpoint):
    from plus_point.operations import terms_doc
    from plus_point.billing import create_invoice
    terms=terms_doc(agreement,True);frappe.db.get_value('PP Contract Terms',agreement,'name',for_update=True)
    rows=frappe.parse_json(terms.get('pp_daily_checkpoints') or '[]');row=next((r for r in rows if r['id']==checkpoint),None)
    if not row:frappe.throw('Reopen the agreement to select its billing checkpoint.')
    if row.get('invoice'):return dict(name=row['invoice'],existing=True)
    if row['to_date']>today():frappe.throw('Wait until this attendance period ends before generating its invoice.')
    result=create_invoice(agreement,from_date=row['from_date'],to_date=row['to_date'])
    row['invoice']=result['name']
    # The reference is derived from the locked invoice action, never accepted from the browser.
    frappe.db.set_value('PP Contract Terms',agreement,'pp_daily_checkpoints',frappe.as_json(rows))
    return result
