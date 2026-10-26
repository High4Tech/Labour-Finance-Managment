"""Native planning lists with scoped, read-only projections of partial drafts.

Drafts retain their own storage: an incomplete form must not become a contract,
project, event or financial record just to appear in its product list.
"""
import re
import frappe
from frappe.utils import cint, flt

TYPES = {'PP Contract Terms': 'Agreement', 'PP Event Plan': 'Event'}
PREFIX = 'draft:'


def field_name(value, doctype):
    value = str(value).replace('`', '')
    alias = re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\s+as\s+([A-Za-z_][A-Za-z0-9_]*)', value, re.I)
    if alias:
        return alias.group(1)
    value = value.removeprefix('tab' + doctype + '.').removeprefix(doctype + '.')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value):
        frappe.throw('Choose a supported list field.')
    return value


def expressions(kind):
    def value(path):
        return "NULLIF(JSON_UNQUOTE(JSON_EXTRACT(d.payload, '$." + path + "')), 'null')"
    fields = {key: 'd.`' + key + '`' for key in ('owner', 'creation', 'modified', 'modified_by')}
    fields.update(name="CONCAT('draft:', d.name)", agreement_title='d.title', event_name='d.title',
                  status="'Draft'", docstatus='0', pp_reference="''", _assign="'[]'", _liked_by="'[]'",
                  _user_tags="''", _comments="'[]'", _comment_count='0', pp_archived='0')
    if kind == 'Agreement':
        fields.update({key: value('details.' + key) for key in ('effective_start', 'effective_end', 'scope')})
        fields.update({key: value('terms.' + key) for key in ('billing_model', 'agreement_currency', 'fixed_amount')})
        fields['fixed_amount'] = 'COALESCE(CAST(' + fields['fixed_amount'] + ' AS DECIMAL(21,9)),0)'
        fields['currency'] = fields['agreement_currency']
    else:
        fields.update({key: value(key) for key in ('start_date', 'end_date', 'notes', 'contract_terms')})
        fields['contract_terms'] = 'COALESCE(' + fields['contract_terms'] + ',d.agreement)'
    return fields


def predicate(column, operator, value, params, datetime_field=False):
    operator = str(operator).lower()
    if operator == 'timespan':
        from frappe.utils import get_timespan_date_range
        first, last = get_timespan_date_range(value)
        value = [str(first)[:10], str(last)[:10] + (' 23:59:59.999999' if datetime_field else '')]
        operator = 'between'
    if operator in ('=', '!=', '<', '>', '<=', '>=', 'like', 'not like'):
        params.append(value)
        return column + ' ' + operator + ' %s'
    if operator in ('in', 'not in'):
        values = value if isinstance(value, (tuple, list)) else str(value).split(',')
        if not values:
            return '1=1' if operator == 'not in' else '1=0'
        params.extend(values)
        return column + ' ' + operator + ' (' + ','.join(['%s'] * len(values)) + ')'
    if operator in ('between', 'not between') and isinstance(value, (tuple, list)) and len(value) == 2:
        params.extend(value)
        return column + ' ' + operator + ' %s AND %s'
    if operator == 'is' and value in ('set', 'not set'):
        return '(' + column + (" IS NOT NULL AND " + column + "!='')" if value == 'set' else " IS NULL OR " + column + "='')")
    frappe.throw('This filter is not supported in the combined planning list.')


def normalized_filters(filters, doctype):
    filters = frappe.parse_json(filters) or []
    if isinstance(filters, dict):
        filters = [[doctype, key, *(value if isinstance(value, list) else ['=', value])] for key, value in filters.items()]
    result = []
    for row in filters:
        if len(row) == 3:
            row = [doctype, *row]
        if len(row) != 4 or row[0] != doctype:
            # Never silently show unrelated drafts for a joined/child filter.
            result.append(None)
        else:
            result.append([field_name(row[1], doctype), row[2], row[3]])
    return filters, result


