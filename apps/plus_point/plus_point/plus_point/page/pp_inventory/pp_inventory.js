frappe.pages['pp-inventory'].on_page_load=wrapper=>plus_point.mount_resource_page(wrapper);
frappe.pages['pp-inventory'].on_page_show=wrapper=>wrapper.pp_inventory_load?.();
