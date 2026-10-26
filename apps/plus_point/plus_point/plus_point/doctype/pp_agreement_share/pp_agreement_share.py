import frappe
from frappe.model.document import Document
class PPAgreementShare(Document):
    def validate(self):
        if not frappe.flags.get('pp_signing_operation'):frappe.throw('Use the agreement sharing actions to manage signing requests.')
        old=self.get_doc_before_save()
        if old and any((str(self.get(k)) if k=='base_modified' else self.get(k))!=(str(old.get(k)) if k=='base_modified' else old.get(k)) for k in ('contract_terms','token_hash','snapshot','digest','proposed_values','base_modified','change_summary')):frappe.throw('Signing snapshots cannot be rewritten.')
    def on_trash(self):
        if self.status=='Signed':frappe.throw('Signed agreement evidence cannot be deleted.')
