import frappe
from frappe.model.document import Document

class PPPlanningDraft(Document):
    def validate(self):
        from plus_point.drafts import assert_scope
        if not frappe.flags.get('pp_draft_write'):
            frappe.throw('Use the draft editor to change draft content.',frappe.PermissionError)
        assert_scope(self)

    def on_trash(self):
        from plus_point.drafts import assert_scope
        assert_scope(self)
        if self.status=='Scheduled':
            frappe.throw('Cancel scheduled creation before deleting this draft.')
