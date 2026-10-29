"""One staffing requirement can cover several phases without multiplying headcount."""
import re
import frappe
PHASES=('Setup','Event','Pack-down','Other')
def normalize(value):
    values=value if isinstance(value,list) else re.split(r'[,;|]',str(value or 'Event'))
    aliases={p.casefold():p for p in PHASES};aliases['pack down']='Pack-down'
    chosen=[]
    for raw in values:
        if isinstance(raw,str) and raw.strip().casefold().startswith('other:'):
            description=raw.strip().split(':',1)[1].strip()
            if not description or len(description)>80:frappe.throw('Describe the custom phase in 1 to 80 characters.')
            chosen.append('Other: '+description);continue
        if not isinstance(raw,str) or raw.strip().casefold() not in aliases:frappe.throw('Choose Setup, Event or Pack-down, or describe a custom phase.')
        chosen.append(aliases[raw.strip().casefold()])
    if not chosen:frappe.throw('Choose at least one crew phase.')
    return ', '.join([p for p in PHASES if p in chosen]+list(dict.fromkeys(p for p in chosen if p.startswith('Other:'))))
