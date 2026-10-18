frappe.ui.form.on('PP Equipment Booking',{
 setup(frm){frm.set_query('site',()=>({filters:{project:frm.doc.project,is_active:1}}));frm.set_query('item',()=>({filters:{is_stock_item:1,disabled:0}}));frm.set_query('warehouse',()=>({filters:{company:frm.doc.company,is_group:0,disabled:0}}));},
 async project(frm){if(frm.doc.project){const r=await frappe.db.get_value('Project',frm.doc.project,'company');frm.set_value('company',r.message.company);}},
 async item(frm){if(frm.doc.item){const r=await frappe.db.get_value('Item',frm.doc.item,'stock_uom');frm.set_value('stock_uom',r.message.stock_uom);}}
});
