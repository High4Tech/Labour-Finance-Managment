import frappe
from frappe.model.document import Document


class PPSignupRequest(Document):
    def validate(self):
        from plus_point.platform import require_platform
        if not getattr(self.flags, 'public_signup', False):
            require_platform()
        if not frappe.conf.get('pp_control_plane'):
            frappe.throw('Signup requests belong to High4Tech', frappe.PermissionError)
        old=self.get_doc_before_save()
        if old:
            for key in ('contact_name','business_name','email','plan','amount','currency','interval','token_hash','login_username'):
                if self.get(key)!=old.get(key):frappe.throw('Signup identity and quoted plan cannot change')
            permitted=set()
            if self.flags.public_signup:permitted.update(('payment_status','review_status'))
            if self.flags.signup_review:permitted.update(('review_status','reviewed_by','reviewed_on'))
            if self.flags.signup_activation:permitted.update(('workspace_site','workspace_subscription','activation_status','activation_message','setup_secret','setup_expires_on'))
            for key in ('payment_status','review_status','reviewed_by','reviewed_on','workspace_site','workspace_subscription','activation_status','activation_message','setup_secret','setup_expires_on'):
                if self.get(key)!=old.get(key) and key not in permitted:frappe.throw('Use the signup approval and company login actions')

