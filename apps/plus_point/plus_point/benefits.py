"""Worker leave and salary settings, with advances backed by native accounting."""
from decimal import Decimal
from functools import wraps
import uuid
import frappe
from frappe.utils import getdate, today, add_months, get_first_day, get_last_day, cint
from plus_point.setup_flow import linked, require_customer
from plus_point.finance import money, as_decimal


def atomic(function):
    @wraps(function)
    def run(*args,**kwargs):
        point='pp_worker_'+uuid.uuid4().hex[:10];frappe.db.savepoint(point)
        try:return function(*args,**kwargs)
        except Exception:
            frappe.db.rollback(save_point=point);raise
    return run


def worker_doc(employee, write=False):
    require_customer();doc=linked('Employee',employee);linked('Company',doc.company)
    doc.check_permission('write' if write else 'read')
    return doc


def installed():
    return bool(frappe.db.exists('DocType','PP Worker Loan'))


def eligibility(worker, day=None):
    day=getdate(day or today())
    eligible_on=getdate(add_months(worker.date_of_joining,cint(worker.get('pp_loan_wait_months')))) if worker.date_of_joining else None
    reason=('Activate this worker first.' if worker.status!='Active' else
        'Loans are disabled in this worker’s Salary and leaves settings.' if not worker.get('pp_loan_allowed') else
        'Set a joining date first.' if not eligible_on else
        f'Eligible from {eligible_on}.' if day<eligible_on else '')
    return dict(eligible=not reason,eligible_on=str(eligible_on or ''),reason=reason)


def validate_worker_settings(doc):
    for field in ['pp_salary_amount','pp_leaves_per_month','pp_loan_wait_months']:
        if as_decimal(doc.get(field) or 0)<0:frappe.throw('Salary, leave allowance and loan waiting months cannot be negative.')
    if as_decimal(doc.get('pp_leaves_per_month') or 0)>31:frappe.throw('Use at most 31 leave days per month.')
    if not 0<=as_decimal(doc.get('pp_loan_deduction_percent') or 0)<=100:frappe.throw('Loan deduction must be between 0 and 100 percent.')


def wage(worker):
    amount=money(worker.get('pp_salary_amount') or 0)
    return money(amount/Decimal(30)) if worker.get('pp_salary_basis')=='Monthly' else amount


@frappe.whitelist(methods=['POST'])
def activate(employee):
    doc=worker_doc(employee,True);doc.status='Active';doc.save()
    return dict(status=doc.status)


def leave_units(employee,day):
    if not installed():return Decimal(0)
    return sum((Decimal(str(r.units)) for r in frappe.get_list('PP Worker Leave',filters={'employee':employee,'leave_date':day,'docstatus':1},fields=['units'],limit_page_length=0)),Decimal(0))


def leave_map(employees,start,end):
    if not installed() or not employees:return {}
    rows=frappe.get_list('PP Worker Leave',filters={'employee':['in',list(set(employees))],'leave_date':['between',[start,end]],'docstatus':1},fields=['employee','leave_date','units'],limit_page_length=0)
    return {(r.employee,str(r.leave_date)):Decimal(str(r.units)) for r in rows}


def validate_leave(doc):
    worker=worker_doc(doc.employee,True);frappe.db.get_value('Employee',worker.name,'name',for_update=True)
    if worker.status!='Active':frappe.throw('Activate this worker before assigning leave.')
    day=getdate(doc.leave_date)
    if day<getdate(worker.date_of_joining) or worker.relieving_date and day>getdate(worker.relieving_date):frappe.throw('Leave must fall within this worker’s employment dates.')
    doc.company=worker.company;doc.units=float(Decimal('0.5') if doc.leave_type=='Half day' else Decimal(1))
    if frappe.db.exists('PP Worker Leave',{'employee':worker.name,'leave_date':day,'docstatus':1,'name':['!=',doc.name]}):frappe.throw('Leave has already been recorded on this date.')
    entries=frappe.get_list('PP Work Entry',filters={'employee':worker.name,'work_date':day},fields=['units','status'],limit_page_length=0)
    if any(r.status=='Approved' for r in entries):frappe.throw('Attendance is already approved on this date. Correct the attendance before assigning leave.')
    used=sum((Decimal(str(r.units)) for r in frappe.get_list('PP Worker Leave',filters={'employee':worker.name,'leave_date':['between',[get_first_day(day),get_last_day(day)]],'docstatus':1,'name':['!=',doc.name]},fields=['units'],limit_page_length=0)),Decimal(0))
    if used+Decimal(str(doc.units))>Decimal(str(worker.get('pp_leaves_per_month') or 0)):frappe.throw('This leave exceeds the worker’s monthly allowance. Review Salary and leaves first.')


