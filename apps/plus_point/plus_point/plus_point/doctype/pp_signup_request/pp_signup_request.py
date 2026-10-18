import frappe
from frappe.model.document import Document


class PPSignupRequest(Document):
    def validate(self):
        from plus_point.platform import require_platform
        if not getattr(self.flags, 'public_signup', False):
            require_platform()
        if not frappe.conf.get('pp_control_plane'):
            frappe.throw('Signup requests belong to High4Tech', frappe.PermissionError)

