/** @type {Array<[string,string[]]>} */
export const clientSections=[
 ['Client details',['customer_name','customer_type','contact_name']],
 ['Contact details',['email','phone']],
 ['Address and billing',['country','default_currency','city','state','address_line1','address_line2','postal_code']]
];
/** @type {Record<string,string>} */
export const clientLabels={customer_name:'Client name',customer_type:'Client type',contact_name:'Contact person',email:'Email',phone:'Phone',country:'Country',default_currency:'Client invoice currency',city:'City',state:'State / region',address_line1:'Street address',address_line2:'Address line 2',postal_code:'Postal code'};
export function clientErrors(values){
 const errors={};
 for(const key of ['customer_name','contact_name','country','city','address_line1','default_currency'])if(!String(values[key]||'').trim())errors[key]='Complete this required field.';
 if(!['Company','Individual'].includes(values.customer_type))errors.customer_type='Choose Company or Individual.';
 if(!values.email&&!values.phone){errors.email='Enter an email or phone number so you can contact this client.';errors.phone=errors.email;}
 if(values.email&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email))errors.email='Enter an email such as name@example.com.';
 if(values.phone&&(!/^\+?[0-9 ()-]+$/.test(values.phone)||values.phone.replace(/\D/g,'').length<7||values.phone.replace(/\D/g,'').length>15))errors.phone='Enter 7–15 digits; +, spaces, parentheses and hyphens are allowed.';
 for(const [key,value] of Object.entries(values))if(String(value).length>(['customer_name','contact_name'].includes(key)?140:240))errors[key]='Shorten this field before saving.';
 return errors;
}