@frappe.whitelist(methods=['POST'])
@atomic
def grant_leave(employee,leave_date,leave_type,reason):
    worker=worker_doc(employee,True)
    return frappe.get_doc(dict(doctype='PP Worker Leave',employee=worker.name,company=worker.company,leave_date=leave_date,leave_type=leave_type,reason=reason)).insert().submit().as_dict()


def validate_loan(doc):
    worker=worker_doc(doc.employee,True);frappe.db.get_value('Employee',worker.name,'name',for_update=True)
    doc.company=worker.company;doc.currency=frappe.db.get_value('Company',worker.company,'default_currency')
    check=eligibility(worker,doc.loan_date)
    if not check['eligible']:frappe.throw(check['reason'])
    if money(doc.amount)<=0:frappe.throw('Enter a positive loan amount.')
    if not 0<as_decimal(doc.deduction_percent)<=100:frappe.throw('Choose a monthly deduction percentage above 0 and at most 100.')
    if getdate(doc.loan_date)>getdate(today()):frappe.throw('Record a loan on its disbursement date, not a future date.')
    if doc.docstatus==1:
        if not doc.payment_entry:frappe.throw('Link the submitted employee advance payment before recording this loan as disbursed.')
        payment=linked('Payment Entry',doc.payment_entry)
        account=linked('Account',payment.paid_to)
        if (payment.docstatus!=1 or payment.payment_type!='Pay' or payment.party_type!='Employee' or payment.party!=worker.name or payment.company!=worker.company or payment.paid_to_account_currency!=doc.currency or payment.paid_from_account_currency!=doc.currency or money(payment.received_amount)!=money(doc.amount) or getdate(payment.posting_date)!=getdate(doc.loan_date) or account.root_type!='Asset' or account.account_type!='Receivable'):
            frappe.throw('Use an equal, submitted employee payment on the loan date, in company currency, to an employee advance receivable account.')
        if frappe.db.exists('PP Wage Settlement',{'payment_entry':payment.name,'docstatus':1}):frappe.throw('A wage payment cannot also be a loan disbursement.')
        if frappe.db.exists('PP Worker Loan',{'payment_entry':payment.name,'docstatus':1,'name':['!=',doc.name]}):frappe.throw('This payment is already linked to a loan.')


@frappe.whitelist(methods=['POST'])
@atomic
def grant_loan(employee,amount,deduction_percent,loan_date,reason,payment_entry=None):
    worker=worker_doc(employee,True)
    doc=frappe.get_doc(dict(doctype='PP Worker Loan',employee=worker.name,company=worker.company,amount=amount,deduction_percent=deduction_percent,loan_date=loan_date,reason=reason,payment_entry=payment_entry)).insert()
    if payment_entry:doc.submit()
    return dict(name=doc.name,disbursed=doc.docstatus==1)


@frappe.whitelist()
def payment_options(employee):
    worker=worker_doc(employee)
    rows=frappe.get_list('Payment Entry',filters={'company':worker.company,'party_type':'Employee','party':employee,'payment_type':'Pay','docstatus':1},fields=['name','posting_date','received_amount','paid_to','paid_to_account_currency'],order_by='posting_date desc',limit_page_length=0)
    return [r for r in rows if frappe.db.get_value('Account',r.paid_to,'account_type')=='Receivable' and not frappe.db.exists('PP Worker Loan',{'payment_entry':r.name,'docstatus':1}) and not frappe.db.exists('PP Wage Settlement',{'payment_entry':r.name,'docstatus':1})]


