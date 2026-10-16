import frappe
from frappe.model.document import Document


class PPSite(Document):
    def validate(self):
        old = self.get_doc_before_save()
        if old and old.project != self.project and frappe.db.exists("PP Assignment", {"site": self.name}):
            frappe.throw("A site with assignments cannot move to another project")
        if self.parent_site:
            if self.parent_site == self.name:
                frappe.throw("A site cannot be its own parent")
            parent = frappe.get_doc("PP Site", self.parent_site)
            if parent.project != self.project:
                frappe.throw("Parent and child sites must belong to the same project")
            seen = {self.name}
            while parent:
                if parent.name in seen:
                    frappe.throw("Circular parent site hierarchy")
                seen.add(parent.name)
                parent = frappe.get_doc("PP Site", parent.parent_site) if parent.parent_site else None
