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

BENCH = Path('/home/frappe/frappe-bench')


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
    created = not (BENCH / 'sites' / site / 'site_config.json').exists()
    if created:
        try:
            subprocess.run([str(BENCH / 'env/bin/python'), '/workspace/scripts/create-site.py', site], cwd=BENCH, check=True)
        except subprocess.CalledProcessError:
            raise RuntimeError('Tenant site creation failed (credentials redacted); no sites were deleted') from None
    installed = json.loads(subprocess.check_output(['bench', '--site', site, 'list-apps', '--format', 'json'], cwd=BENCH, text=True)).get(site, [])
    for app in ('erpnext', 'hrms', 'plus_point'):
        if app not in installed:
            subprocess.run(['bench', '--site', site, 'install-app', app], cwd=BENCH, check=True)
    if created:
        subprocess.run(['bench', '--site', site, 'execute', 'plus_point.install.local_defaults'], cwd=BENCH, check=True)
        subprocess.run(['bench', '--site', site, 'enable-scheduler'], cwd=BENCH, check=True)
    if data.get('owner_email'):
        subprocess.run(['bench', '--site', site, 'execute', 'plus_point.platform.setup_local_owner',
            '--kwargs', json.dumps(dict(email=data['owner_email'], organization=data['organization']))], cwd=BENCH, check=True)
    subprocess.run(['bench', '--site', site, 'set-config', 'pp_entitlement',
        repr(data['entitlement']), '--parse'], cwd=BENCH, check=True)
    print(f'Tenant {site} provisioned/synchronized; credentials were not printed')


if __name__ == '__main__':
    main()
