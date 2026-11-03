export const workerTabs=['Overview','Work details','Salary and leaves','Contact'];
export const workerGroups=[['first_name','last_name','gender','date_of_birth','date_of_joining','status','employee_number'],['department','designation','new_category','reports_to','employment_type'],['pp_salary_basis','pp_daily_rate','pp_monthly_rate','pp_leaves_per_month','pp_loan_allowed','pp_loan_wait_months','pp_loan_deduction_percent'],['cell_number','personal_email','current_address','person_to_be_contacted','emergency_phone_number','relation']];
export function workerErrors(values,today){
 const errors={};for(const key of ['first_name','gender','date_of_birth','date_of_joining','status'])if(!String(values[key]??'').trim())errors[key]='Complete this required field.';
 if(values.designation==='__new__'&&!String(values.new_category||'').trim())errors.new_category='Enter the new category name.';
 for(const key of ['first_name','last_name','person_to_be_contacted'])if(values[key]&&!/^[\p{L}\p{M} .\-'’ʼ]+$/u.test(values[key]))errors[key]='Use letters, spaces, apostrophes, periods or hyphens.';
 if(values.date_of_birth>today)errors.date_of_birth='Choose today or an earlier date.';
 if(values.date_of_birth&&values.date_of_joining&&values.date_of_joining<values.date_of_birth)errors.date_of_joining='Choose a joining date on or after the date of birth.';
 for(const key of ['cell_number','emergency_phone_number'])if(values[key]&&(!/^\+?[0-9 ()-]+$/.test(values[key])||values[key].replace(/\D/g,'').length<7||values[key].replace(/\D/g,'').length>15))errors[key]='Enter 7–15 digits; +, spaces, parentheses and hyphens are allowed.';
 if(values.personal_email&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.personal_email))errors.personal_email='Enter an email such as name@example.com.';
 for(const key of ['pp_daily_rate','pp_monthly_rate','pp_leaves_per_month','pp_loan_wait_months','pp_loan_deduction_percent'])if(values[key]!==undefined&&values[key]!==''&&(!Number.isFinite(Number(values[key]))||Number(values[key])<0))errors[key]='Enter a number of zero or greater.';
 if(Number(values.pp_leaves_per_month)>31)errors.pp_leaves_per_month='Use at most 31 leave days per month.';
 if(Number(values.pp_loan_deduction_percent)>100)errors.pp_loan_deduction_percent='Use a percentage from 0 to 100.';
 if(!Number.isInteger(Number(values.pp_loan_wait_months||0)))errors.pp_loan_wait_months='Use whole months.';
 return errors;
}
