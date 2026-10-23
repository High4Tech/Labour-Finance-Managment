import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from plus_point.finance import as_decimal


class PPContractTerms(Document):
    def validate(self):
        from plus_point.operations import validate_agreement
        validate_agreement(self)
        frappe.db.get_value('Contract', self.contract, 'name', for_update=True)
        old = self.get_doc_before_save()
        def normalized(doc, field):
            value = doc.get(field)
            if field == 'fixed_amount':
                return as_decimal(value or 0)
            if field in ('effective_start', 'effective_end'):
                return getdate(value) if value else None
            return value
        if old and any(normalized(self, k) != normalized(old, k) for k in
                       ("contract", "project", "billing_model", "currency")):
            if (frappe.db.exists("PP Work Entry", {"contract_terms": self.name}) or
                frappe.db.exists("PP Milestone", {"contract_terms": self.name})):
                frappe.throw("Billing terms cannot change after work entries or milestones exist")
        if self.billing_model=='Fixed' and not self.is_new():
            approved=sum(float(r.amount) for r in frappe.get_all('PP Milestone',filters={'contract_terms':self.name,'status':'Approved'},fields=['amount']))
            if float(self.fixed_amount or 0)<approved:frappe.throw('Fixed value cannot be less than approved milestones.')
        if self.billing_model not in {"Daily", "Fixed"}:
            frappe.throw("Billing model must be Daily or Fixed")
        if self.effective_end and getdate(self.effective_end) < getdate(self.effective_start):
            frappe.throw("End date must not precede start date")
        if self.billing_model == "Fixed" and as_decimal(self.fixed_amount or 0) <= 0:
            frappe.throw("Fixed contracts require a positive fixed amount")
        if self.billing_model == "Daily" and as_decimal(self.fixed_amount or 0) != 0:
            frappe.throw("Daily contracts must not specify a fixed amount")
        contract = frappe.get_doc("Contract", self.contract)
        project = frappe.get_doc("Project", self.project)
        if self.currency != frappe.db.get_value("Company", project.company, "default_currency"):
            frappe.throw("MVP contract currency must match project company currency")
        if contract.party_type != "Customer":
            frappe.throw("PLUS POINT terms require a customer contract")
        if project.customer and project.customer != contract.party_name:
            frappe.throw("Contract customer does not match project customer")
        other = frappe.db.get_value("PP Contract Terms", {
            "contract": self.contract, "project": self.project, "name": ["!=", self.name or ""]
        }, 'name', for_update=True)
        if other:
            frappe.throw("This ERPNext contract already has PLUS POINT terms for the project")
