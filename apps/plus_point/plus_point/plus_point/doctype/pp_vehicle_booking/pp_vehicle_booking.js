frappe.ui.form.on('PP Vehicle Booking',{
 setup(frm){frm.set_query('site',()=>({filters:{project:frm.doc.project,is_active:1}}));frm.set_query('vehicle',()=>({filters:{company:frm.doc.company,pp_event_enabled:1}}));},
 async project(frm){if(frm.doc.project){const r=await frappe.db.get_value('Project',frm.doc.project,'company');frm.set_value('company',r.message.company);}},
 async vehicle(frm){if(frm.doc.vehicle){const r=await frappe.db.get_value('Vehicle',frm.doc.vehicle,['pp_cargo_uom','pp_crew_seats','pp_cargo_capacity']);frm.set_value('cargo_uom',r.message.pp_cargo_uom);frm.dashboard.set_headline_alert(__('Crew seats: {0} (driver excluded) · Inventory capacity: {1} {2}',[r.message.pp_crew_seats,r.message.pp_cargo_capacity,r.message.pp_cargo_uom]),'blue');}}
});
