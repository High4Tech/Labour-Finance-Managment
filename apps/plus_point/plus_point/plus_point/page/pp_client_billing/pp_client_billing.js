frappe.pages['pp-client-billing'].on_page_load=wrapper=>plus_point.mount_operations(wrapper,'pp-client-billing');
frappe.pages['pp-client-billing'].on_page_show=wrapper=>wrapper.pp_operations_load?.();
