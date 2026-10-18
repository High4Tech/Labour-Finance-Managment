/* Local demo requests only: no payment gateway or account password. */
(()=>{
 const $=id=>document.getElementById(id);let plan,request;
 const show=step=>{['plan-picker','business-step','payment-step','approval-step'].forEach(id=>$('pp-'+id).hidden=id!==step);document.querySelectorAll('.pp-signup-progress li').forEach((node,i)=>{if(i===['plan-picker','business-step','payment-step','approval-step'].indexOf(step))node.setAttribute('aria-current','step');else node.removeAttribute('aria-current');});};
 async function call(method,args,button){
  $('pp-signup-error').hidden=true;if(button)button.disabled=true;
  try{const response=await fetch('/api/method/plus_point.signup.'+method,{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':window.frappe?.csrf_token||window.csrf_token||''},body:JSON.stringify(args)});const data=await response.json();if(!response.ok||!data.message)throw new Error();return data.message;}
  catch{const error=$('pp-signup-error');error.textContent='Could not complete this step. Check your details and connection, then try the same button again.';error.hidden=false;throw new Error('Signup step failed');}
  finally{if(button)button.disabled=false;}
 }
 const remember=()=>{try{sessionStorage.setItem('pp-demo-signup',JSON.stringify(request));}catch{}};
 function approval(data){
  request={...request,...data};remember();show('approval-step');
  $('pp-approval-title').textContent=data.status==='Approved'?'Demo signup approved':data.status==='Rejected'?'Demo signup not approved':'Waiting for High4Tech approval';
  $('pp-approval-message').textContent=data.status==='Approved'?'High4Tech approved your demo request. No live account or payment has been created.':data.status==='Rejected'?'High4Tech declined this demo request. Contact your software provider to discuss the next step.':'Your simulated payment is recorded. High4Tech can review this request in Signup approvals. Use Check approval status to see a decision.';
  $('pp-reference').textContent='Reference: '+data.reference;$('pp-approval-step').focus();
 }
 function payment(data){request={...request,...data};remember();if(data.status!=='Pending payment'){approval(data);return;}show('payment-step');$('pp-demo-summary').textContent=`${data.business} · ${data.plan} · ${data.amount} ${data.currency} / ${data.interval}`;}
 document.querySelectorAll('.pp-choose-plan').forEach(button=>button.onclick=()=>{plan=button.dataset.plan;$('pp-chosen-plan').textContent='Selected: '+plan;show('business-step');$('pp-signup-form').elements.contact_name.focus();});
 $('pp-back-plans').onclick=()=>show('plan-picker');
 $('pp-signup-form').onsubmit=async event=>{event.preventDefault();try{const data=Object.fromEntries(new FormData(event.currentTarget));payment(await call('register',{...data,plan},event.currentTarget.querySelector('[type=submit]')));}catch{}};
 $('pp-simulate-payment').onclick=async event=>{try{approval(await call('simulate_payment',{reference:request.reference,token:request.token},event.currentTarget));}catch{}};
 $('pp-check-status').onclick=async event=>{try{approval(await call('status',{reference:request.reference,token:request.token},event.currentTarget));}catch{}};
 try{request=JSON.parse(sessionStorage.getItem('pp-demo-signup')||'null');if(request?.token)call('status',{reference:request.reference,token:request.token}).then(payment).catch(()=>{});}catch{}
})();
