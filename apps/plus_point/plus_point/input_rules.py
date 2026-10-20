"""Field-specific input rules shared by forms, native saves and imports."""
import re
import unicodedata
from decimal import Decimal, InvalidOperation
import frappe

PERSON_FIELDS={'first_name','middle_name','last_name','contact_name','person_to_be_contacted'}
PHONE_FIELDS={'phone','cell_number','emergency_phone_number','phone_number','mobile_no'}
CODE_FIELDS={'employee_number','passport_number','license_plate'}
PERSON_PUNCTUATION=" .'-’ʼ"


def person(value):
    return all(unicodedata.category(c)[0] in ('L','M') or c in PERSON_PUNCTUATION for c in value) and any(c.isalpha() for c in value)


def check(fieldname,value,fieldtype=None,label=None):
    if value in (None,''):return
    text=str(value);label=label or fieldname.replace('_',' ').capitalize()
    if fieldname in PERSON_FIELDS and not person(text):
        frappe.throw(f'{label}: use letters, spaces, apostrophes, hyphens or periods; no numbers or other symbols.')
    if fieldname in PHONE_FIELDS and (not re.fullmatch(r'\+?[0-9 ()-]{3,40}',text) or not any(c.isdigit() for c in text)):
        frappe.throw(f'{label}: use digits and optional +, spaces, parentheses or hyphens (up to 40 characters).')
    if fieldname in CODE_FIELDS and any(not(c.isalnum() or c in ' ./_-') for c in text):
        frappe.throw(f'{label}: use letters, numbers, spaces, periods, slashes, underscores or hyphens.')
    if fieldtype in ('Int','Float','Currency','Percent'):
        try:
            number=Decimal(text)
            valid=number.is_finite() and (fieldtype!='Int' or number==number.to_integral_value())
        except (InvalidOperation,ValueError):valid=False
        if not valid:frappe.throw(f'{label}: enter a finite {"whole " if fieldtype=="Int" else ""}number.')


SUPPORTED={'Employee','Customer','Contact','Address','Vehicle','Item','Warehouse','Project','Contract',
    'PP Site','PP Assignment','PP Contract Terms','PP Event Plan','PP Work Entry','PP Daily Register',
    'PP Milestone','PP Vehicle Booking','PP Equipment Booking','PP Wage Settlement'}


def validate_document(doc,method=None):
    if doc.doctype not in SUPPORTED or frappe.flags.in_install or frappe.flags.in_migrate:return
    old=doc.get_doc_before_save()
    for row in [doc]+[child for df in doc.meta.get_table_fields() for child in doc.get(df.fieldname,[])]:
        previous=old if row is doc else row.get_doc_before_save()
        for df in row.meta.fields:
            # Keep existing legacy names readable/editable; validate a name/phone
            # when it is newly supplied or changed, never silently rewrite it.
            if previous and df.fieldname in PERSON_FIELDS|PHONE_FIELDS|CODE_FIELDS and previous.get(df.fieldname)==row.get(df.fieldname):continue
            if df.fieldname in PERSON_FIELDS|PHONE_FIELDS|CODE_FIELDS or doc.doctype.startswith('PP ') and df.fieldtype in ('Int','Float','Currency','Percent'):
                check(df.fieldname,row.get(df.fieldname),df.fieldtype,df.label)