@frappe.whitelist(methods=['POST'])
@atomic
def disburse(loan,payment_entry):
    doc=linked('PP Worker Loan',loan);worker_doc(doc.employee,True)
    doc.check_permission('write');doc.payment_entry=payment_entry;doc.save();doc.submit()
    return dict(name=doc.name)


@frappe.whitelist()
def deduction_projects(employee):
    worker=worker_doc(employee)
    names=frappe.get_list('PP Work Entry',filters={'employee':worker.name,'status':'Approved'},pluck='project',limit_page_length=0)
    return frappe.get_list('Project',filters={'name':['in',list(set(names)) or ['']],'company':worker.company},fields=['name','project_name'],limit_page_length=0)


def recovered(employee,project=None):
    if not installed():return Decimal(0)
    filters={'employee':employee,'docstatus':1}
    if project:filters['project']=project
    return sum((money(r.amount) for r in frappe.get_list('PP Loan Recovery',filters=filters,fields=['amount'],limit_page_length=0)),Decimal(0))


@frappe.whitelist()
def balances(employee,month=None):
    worker=worker_doc(employee)
    if not installed():return dict(enabled=False,eligibility=dict(eligible=False,reason='Salary, leave and loan update is awaiting installation approval.'),loans=[],leaves=[],loan_outstanding='0.00',month=str(get_first_day(today())),monthly_outstanding='0.00',monthly_after_deduction='0.00',monthly_earned='0.00',proposed_deduction='0.00',recovered='0.00',leave_allowance=0)
    day=getdate(month or today());first=get_first_day(day);last=get_last_day(day)
    if not worker.get('pp_salary_basis'):worker.pp_salary_basis='Daily'
    loans=frappe.get_list('PP Worker Loan',filters={'employee':employee,'docstatus':['<',2]},fields=['name','amount','deduction_percent','loan_date','docstatus','reason','payment_entry'],order_by='loan_date,name',limit_page_length=0)
    entries=frappe.get_list('PP Work Entry',filters={'employee':employee,'status':'Approved','work_date':['between',[first,last]]},fields=['wage_amount','project'],limit_page_length=0)
    earned=sum((money(r.wage_amount) for r in entries),Decimal(0))
    payments=frappe.get_list('PP Wage Settlement',filters={'employee':employee,'docstatus':1},fields=['amount','payment_entry'],limit_page_length=0)
    paid=sum((money(r.amount) for r in payments if first<=getdate(frappe.db.get_value('Payment Entry',r.payment_entry,'posting_date'))<=last),Decimal(0))
    repayments=frappe.get_list('PP Loan Recovery',filters={'employee':employee,'docstatus':1},fields=['loan','amount','month'],limit_page_length=0)
    remaining=Decimal(0);projected=Decimal(0)
    deducted=sum((money(r.amount) for r in repayments if get_first_day(r.month)==first),Decimal(0))
    gross=max(Decimal(0),earned-paid)
    for loan in loans:
        loan.recovered=str(sum((money(r.amount) for r in repayments if r.loan==loan.name),Decimal(0)))
        balance=max(Decimal(0),money(loan.amount)-money(loan.recovered)) if loan.docstatus==1 else Decimal(0)
        loan.outstanding=str(balance);remaining+=balance
        already=any(r.loan==loan.name and get_first_day(r.month)==first for r in repayments)
        proposed=min(balance,money(earned*Decimal(str(loan.deduction_percent))/100),max(Decimal(0),gross-deducted-projected)) if loan.docstatus==1 and getdate(loan.loan_date)<=last and not already else Decimal(0)
        loan.proposed_deduction=str(proposed);projected+=proposed
    deducted=sum((money(r.amount) for r in repayments if get_first_day(r.month)==first),Decimal(0))
    return dict(enabled=True,eligibility=eligibility(worker),loans=loans,loan_outstanding=str(money(remaining)),month=str(first),monthly_earned=str(earned),monthly_outstanding=str(money(gross-deducted)),proposed_deduction=str(money(projected)),monthly_after_deduction=str(max(Decimal(0),money(gross-deducted-projected))),recovered=str(recovered(employee)),leave_allowance=worker.get('pp_leaves_per_month') or 0,leaves=frappe.get_list('PP Worker Leave',filters={'employee':employee,'docstatus':1,'leave_date':['between',[first,last]]},fields=['name','leave_date','leave_type','units','reason'],order_by='leave_date',limit_page_length=0))


