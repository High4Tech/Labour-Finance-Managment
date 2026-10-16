"""Allocate real ERPNext employee payments to approved contractor earnings."""
from decimal import Decimal
import frappe
from frappe.model.document import Document
from plus_point.finance import money


class PPWageSettlement(Document):
    def validate(self):
        frappe.db.get_value('Employee', self.employee, 'name', for_update=True)
        payment = frappe.get_doc('Payment Entry', self.payment_entry)
        payment.check_permission('read')
        project = frappe.get_doc('Project', self.project)
        currency = frappe.db.get_value('Company', project.company, 'default_currency')
        if (payment.docstatus != 1 or payment.payment_type != 'Pay' or payment.party_type != 'Employee'
                or payment.party != self.employee or payment.company != project.company
                or payment.project != self.project or payment.paid_from_account_currency != currency
                or payment.paid_to_account_currency != currency):
            frappe.throw('Link a submitted employee payment in the project, company and company currency')
        self.amount = float(money(payment.paid_amount))
        if money(self.amount) <= 0:
            frappe.throw('Settlement amount must be positive')
        if self.docstatus == 1:
            earnings = frappe.get_all('PP Work Entry', filters=dict(employee=self.employee,
                project=self.project, status='Approved'), fields=['wage_amount'], limit_page_length=0)
            settled = frappe.get_all('PP Wage Settlement', filters=dict(employee=self.employee,
                project=self.project, docstatus=1, name=['!=', self.name]), fields=['amount'], limit_page_length=0)
            earned = sum((money(row.wage_amount) for row in earnings), Decimal(0))
            paid = sum((money(row.amount) for row in settled), Decimal(0))
            if paid + money(self.amount) > earned:
                frappe.throw('Settlement exceeds approved outstanding wages')


def protect_payment(doc, method=None):
    if frappe.db.exists('PP Wage Settlement', dict(payment_entry=doc.name, docstatus=1)):
        frappe.throw('Cancel the linked wage settlement before cancelling this employee payment')
