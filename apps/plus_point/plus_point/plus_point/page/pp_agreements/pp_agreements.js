frappe.pages['pp-agreements'].on_page_load=wrapper=>plus_point.mount_operations(wrapper,'pp-agreements');
frappe.pages['pp-agreements'].on_page_show=wrapper=>wrapper.pp_operations_load?.();
