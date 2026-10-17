import re
import frappe
from frappe.model.document import Document
from plus_point.platform import require_platform


class PPTenant(Document):
    def validate(self):
        require_platform()
        if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.localhost', self.site_hostname):
            frappe.throw('Local tenant hosts must end in .localhost')
        if self.site_hostname == frappe.local.site:
            frappe.throw('Choose a customer hostname distinct from the platform site')
        if any(int(self.get(field) or 0) < 0 for field in ('worker_limit', 'user_limit', 'site_limit')):
            frappe.throw('Subscription limits cannot be negative')
        old = self.get_doc_before_save()
        if old and old.site_hostname != self.site_hostname:
            frappe.throw('Tenant hostname cannot change after registration')
        subscription = frappe.get_doc('Subscription', self.subscription)
        if subscription.party_type != 'Customer':
            frappe.throw('Tenant subscriptions must bill an ERPNext Customer')
