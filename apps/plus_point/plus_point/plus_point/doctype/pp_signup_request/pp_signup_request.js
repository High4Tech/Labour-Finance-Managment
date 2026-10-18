frappe.ui.form.on('PP Signup Request',{
    refresh(frm){
        frm.dashboard.set_headline_alert(__('Demo only: no money was collected and approval does not create a tenant login.'),'orange');
        if(frm.doc.review_status!=='Awaiting approval')return;
        for(const [label,decision] of [['Approve demo signup','Approved'],['Reject demo signup','Rejected']])
            frm.add_custom_button(__(label),()=>frappe.call({method:'plus_point.signup.review',type:'POST',
                args:{reference:frm.doc.name,decision},freeze:true,callback:()=>frm.reload_doc()}));
    }
});
