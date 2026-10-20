"""Keep local simulated-payment workspaces out of native invoice generation."""
import frappe


class DemoWorkspaceSubscription:
    def can_generate_new_invoice(self,posting_date=None):
        if self.get('pp_demo_workspace'):return False
        return super().can_generate_new_invoice(posting_date)

    def generate_invoice(self,*args,**kwargs):
        if self.get('pp_demo_workspace'):frappe.throw('This local trial uses simulated payments and cannot generate a software invoice')
        return super().generate_invoice(*args,**kwargs)

    def create_invoice(self,*args,**kwargs):
        if self.get('pp_demo_workspace'):frappe.throw('This local trial cannot generate a software invoice')
        return super().create_invoice(*args,**kwargs)
