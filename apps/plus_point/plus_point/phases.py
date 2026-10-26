"""One staffing requirement can cover several phases without multiplying headcount."""
import re
import frappe
PHASES=('Setup','Event','Pack-down','Other')
def normalize(value):
    values=value if isinstance(value,list) else re.split(r'[,;|]',str(value or 'Event'))
    aliases={p.casefold():p for p in PHASES};aliases['pack down']='Pack-down'
    chosen=[]
    for raw in values:
        if not isinstance(raw,str) or raw.strip().casefold() not in aliases:frappe.throw('Choose Setup, Event, Pack-down or Other. Select every phase this crew will cover.')
        chosen.append(aliases[raw.strip().casefold()])
    if not chosen:frappe.throw('Choose at least one crew phase.')
    return ', '.join(p for p in PHASES if p in chosen)