@frappe.whitelist()
def rows(doctype, fields=None, filters=None, order_by=None, start=0, page_length=20, planning_status=None, **_ignored):
    from plus_point.operations import company
    from plus_point.setup_flow import require_customer
    require_customer()
    if doctype not in TYPES:
        frappe.throw('Open Client agreements or Events.')
    frappe.has_permission(doctype, 'read', throw=True)
    business = company()
    native_fields = frappe.parse_json(fields) or ['name']
    native_filters, draft_filters = normalized_filters(filters, doctype)
    native_filters = list(native_filters)
    if doctype == 'PP Event Plan':
        native_filters.append([doctype, 'company', '=', business.name])
    else:
        projects = frappe.get_list('Project', filters={'company': business.name}, pluck='name', limit_page_length=0)
        native_filters.append([doctype, 'project', 'in', projects or ['']])
        native_filters.append([doctype, 'event_basis', '=', 0])
    status = str(planning_status or '')
    if status not in ('', 'Draft', 'Created'):
        frappe.throw('Choose All, Draft or Created.')
    start, length = max(0, cint(start)), min(2500, max(1, cint(page_length)))
    if start > 10000:
        frappe.throw('Narrow the search before loading more records.')
    order = []
    for item in str(order_by or 'modified desc').split(','):
        parts = item.strip().rsplit(' ', 1)
        key = field_name(parts[0], doctype)
        direction = parts[1].lower() if len(parts) == 2 else 'asc'
        if direction not in ('asc', 'desc'):
            frappe.throw('Choose a valid sort direction.')
        if not frappe.get_meta(doctype).has_field(key) and key not in ('name', 'creation', 'modified', 'owner', 'modified_by'):
            frappe.throw('Choose a supported sort field.')
        order.append((key, direction))
    order.append(('name', 'asc'))
    ordering = ','.join('`' + key + '` ' + direction for key, direction in order)
    wanted = list(dict.fromkeys([field_name(field, doctype) for field in native_fields] + ['name', 'pp_reference', *[key for key, _ in order]]))
    query_fields = [*native_fields, 'name', 'pp_reference', *[key for key, _ in order]]
    if doctype == 'PP Event Plan':
        query_fields.append('project.pp_archived as pp_record_archived')
    if status == 'Draft':
        native_filters.append([doctype, 'status', '=', 'Draft'] if doctype == 'PP Contract Terms' else [doctype, 'name', '=', '__pp_drafts_only__'])
    elif status == 'Created' and doctype == 'PP Contract Terms':
        native_filters.append([doctype, 'status', '!=', 'Draft'])
    native = frappe.get_list(doctype, fields=query_fields, filters=native_filters,
                  order_by=','.join(key + ' ' + direction for key, direction in order), limit_start=0, limit_page_length=start + length)
    native_total = frappe.get_list(doctype, fields=[{'COUNT':'name','as':'total'}], filters=native_filters)[0].total
    for row in native:
        row['pp_draft_name'] = None
    drafts, draft_total = [], 0
    if status != 'Created' and frappe.has_permission('PP Planning Draft', 'read'):
        mapping = expressions(TYPES[doctype])
        params = [business.name, TYPES[doctype]]
        where = ["d.company=%s", "d.kind=%s", "d.status IN ('Draft','Scheduled','Failed')"]
        if 'System Manager' not in frappe.get_roles():
            where.append('d.owner=%s')
            params.append(frappe.session.user)
        for condition in draft_filters:
            if condition is None:
                where.append('1=0')
                continue
            key, operator, value = condition
            where.append(predicate(mapping.get(key, 'NULL'), operator, value, params, key in ('creation', 'modified')))
        clause = ' FROM `tabPP Planning Draft` d WHERE ' + ' AND '.join(where)
        draft_total = frappe.db.sql('SELECT COUNT(*)' + clause, params)[0][0]
        select = [mapping.get(key, 'NULL') + ' AS `' + key + '`' for key in wanted]
        select += ['d.name AS pp_draft_name', 'd.status AS pp_draft_status', 'd.scheduled_for AS pp_scheduled_for', 'd.last_error AS pp_draft_error']
        drafts = frappe.db.sql('SELECT ' + ','.join(select) + clause + ' ORDER BY ' + ordering + ' LIMIT %s',
                               [*params, start + length], as_dict=True)
    result = [*native, *drafts]
    meta = frappe.get_meta(doctype)
    for key, direction in reversed(order):
        numeric = meta.get_field(key) and meta.get_field(key).fieldtype in ('Int', 'Float', 'Currency', 'Percent', 'Check')
        result.sort(key=lambda row: flt(row.get(key)) if numeric else str(row.get(key) or '').casefold(), reverse=direction == 'desc')
    # Native BaseList accepts a dictionary array. Preserve draft source metadata
    # without pretending these IDs belong to the agreement/event DocType.
    page = result[start:start + length]
    keys = list(dict.fromkeys([*wanted, 'pp_draft_name', 'pp_draft_status', 'pp_scheduled_for', 'pp_draft_error', 'pp_record_archived']))
    return dict(rows=page, keys=keys, values=[[row.get(key) for key in keys] for row in page], total=cint(native_total) + cint(draft_total))