@frappe.whitelist(methods=['POST'])
@atomic
def apply_deduction(loan,project,month):
    doc=linked('PP Worker Loan',loan);worker=worker_doc(doc.employee,True);event=linked('Project',project)
    if event.company!=worker.company:frappe.throw('Choose this worker’s company project.')
    frappe.db.get_value('Employee',worker.name,'name',for_update=True)
    if get_first_day(month)>get_first_day(today()):frappe.throw('Future wage deductions cannot be posted.')
    state=balances(worker.name,month);row=next((r for r in state['loans'] if r.name==loan),None)
    amount=money(row.proposed_deduction if row else 0)
    # Recovery is allocated to a project so the native worker statement and
    # subsequent cash settlements reconcile with the same approved earnings.
    earned=sum((money(r.wage_amount) for r in frappe.get_list('PP Work Entry',filters={'employee':worker.name,'project':project,'status':'Approved','work_date':['between',[get_first_day(month),get_last_day(month)]]},fields=['wage_amount'],limit_page_length=0)),Decimal(0))
    paid=sum((money(r.amount) for r in frappe.get_list('PP Wage Settlement',filters={'employee':worker.name,'project':project,'docstatus':1},fields=['amount'],limit_page_length=0)),Decimal(0))
    amount=min(amount,max(Decimal(0),earned-paid-recovered(worker.name,project)))
    if amount<=0:frappe.throw('No eligible outstanding wages to deduct, or this loan already has a deduction for this month.')
    payment=linked('Payment Entry',doc.payment_entry);business=linked('Company',worker.company)
    payable=business.default_payable_account
    if not payable:frappe.throw('Set the company payable account before posting a recovery.')
    journal=frappe.get_doc(dict(doctype='Journal Entry',voucher_type='Journal Entry',company=worker.company,posting_date=today(),user_remark=f'Loan {loan}, wage recovery for {state["month"]}',accounts=[dict(account=payable,party_type='Employee',party=worker.name,project=project,debit_in_account_currency=float(amount)),dict(account=payment.paid_to,party_type='Employee',party=worker.name,project=project,credit_in_account_currency=float(amount))])).insert();journal.submit()
    recovery=frappe.get_doc(dict(doctype='PP Loan Recovery',loan=loan,employee=worker.name,company=worker.company,project=project,month=state['month'],amount=float(amount),journal_entry=journal.name,recovery_key=loan+':'+state['month'])).insert();recovery.submit()
    return dict(name=recovery.name,amount=str(amount),journal=journal.name)


def protect_finance(doc,method=None):
    if not installed():return
    field='payment_entry' if doc.doctype=='Payment Entry' else 'journal_entry'
    dt='PP Worker Loan' if doc.doctype=='Payment Entry' else 'PP Loan Recovery'
    if frappe.db.exists(dt,{field:doc.name,'docstatus':1}):frappe.throw('Cancel the linked worker loan or recovery before cancelling this accounting record.')


