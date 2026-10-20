/* Local trial signup: simulated payment, isolated workspace and native password setup. */
(()=>{
 const $=id=>document.getElementById(id);let plan,request,timer;
 const show=step=>{['plan-picker','business-step','payment-step','approval-step'].forEach(id=>$('pp-'+id).hidden=id!==step);document.querySelectorAll('.pp-signup-progress li').forEach((node,i)=>{if(i===['plan-picker','business-step','payment-step','approval-step'].indexOf(step))node.setAttribute('aria-current','step');else node.removeAttribute('aria-current');});};
 async function call(method,args,button){
  $('pp-signup-error').hidden=true;if(button)button.disabled=true;
  try{const response=await fetch('/api/method/plus_point.signup.'+method,{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':window.frappe?.csrf_token||window.csrf_token||''},body:JSON.stringify(args)});const data=await response.json();if(!response.ok||!data.message)throw new Error();return data.message;}
  catch{const error=$('pp-signup-error');error.textContent='Could not complete this step. Check your details and connection, then try the same button again.';error.hidden=false;throw new Error('Signup step failed');}
  finally{if(button)button.disabled=false;}
 }
 const remember=()=>{try{sessionStorage.setItem('pp-demo-signup',JSON.stringify({reference:request.reference,token:request.token}));}catch{}};
 function approval(data){
  clearTimeout(timer);request={...request,...data};remember();show('approval-step');
  const approved=data.status==='Approved',busy=approved&&['Queued','Creating'].includes(data.activation),ready=approved&&['Ready','Active'].includes(data.activation);
  $('pp-approval-title').textContent=ready?'Your company workspace is ready':busy?'Preparing your company workspace':data.status==='Rejected'?'Signup not approved':approved?'Your signup is approved':'Waiting for High4Tech approval';
  $('pp-approval-message').textContent=approved?(data.activation_message||'High4Tech can now create your company workspace from this approved request.'):data.status==='Rejected'?'High4Tech declined this request. Contact your software provider to discuss the next step.':'Your simulated payment is recorded. High4Tech will approve the company before its workspace opens.';
  $('pp-reference').textContent='Reference: '+data.reference;
  const setup=$('pp-set-password'),open=$('pp-open-workspace');setup.hidden=!data.setup_url;setup.removeAttribute('href');if(data.setup_url)setup.href=data.setup_url;
  open.hidden=!ready;open.removeAttribute('href');if(ready)open.href=data.workspace_url;
  $('pp-refresh-setup').hidden=!(approved&&data.activation==='Ready'&&!data.setup_url);
  $('pp-login-details').textContent=data.login_email?'Login email: '+data.login_email+(data.login_username?' · Login ID: '+data.login_username:''):'';
  $('pp-approval-step').focus();
  if(busy)timer=setTimeout(async()=>{try{approval(await call('status',{reference:request.reference,token:request.token}));}catch{}},5000);
 }
 function payment(data){request={...request,...data};remember();if(data.status!=='Pending payment'){approval(data);return;}show('payment-step');$('pp-demo-summary').textContent=`${data.business} · ${data.plan} · ${data.amount} ${data.currency} / ${data.interval}`;}
 document.querySelectorAll('.pp-choose-plan').forEach(button=>button.onclick=()=>{plan=button.dataset.plan;$('pp-chosen-plan').textContent='Selected: '+plan;show('business-step');$('pp-signup-form').elements.contact_name.focus();});
 $('pp-back-plans').onclick=()=>show('plan-picker');
 $('pp-signup-form').onsubmit=async event=>{event.preventDefault();try{const data=Object.fromEntries(new FormData(event.currentTarget));payment(await call('register',{...data,plan},event.currentTarget.querySelector('[type=submit]')));}catch{}};
 $('pp-simulate-payment').onclick=async event=>{try{approval(await call('simulate_payment',{reference:request.reference,token:request.token},event.currentTarget));}catch{}};
 $('pp-refresh-setup').onclick=async event=>{try{approval(await call('refresh_password_setup',{reference:request.reference,token:request.token},event.currentTarget));}catch{}};
 $('pp-check-status').onclick=async event=>{try{approval(await call('status',{reference:request.reference,token:request.token},event.currentTarget));}catch{}};
 try{request=JSON.parse(sessionStorage.getItem('pp-demo-signup')||'null');if(request?.token)call('status',{reference:request.reference,token:request.token}).then(payment).catch(()=>{});}catch{}
})();
