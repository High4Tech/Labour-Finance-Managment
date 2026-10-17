"""Local external HTTP + native support worker integration. Secrets remain in memory."""
from datetime import date
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlparse, parse_qs
from urllib.request import Request, build_opener, HTTPCookieProcessor, urlopen
import uuid

ROOT=Path(__file__).resolve().parents[1]
PLATFORM='platform.localhost'
TENANT='qa.localhost'


def bench(site,method,kwargs=None):
    command=['docker','compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site',site,'execute',method]
    if kwargs is not None:
        command+=['--kwargs',json.dumps(kwargs)]
    result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        raise RuntimeError('Local operator check failed; captured output withheld')
    return json.loads(result.stdout)


class API:
    def __init__(self,site,token=None):
        self.site,self.token,self.csrf=site,token,None
        self.opener=build_opener(HTTPCookieProcessor(CookieJar()))

    def call(self,path,method='GET',payload=None,expect=200,raw=False):
        headers={'Host':self.site,'Content-Type':'application/json'}
        if self.token:
            headers['Authorization']='token '+self.token['api_key']+':'+self.token['api_secret']
        if self.csrf:
            headers['X-Frappe-CSRF-Token']=self.csrf
        request=Request('http://127.0.0.1:8000'+path,method=method,headers=headers,
            data=json.dumps(payload).encode() if payload is not None else None)
        try:
            with self.opener.open(request,timeout=40) as response:
                status,data=response.status,response.read()
        except HTTPError as error:
            status,data=error.code,error.read()
        expected=expect if isinstance(expect,tuple) else (expect,)
        if status not in expected:
            raise AssertionError(f'{method} {path.split("?")[0]} returned HTTP {status}, expected {expected}')
        if raw:
            return data
        return json.loads(data) if data else {}

    def login(self,user,password):
        result=self.call('/api/method/login','POST',dict(usr=user,pwd=password))
        assert result['message']=='Logged In'
        html=self.call('/desk',raw=True).decode()
        csrf=re.search(r'frappe\.csrf_token\s*=\s*"([^"]+)"',html)
        assert csrf,'Missing native session CSRF token'
        self.csrf=csrf.group(1)


