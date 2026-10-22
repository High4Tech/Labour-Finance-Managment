frappe.pages['pp-event-plans'].on_page_load=wrapper=>plus_point.mount_operations(wrapper,'pp-event-plans');
frappe.pages['pp-event-plans'].on_page_show=wrapper=>wrapper.pp_operations_load?.();
