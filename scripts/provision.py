"""Trusted operator worker for local .localhost tenants. Never invoked by a web request.

Run in the Frappe container. Native bench creates each isolated database and user.
No deletion, shell interpolation or overwriting existing sites is supported.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import fcntl

BENCH = Path('/home/frappe/frappe-bench')


def native_json(site,method,args=None,input_data=None):
    command=['bench','--site',site,'execute',method]
    # Bench v16 evaluates --kwargs as a Python literal (JSON booleans fail).
    if args is not None:command+=['--kwargs',repr(args)]
    result=subprocess.run(command,cwd=BENCH,text=True,input=json.dumps(input_data) if input_data is not None else None,
        capture_output=True,timeout=180)
    if result.returncode:raise RuntimeError('Local workspace operation failed; child output redacted')
    return json.loads(result.stdout) if result.stdout.strip() else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform-site', default='platform.localhost')
    parser.add_argument('--tenant', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.localhost', args.platform_site):
        raise ValueError('Only local platform hosts are supported')
    output = subprocess.check_output(['bench', '--site', args.platform_site, 'execute',
        'plus_point.platform.export_entitlement', '--kwargs', json.dumps({'tenant': args.tenant})], cwd=BENCH, text=True)
    data = json.loads(output)
    site = data['site']
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.localhost', site) or site == args.platform_site:
        raise ValueError('Tenant must use its own local hostname')
    lock_dir=BENCH/'sites'/'.provision-locks';lock_dir.mkdir(exist_ok=True)
    with (lock_dir/(site+'.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        data=native_json(args.platform_site,'plus_point.platform.export_entitlement',dict(tenant=site))
        provision(args.platform_site,data)


def provision(platform_site,data):
    site=data['site'];reference=data.get('signup_reference')
    if reference and data.get('signup_status')=='Failed':return
    if reference and data.get('signup_status') in ('Queued','Creating'):
        native_json(platform_site,'plus_point.activation.mark_creating',dict(reference=reference))
    try:
        provision_inner(platform_site,data)
    except Exception:
        if reference and data.get('signup_status') in ('Queued','Creating'):
            native_json(platform_site,'plus_point.activation.finish_from_stdin',input_data=dict(reference=reference,failed=True))
        raise RuntimeError('Workspace setup failed; existing sites were retained and child output was redacted') from None


def provision_inner(platform_site,data):
    site=data['site'];reference=data.get('signup_reference')
    config_path=BENCH/'sites'/site/'site_config.json'
    created = not config_path.exists()
    if reference and not created:
        if json.loads(config_path.read_text()).get('pp_signup_reference')!=reference:
            raise RuntimeError('Refusing to reuse a site not bound to this signup')
    if created:
        try:
            env=dict(os.environ)
            if reference:env.update(PP_SIGNUP_REFERENCE=reference,PP_SIGNUP_COMPANY=data['organization'],PP_SIGNUP_OWNER=data['owner_email'])
            subprocess.run([str(BENCH / 'env/bin/python'), '/workspace/scripts/create-site.py', site], cwd=BENCH, check=True,env=env,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            raise RuntimeError('Tenant site creation failed (credentials redacted); no sites were deleted') from None
    installed = json.loads(subprocess.check_output(['bench', '--site', site, 'list-apps', '--format', 'json'], cwd=BENCH, text=True)).get(site, [])
    for app in ('erpnext', 'hrms', 'plus_point'):
        if app not in installed:
            subprocess.run(['bench', '--site', site, 'install-app', app], cwd=BENCH, check=True)
    if created or reference and not json.loads(config_path.read_text()).get('pp_signup_setup_initialized'):
        subprocess.run(['bench', '--site', site, 'execute', 'plus_point.install.local_defaults'], cwd=BENCH, check=True)
        subprocess.run(['bench', '--site', site, 'enable-scheduler'], cwd=BENCH, check=True)
    if data.get('owner_email'):
        subprocess.run(['bench', '--site', site, 'execute', 'plus_point.platform.setup_local_owner',
            '--kwargs', json.dumps(dict(email=data['owner_email'], organization=data['organization']))], cwd=BENCH, check=True)
    subprocess.run(['bench', '--site', site, 'set-config', 'pp_entitlement',
        repr(data['entitlement']), '--parse'], cwd=BENCH, check=True)
    if reference and data.get('signup_status') in ('Queued','Creating','Ready'):
        outcome=native_json(site,'plus_point.activation.initialize_customer',dict(reference=reference,email=data['owner_email'],
            organization=data['organization'],username=data.get('login_username') or '',issue_link=data.get('signup_status') in ('Queued','Creating')))
        if outcome and (outcome.get('setup_url') or outcome.get('activated')):
            native_json(platform_site,'plus_point.activation.finish_from_stdin',input_data=dict(reference=reference,**outcome))
    print(f'Tenant {site} provisioned/synchronized; credentials were not printed')


if __name__ == '__main__':
    main()