def validate_recovery(doc):
    loan=linked('PP Worker Loan',doc.loan);worker=worker_doc(loan.employee,True)
    if loan.docstatus!=1:frappe.throw('Recover only a disbursed loan.')
    frappe.db.get_value('Employee',worker.name,'name',for_update=True)
    if doc.docstatus==1:
        state=balances(worker.name,doc.month);row=next(r for r in state['loans'] if r.name==loan.name)
        if money(doc.amount)>money(row.proposed_deduction):frappe.throw('Recovery exceeds the permitted monthly deduction.')
    if get_first_day(doc.month)>get_first_day(today()):frappe.throw('Future wage deductions cannot be posted.')
    doc.month=str(get_first_day(doc.month));doc.recovery_key=loan.name+':'+str(doc.month)
    if (doc.employee,doc.company)!=(worker.name,worker.company):frappe.throw('Recovery worker and company must match the loan.')
    project=linked('Project',doc.project)
    if project.company!=worker.company:frappe.throw('Recovery project must belong to this worker’s company.')
    earned=sum((money(r.wage_amount) for r in frappe.get_list('PP Work Entry',filters={'employee':worker.name,'project':project.name,'status':'Approved'},fields=['wage_amount'],limit_page_length=0)),Decimal(0))
    paid=sum((money(r.amount) for r in frappe.get_list('PP Wage Settlement',filters={'employee':worker.name,'project':project.name,'docstatus':1},fields=['amount'],limit_page_length=0)),Decimal(0))
    if doc.docstatus==1 and money(doc.amount)>max(Decimal(0),earned-paid-recovered(worker.name,project.name)):frappe.throw('Recovery exceeds the project’s outstanding wages.')
    journal=linked('Journal Entry',doc.journal_entry);payment=linked('Payment Entry',loan.payment_entry)
    if journal.docstatus!=1 or journal.company!=worker.company:frappe.throw('Link a submitted recovery journal in this company.')
    business=linked('Company',worker.company)
    debit=sum((money(r.debit_in_account_currency) for r in journal.accounts if r.account==business.default_payable_account and r.party_type=='Employee' and r.party==worker.name and r.project==doc.project),Decimal(0))
    credit=sum((money(r.credit_in_account_currency) for r in journal.accounts if r.account==payment.paid_to and r.party_type=='Employee' and r.party==worker.name and r.project==doc.project),Decimal(0))
    if money(doc.amount)<=0 or debit!=money(doc.amount) or credit!=money(doc.amount):frappe.throw('Recovery journal must debit worker payable and credit the loan advance by the exact recovery amount.')
    own=sum((money(r.amount) for r in frappe.get_list('PP Loan Recovery',filters={'loan':loan.name,'docstatus':1,'name':['!=',doc.name]},fields=['amount'],limit_page_length=0)),Decimal(0))
    if own+money(doc.amount)>money(loan.amount):frappe.throw('Recovery exceeds this loan’s outstanding balance.')
    if recovered(worker.name)+money(doc.amount)>sum((money(r.amount) for r in frappe.get_list('PP Worker Loan',filters={'employee':worker.name,'docstatus':1},fields=['amount'],limit_page_length=0)),Decimal(0)):frappe.throw('Recovery exceeds outstanding loans.')


def cancel_loan(doc,method=None):
    if frappe.db.exists('PP Loan Recovery',{'loan':doc.name,'docstatus':1}):frappe.throw('Cancel the linked recoveries before cancelling a loan.')


def cancel_recovery(doc,method=None):
    journal=linked('Journal Entry',doc.journal_entry)
    doc.db_set('recovery_key',None,update_modified=False)
    if journal.docstatus==1:
        # The recovery is already cancelled at on_cancel, so its guard permits
        # cancelling the exact journal; ledger reversals stay native and atomic.
        journal.cancel()


def install():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    fields=[('pp_salary_basis','Salary basis','Select','Daily\nMonthly'),('pp_salary_amount','Salary amount','Currency',None),('pp_loan_allowed','Eligible for loans','Check',None),('pp_loan_wait_months','Loan waiting period (months)','Int',None),('pp_loan_deduction_percent','Monthly loan deduction (%)','Percent',None),('pp_leaves_per_month','Leave days per month','Float',None)]
    create_custom_fields({'Employee':[dict(fieldname=k,label=label,fieldtype=kind,**({'options':options} if options else {})) for k,label,kind,options in fields]})
    for dt in ['pp_worker_leave','pp_worker_loan','pp_loan_recovery']:frappe.reload_doc('plus_point','doctype',dt)


