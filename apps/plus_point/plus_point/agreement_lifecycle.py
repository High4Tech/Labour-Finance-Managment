"""Date-driven agreement lifecycle. Closure never cancels financial history."""
import frappe
from frappe.utils import getdate,today


def apply_status(doc):
    if doc.status!='Draft' and doc.effective_end:
        doc.status='Closed' if getdate(doc.effective_end)<getdate(today()) else 'Active'


def close_expired():
    # A bounded hourly batch; agreements ending today stay active through today.
    names=frappe.get_all('PP Contract Terms',filters={'status':'Active','effective_end':['<',today()]},pluck='name',limit_page_length=200,order_by='effective_end,name')
    for name in names:
        frappe.db.sql("update `tabPP Contract Terms` set status='Closed' where name=%s and status='Active' and effective_end<%s",(name,today()))
    return len(names)
