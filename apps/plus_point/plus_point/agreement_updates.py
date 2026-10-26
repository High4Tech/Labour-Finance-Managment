"""Proposed updates use the existing immutable signing request and approval link."""
import secrets
import frappe
from frappe.utils import now_datetime,add_to_date


def guard(terms):
    if frappe.flags.get('pp_agreement_revision') or terms.status=='Draft' or terms.get('event_basis'):return
    if frappe.db.exists('PP Agreement Share',{'contract_terms':terms.name}) or frappe.db.get_value('Contract',terms.contract,'is_signed'):
        frappe.throw('Propose an agreement update. The current agreement stays unchanged until client approval or recorded company attestation.')


def protect_contract(doc,method=None):
    """Native Contract edits must not bypass the agreement approval boundary."""
    old=doc.get_doc_before_save()
    if not old or frappe.flags.get('pp_agreement_revision'):return
    from frappe.utils import getdate
    def value(record,key):
        result=record.get(key)
        return getdate(result) if key in ('start_date','end_date') and result else result
    if not any(value(doc,k)!=value(old,k) for k in ('contract_terms','start_date','end_date','party_name','party_type')):return
    root=frappe.db.get_value('PP Contract Terms',{'contract':doc.name,'event_basis':0},'name')
    if root:guard(frappe.get_doc('PP Contract Terms',root))


@frappe.whitelist(methods=['POST'])
def propose(name,values,summary,method='Client signature',recipient='',cc=''):
    from plus_point.operations import terms_doc,save_agreement
    from plus_point.signing import operation,snapshot,digest,send_link
    from plus_point.agreement_documents import recipients
    from plus_point.benefits import atomic
    @atomic
    def save():
        terms=terms_doc(name,True)
        if terms.get('event_basis'):frappe.throw('Edit event commercial terms from the event.')
        if method not in ('Client signature','Company attested'):frappe.throw('Choose client approval or recorded company attestation.')
        if not str(summary or '').strip() or len(summary)>1000:frappe.throw('Describe this update in 1,000 characters or less.')
        if method=='Client signature':
            recipients(recipient,cc)
            if not frappe.db.exists('Email Account',{'enable_outgoing':1}):frappe.throw('Configure outgoing email, or record the client’s agreement using company attestation.')
        proposed=frappe.parse_json(values) or {}
        allowed={'agreement_title','effective_start','effective_end','validity_mode','resource_mode','rate_card','recurrence_note','scope','billing_model','fixed_amount','agreement_currency','pp_agreement_currency','pp_conditions','staffing','sites','site_details','transport_requirements','pp_daily_checkpoints','auto_invoice','confirm_over_budget','allow_past_dates','client','customer'}
        if not isinstance(proposed,dict) or set(proposed)-allowed:frappe.throw('Choose valid agreement changes.')
        frappe.db.get_value('PP Contract Terms',name,'name',for_update=True);terms.reload();base=str(terms.modified)
        frappe.db.savepoint('pp_update_preview');previous=frappe.flags.get('pp_agreement_revision');frappe.flags.pp_agreement_revision=True
        try:
            save_agreement(proposed,name);html=snapshot(name)
        finally:
            frappe.db.rollback(save_point='pp_update_preview');frappe.flags.pp_agreement_revision=previous
        token=secrets.token_urlsafe(40)
        with operation():
            share=frappe.get_doc(dict(doctype='PP Agreement Share',contract_terms=name,token_hash=digest(token),
                expires=add_to_date(now_datetime(),days=7),status='Pending',snapshot=html,digest=digest(html),
                proposed_values=frappe.as_json(proposed),base_modified=base,approval_method=method,change_summary=summary)).insert()
        url=frappe.utils.get_url('/agree?token='+token)
        if method=='Company attested':
            apply(share)
            with operation():
                share.status='Signed';share.signed_by=frappe.session.user;share.signed_on=now_datetime();share.save()
        else:send_link(name,share.name,token,recipient,cc=cc)
        terms.add_comment('Comment',frappe.utils.escape_html(f'Agreement update: {summary}. '+('Company recorded that the client agreed; not a client signature.' if method=='Company attested' else 'Pending client approval. Current terms unchanged.')))
        return dict(name=share.name,status=share.status,url=url,method=method)
    return save()


def apply(share):
    if not share.get('proposed_values'):return
    from plus_point.operations import terms_doc,save_agreement
    user=frappe.session.user;previous=frappe.flags.get('pp_agreement_revision')
    try:
        # Token grants this stored proposal only. Recheck its original author's permissions.
        frappe.set_user(share.owner)
        if not frappe.db.get_value('User',share.owner,'enabled'):frappe.throw('The update author is disabled. Ask the company to issue a new update.')
        terms=terms_doc(share.contract_terms,True);frappe.db.get_value('PP Contract Terms',terms.name,'name',for_update=True);terms.reload()
        if str(terms.modified)!=str(share.base_modified):frappe.throw('The agreement changed after this proposal. Ask the company to send a fresh update.')
        frappe.flags.pp_agreement_revision=True
        save_agreement(frappe.parse_json(share.proposed_values),terms.name)
        from plus_point.signing import operation
        with operation():
            for name in frappe.get_list('PP Agreement Share',filters={'contract_terms':terms.name,'status':'Pending','name':['!=',share.name]},pluck='name',limit_page_length=100):
                old=frappe.get_doc('PP Agreement Share',name);old.status='Revoked';old.save()
    finally:
        frappe.flags.pp_agreement_revision=previous;frappe.set_user(user)