@frappe.whitelist()
def event_options(employee):
    worker=worker_doc(employee)
    plans=frappe.get_list('PP Event Plan',filters={'company':worker.company,'end_date':['>=',today()]},fields=['name','event_name','start_date','end_date','contract_terms'],order_by='start_date,event_name',limit_page_length=0)
    return [p for p in plans if frappe.db.get_value('PP Contract Terms',p.contract_terms,'status')=='Active']


@frappe.whitelist()
def event_positions(employee,plan):
    from plus_point.events import plan_doc
    worker=worker_doc(employee);event=plan_doc(plan)
    if worker.company!=event.company:frappe.throw('Choose an event in this worker’s company.')
    from plus_point.operations import coverage
    days=coverage(event);positions=[]
    for row in event.staffing:
        start=max(getdate(today()),getdate(row.start_date))
        if start>getdate(row.end_date) or row.designation!=worker.designation:continue
        free=min((d['missing'] for d in days if d['site']==row.site and d['designation']==row.designation and start<=getdate(d['date'])<=getdate(row.end_date)),default=0)
        if free>0:positions.append(dict(name=row.name,site=row.site,title=frappe.db.get_value('PP Site',row.site,'site_name'),start=str(start),end=str(row.end_date),free=free))
    return dict(positions=positions,sites=[dict(name=r.name,title=r.site_name) for r in frappe.get_list('PP Site',filters={'project':event.project,'is_active':1},fields=['name','site_name'],limit_page_length=0)],designation=worker.designation,default_wage=str(wage(worker)),fixed=frappe.db.get_value('PP Contract Terms',event.contract_terms,'billing_model')=='Fixed')


@frappe.whitelist(methods=['POST'])
@atomic
def assign_event(employee,plan,position=None,extra=False,site=None,wage_rate=0,client_rate=0):
    from plus_point.events import plan_doc
    from plus_point.operations import add_requirement,coverage
    from plus_point.crew import assign
    worker=worker_doc(employee,True);event=plan_doc(plan,True)
    from plus_point.budget import lock_project
    lock_project(event.project);frappe.db.get_value('Employee',worker.name,'name',for_update=True)
    if worker.company!=event.company:frappe.throw('Choose an event in this worker’s company.')
    if not worker.designation:frappe.throw('Set this worker’s category in Work details first.')
    if frappe.db.exists('PP Assignment',{'employee':worker.name,'project':event.project,'end_date':['>=',today()]}):frappe.throw('This worker is already assigned to this event.')
    options=event_positions(employee,plan)
    choice=next((r for r in options['positions'] if r['name']==position),None)
    if not choice and not cint(extra):frappe.throw('No available position matches this worker’s category. Choose Add as extra crew to record a separate event requirement.')
    if choice:
        row=next(r for r in event.staffing if r.name==position);site=row.site;first=choice['start'];last=choice['end'];pay=money(row.wage_rate or wage(worker));charge=money(row.client_rate)
    else:
        if not any(r['name']==site for r in options['sites']):frappe.throw('Choose a site in this event.')
        first=str(max(getdate(today()),getdate(event.start_date)));last=str(event.end_date);pay=money(wage_rate or wage(worker));charge=Decimal(0) if options['fixed'] else money(client_rate)
    if pay<=0:frappe.throw('Set this worker’s salary, or enter a positive daily payroll wage.')
    if not options['fixed'] and charge<=0:frappe.throw('Enter a positive daily client rate for the extra crew.')
    if not choice:
        same=next((r for r in event.staffing if r.site==site and r.designation==worker.designation and getdate(r.start_date)<=getdate(last) and getdate(r.end_date)>=getdate(first)),None)
        if same:
            same.workers_required+=1;event.save()
        else:add_requirement(event.name,dict(site=site,designation=worker.designation,start_date=first,end_date=last,workers_required=1,wage_rate=float(pay),client_rate=float(charge),phase='Event'))
    result=assign(event.project,site,event.contract_terms,first,last,float(pay),float(charge),[worker.name])
    for name in result.get('assignments',[]):frappe.db.set_value('PP Assignment',name,'pp_event_plan',event.name)
    return dict(created=result['created'],extra=not bool(choice),event=event.event_name)
