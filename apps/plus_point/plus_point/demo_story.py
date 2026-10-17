"""Idempotent, explicitly labelled local demonstration story. No HTTP endpoint."""
import frappe
from frappe.utils import add_days,getdate,today


def seed():
    if frappe.local.site!='demo.localhost' or not frappe.conf.get('allow_tests'):
        raise RuntimeError('This story is only for the test-enabled local demo site')
    frappe.set_user('Administrator')
    marker='pp_demo_story_v1'
    if frappe.defaults.get_global_default(marker):
        return dict(preserved=True,note='Existing labelled demo story preserved')
    company=frappe.get_doc('Company','PLUS POINT Demo')
    def existing_or_create(doctype,filters,**values):
        name=frappe.db.exists(doctype,filters)
        return frappe.get_doc(doctype,name) if name else frappe.get_doc(dict(doctype=doctype,**values)).insert()
    for employee in frappe.get_all('Employee',filters={'company':company.name,'first_name':'PLUS POINT Demo'},pluck='name'):
        doc=frappe.get_doc('Employee',employee);doc.first_name='Ahmed';doc.last_name='Raza (Demo)';doc.save()
    customer=frappe.db.get_value('Customer',{'customer_name':'PLUS POINT Demo'},'name')
    if customer:
        doc=frappe.get_doc('Customer',customer);doc.customer_name='Crescent Builders (Demo)';doc.save()
    for name in frappe.get_all('Project',filters={'company':company.name,'project_name':'PLUS POINT Demo'},pluck='name'):
        doc=frappe.get_doc('Project',name);doc.project_name='DHA Homes — Phase 1 (Demo)';doc.save()
    for name in frappe.get_all('PP Site',filters={'site_name':'PLUS POINT Demo'},pluck='name'):
        doc=frappe.get_doc('PP Site',name)
        if frappe.db.get_value('Project',doc.project,'company')==company.name:
            doc.site_name='DHA construction site (Demo)';doc.save()
    if company.company_name=='PLUS POINT Demo':
        company.company_name='Crescent Workforce Services (Demo)';company.save()
    item=existing_or_create('Item',{'item_code':'PP-DEMO-LABOUR'},item_code='PP-DEMO-LABOUR',
        item_name='Skilled labour services (Demo)',item_group='Services',stock_uom='Nos',is_stock_item=0)
    start=add_days(today(),-34)
    stories=[('Hassan','Ali','Crescent Builders (Demo)','Garden housing project (Demo)','Garden housing site (Demo)',2000,3200),
             ('Sara','Khan','Cedar Infrastructure (Demo)','Canal road works (Demo)','Canal road site (Demo)',1800,3000),
             ('Bilal','Ahmed','Pak Logistics (Demo)','Warehouse expansion (Demo)','Warehouse site (Demo)',2200,3500)]
    created=0
    for index,(first,last,client_name,job,location,wage,rate) in enumerate(stories):
        client=existing_or_create('Customer',{'customer_name':client_name},customer_name=client_name,
            customer_type='Company',customer_group='Commercial',territory='All Territories')
        project=existing_or_create('Project',{'company':company.name,'project_name':job},project_name=job,
            company=company.name,customer=client.name,estimated_costing=100000,pp_enforce_spending_budget=1)
        worker=existing_or_create('Employee',{'company':company.name,'first_name':first,'last_name':last+' (Demo)'},
            first_name=first,last_name=last+' (Demo)',company=company.name,gender='Female' if first=='Sara' else 'Male',
            date_of_birth='1992-04-15',date_of_joining='2020-01-01',status='Active')
        site=existing_or_create('PP Site',{'project':project.name,'site_name':location},site_name=location,project=project.name,is_active=1)
        terms_name=frappe.db.get_value('PP Contract Terms',{'project':project.name,'billing_model':'Daily'},'name')
        if terms_name:
            terms=frappe.get_doc('PP Contract Terms',terms_name)
        else:
            contract=frappe.get_doc(dict(doctype='Contract',party_type='Customer',party_name=client.name,start_date=start,
                contract_terms='Synthetic demo agreement for daily labour services. Not a real contract.')).insert()
            terms=frappe.get_doc(dict(doctype='PP Contract Terms',contract=contract.name,project=project.name,
                billing_model='Daily',currency=company.default_currency,status='Active',effective_start=start)).insert()
        assignment=existing_or_create('PP Assignment',{'employee':worker.name,'site':site.name},employee=worker.name,
            site=site.name,project=project.name,contract_terms=terms.name,start_date=start,wage_rate=wage,client_rate=rate)
        for offset in range(34):
            day=add_days(start,offset)
            if getdate(day).weekday()==6 or (offset+index)%5==0:
                continue
            if frappe.db.exists('PP Work Entry',{'employee':worker.name,'work_date':day}):
                continue
            units=0.5 if (offset+index)%7==0 else 1
            work=frappe.get_doc(dict(doctype='PP Work Entry',assignment=assignment.name,work_date=day,units=units,
                status='Draft',remarks='Synthetic demonstration attendance — PP demo story v1')).insert()
            work.status='Approved';work.save();created+=1
        if first=='Sara':
            from plus_point.billing import create_invoice
            from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
            invoice=frappe.get_doc('Sales Invoice',create_invoice(terms.name,item.name)['name']);invoice.remarks='Synthetic demo invoice — no real sale';invoice.save();invoice.submit()
            receipt=get_payment_entry('Sales Invoice',invoice.name,party_amount=15000,bank_amount=15000,bank_account=company.default_cash_account)
            receipt.project=project.name;receipt.reference_no='PP-DEMO-RECEIPT';receipt.reference_date=today();receipt.insert();receipt.submit()
            payment=frappe.get_doc(dict(doctype='Payment Entry',company=company.name,payment_type='Pay',party_type='Employee',
                party=worker.name,project=project.name,paid_from=company.default_cash_account,paid_to=company.default_payable_account,
                paid_amount=7000,received_amount=7000,source_exchange_rate=1,target_exchange_rate=1,
                reference_no='PP-DEMO-WAGE-PAYMENT',reference_date=today())).insert();payment.submit()
            frappe.get_doc(dict(doctype='PP Wage Settlement',employee=worker.name,project=project.name,payment_entry=payment.name)).insert().submit()
    frappe.defaults.set_global_default(marker,'1')
    frappe.db.commit()
    frappe.clear_cache()
    return dict(created_work_entries=created,workers=4,clients=3,note='Labelled synthetic demo story; native records only, no external payments')