def main():
    settings=dict(line.split('=',1) for line in (ROOT/'.env').read_text().splitlines()
                  if '=' in line and not line.startswith('#'))
    platform=API(PLATFORM,bench(PLATFORM,'plus_point.testing.temporary_token'))
    tenant=API(TENANT,bench(TENANT,'plus_point.testing.temporary_token'))
    owner=API(PLATFORM);owner.login(os.environ.get('PP_PLATFORM_SUPPORT_USER','Administrator'),
        os.environ.get('PP_PLATFORM_SUPPORT_PASSWORD') or settings['PP_ADMIN_PASSWORD'])
    assert tenant.call('/api/method/plus_point.tenancy.account_status')['message']['status']=='Active','QA tenant must start active'
    assert API(PLATFORM).call('/api/method/plus_point.support.request_account_help','POST',
        dict(tenant=TENANT,operation='Reset password'),expect=403)
    owner.call('/api/method/plus_point.support.request_account_help','POST',
        dict(tenant=TENANT,operation='Change login ID',new_username='Administrator'),expect=417)
    owner.call('/api/method/plus_point.support.apply_owner_help','POST',
        dict(email='Administrator',operation='Reset password'),expect=403)
    registry=platform.call('/api/resource/PP%20Tenant/'+TENANT)['data']
    subscription=platform.call('/api/resource/Subscription/'+quote(registry['subscription']))['data']
    base_plan=platform.call('/api/resource/Subscription%20Plan/'+quote(subscription['plans'][0]['plan']))['data']
    marker='pp-support-qa-'+uuid.uuid4().hex[:10]
    email=marker+'@example.invalid'
    password=secrets.token_urlsafe(26)
    replacement=secrets.token_urlsafe(26)
    username='ppold'+uuid.uuid4().hex[:10]
    new_username='ppnew'+uuid.uuid4().hex[:10]
    support_names=[]
    created_user=created_plan=None
    original_username_setting=None
    registry_changed=False
    def synchronize():
        result=subprocess.run(['docker','compose','exec','-T','frappe','python','/workspace/scripts/provision.py','--tenant',TENANT],
            cwd=ROOT,text=True,capture_output=True)
        if result.returncode:
            raise RuntimeError('Tenant synchronization failed; captured output withheld')
    def support(operation,**values):
        result=owner.call('/api/method/plus_point.support.request_account_help','POST',
            dict(tenant=TENANT,operation=operation,**values))['message']
        support_names.append(result['name'])
        deadline=time.monotonic()+130
        while time.monotonic()<deadline:
            outcome=owner.call('/api/method/plus_point.support.account_help_result?'+urlencode({'request_name':result['name']}))['message']
            if outcome['status']=='Completed':
                return outcome
            if outcome['status']=='Failed':
                raise AssertionError('Support job failed; inspect redacted operator diagnostics')
            time.sleep(2)
        raise AssertionError('Support job did not complete before the test deadline')
    try:
        created_plan=platform.call('/api/resource/Subscription%20Plan','POST',dict(plan_name=marker,
            currency=base_plan['currency'],item=base_plan['item'],price_determination='Fixed Rate',cost=1100,
            billing_interval='Month',billing_interval_count=1),expect=(200,201))['data']['name']
        platform.call('/api/resource/Subscription%20Plan/'+quote(created_plan),'PUT',{'cost':1250})
        assert float(platform.call('/api/resource/Subscription%20Plan/'+quote(created_plan))['data']['cost'])==1250
        print('PASS external HTTP pricing plan create/update/read',flush=True)
        settings_doc=tenant.call('/api/resource/System%20Settings/System%20Settings')['data']
        original_username_setting=settings_doc.get('allow_login_using_user_name',0)
        created_user=tenant.call('/api/resource/User','POST',dict(email=email,first_name='PLUS POINT Support QA',
            enabled=1,user_type='System User',username=username,new_password=password,send_welcome_email=0,
            roles=[dict(role='System Manager')]),expect=(200,201))['data']['name']
        platform.call('/api/resource/PP%20Tenant/'+TENANT,'PUT',{'owner_email':email,'suspended':1})
        registry_changed=True
        synchronize()
        assert tenant.call('/api/method/plus_point.tenancy.account_status')['message']['status']=='Suspended'
        tenant.call('/api/resource/ToDo','POST',{'description':marker},expect=403)
        print('PASS platform suspension reaches customer backend; writes blocked, reads retained',flush=True)
        support('Change login ID',new_username=new_username)
        customer=API(TENANT);customer.login(new_username,password)
        customer.call('/api/method/plus_point.support.request_account_help','POST',
            {'tenant':TENANT,'operation':'Reset password'},expect=403)
        print('PASS owner-authorized login-ID support works while suspended; tenant cannot invoke platform support',flush=True)
        platform.call('/api/resource/PP%20Tenant/'+TENANT,'PUT',{'suspended':0})
        synchronize()
        assert tenant.call('/api/method/plus_point.tenancy.account_status')['message']['status']=='Active'
        print('PASS platform reactivation restores customer access',flush=True)
        outcome=support('Reset password')
        parsed=urlparse(outcome['reset_link'])
        assert parsed.hostname==TENANT and parsed.path=='/update-password'
        key=parse_qs(parsed.query)['key'][0]
        raw_doc=platform.call('/api/resource/PP%20Support%20Request/'+quote(outcome['name']))['data']
        assert key not in json.dumps(raw_doc) and raw_doc.get('result_secret')!=outcome['reset_link']
        anonymous=API(TENANT)
        API(TENANT).call('/api/method/frappe.core.doctype.user.user.update_password','POST',
            dict(key=key,new_password=replacement,logout_all_sessions=1))
        anonymous.call('/api/method/frappe.core.doctype.user.user.update_password','POST',
            dict(key=key,new_password=replacement,logout_all_sessions=1),expect=410)
        fresh=API(TENANT);fresh.login(new_username,replacement)
        API(TENANT).call('/api/method/login','POST',dict(usr=new_username,pwd=password),expect=(401,403))
        print('PASS native one-time password reset, encrypted result, new login and old-password rejection; no email sent',flush=True)
        # Independent site credentials cannot be exchanged as arbitrary API access.
        for wrong in (API(TENANT,platform.token),API(PLATFORM,tenant.token)):
            wrong.call('/api/resource/User',expect=(401,403))
        platform.call('/api/resource/User/'+quote(email),expect=404)
        print('PASS cross-site token rejection and customer-account database isolation',flush=True)
        platform.call('/api/resource/PP%20Tenant/'+TENANT,'PUT',{'owner_email':registry['owner_email'],'suspended':registry['suspended']})
        synchronize()
        assert tenant.call('/api/method/plus_point.tenancy.account_status')['message']['status']=='Active'
        print('PASS platform reactivation restores customer access',flush=True)
    finally:
        if registry_changed:
            platform.call('/api/resource/PP%20Tenant/'+TENANT,'PUT',{'owner_email':registry['owner_email'],'suspended':registry['suspended']})
            synchronize()
        if created_user:
            tenant.call('/api/resource/User/'+quote(created_user),'DELETE',expect=(200,202))
        if original_username_setting is not None:
            bench(TENANT,'plus_point.testing.restore_support_test_setting',{'value':original_username_setting})
        for name in support_names:
            platform.call('/api/resource/PP%20Support%20Request/'+quote(name),'DELETE',expect=(200,202))
        if created_plan:
            platform.call('/api/resource/Subscription%20Plan/'+quote(created_plan),'DELETE',expect=(200,202))
        print('PASS registry/settings restored and temporary users, support requests and pricing plan removed',flush=True)


if __name__=='__main__':
    main()
