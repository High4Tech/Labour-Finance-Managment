frappe.ui.form.on('PP Event Plan',{
 setup(frm){frm.set_query('contract_terms',()=>({filters:{project:frm.doc.project,status:'Active'}}));frm.set_query('site','staffing',()=>({filters:{project:frm.doc.project,is_active:1}}));},
 async project(frm){if(!frm.doc.project)return;const r=await frappe.db.get_value('Project',frm.doc.project,['company','project_name','expected_start_date','expected_end_date']);await frm.set_value('company',r.message.company);if(!frm.doc.event_name)frm.set_value('event_name',r.message.project_name);if(!frm.doc.start_date&&r.message.expected_start_date)frm.set_value('start_date',r.message.expected_start_date);if(!frm.doc.end_date&&r.message.expected_end_date)frm.set_value('end_date',r.message.expected_end_date);}
});
