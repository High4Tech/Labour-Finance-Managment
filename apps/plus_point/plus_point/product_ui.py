"""Company-facing product metadata; upstream capabilities stay intact."""
import frappe


def website_context(context):
    if frappe.conf.get('pp_control_plane'):
        return
    context.update(app_name='PLUS POINT', favicon='/assets/plus_point/images/product-favicon.svg')


@frappe.whitelist()
def show_update_popup():
    # Release notifications belong to the platform operator, not company users.
    # Do not disable framework updates, diagnostics or the native admin tools.
    if frappe.conf.get('pp_control_plane'):
        from frappe.utils.change_log import show_update_popup as native
        return native()
    return None
