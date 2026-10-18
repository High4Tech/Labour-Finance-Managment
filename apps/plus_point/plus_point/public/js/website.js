/* Signup stays separate from native website-user registration. */
(()=>{
 if(!location.pathname.endsWith('/login'))return;
 const mount=()=>{const form=document.querySelector('.for-login');if(!form||form.querySelector('.pp-plans-link'))return;const p=document.createElement('p');p.className='pp-plans-link text-center';p.style.marginTop='22px';const a=document.createElement('a');a.href='/plans';a.textContent='New to PLUS POINT? See plans & sign up';p.append(a);form.append(p);};
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();
