"""Fail-fast, resumable local bench setup. Runs inside the official Bench image."""
import json
import os
from pathlib import Path
import re
import subprocess

BENCH = Path('/home/frappe/frappe-bench')
LOCK = json.loads(Path('/workspace/upstream.lock.json').read_text())


def run(*args, cwd=BENCH):
    subprocess.run(args, cwd=cwd, check=True)


def main():
    site = os.environ.get('LOCAL_SITE', 'demo.localhost')
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.localhost', site):
        raise ValueError('Local site must be a .localhost hostname')
    if not (BENCH / 'env/bin/python').exists():
        # Docker creates an empty mount directory; bench init accepts that directory.
        run('bench', 'init', str(BENCH), '--ignore-exist', '--frappe-branch', LOCK['frappe']['ref'],
            '--skip-redis-config-generation', '--python', 'python3.14', cwd=BENCH.parent)
    for app in ('frappe', 'erpnext', 'hrms'):
        pin = LOCK[app]
        if not (BENCH / 'apps' / app).exists():
            run('bench', 'get-app', '--branch', pin['ref'], pin['repository'])
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=BENCH / 'apps' / app, text=True).strip()
        if actual != pin['commit']:
            raise RuntimeError(f'{app} differs from upstream.lock.json; refusing an implicit upgrade')
    for key, value in {'db_host': 'mariadb', 'redis_cache': 'redis://redis-cache:6379',
                       'redis_queue': 'redis://redis-queue:6379',
                       'redis_socketio': 'redis://redis-queue:6379'}.items():
        run('bench', 'set-config', '-g', key, value)
    # Bench defaults to serving only the selected site; SaaS must route by Host.
    run('bench', 'set-config', '-g', 'serve_default_site', 'False', '--parse')
    run('bench', 'set-config', '-g', 'dns_multitenant', 'True', '--parse')
    app_path = BENCH / 'apps/plus_point'
    if not app_path.exists():
        app_path.symlink_to('/workspace/plus_point')
    run(str(BENCH / 'env/bin/pip'), 'install', '-e', str(app_path))
    apps_file = BENCH / 'sites/apps.txt'
    apps = apps_file.read_text().splitlines()
    if 'plus_point' not in apps:
        apps_file.write_text('\n'.join(apps + ['plus_point']) + '\n')
    if not (BENCH / 'sites' / site / 'site_config.json').exists():
        # Secrets are passed as environment variables, never logged by this script.
        try:
            subprocess.run([str(BENCH / 'env/bin/python'), '/workspace/scripts/create-site.py', site], cwd=BENCH, check=True)
        except subprocess.CalledProcessError:
            raise RuntimeError('Site creation failed; existing site data was retained (command credentials redacted)') from None
    installed = json.loads(subprocess.check_output(['bench', '--site', site, 'list-apps', '--format', 'json'], cwd=BENCH, text=True))
    installed = installed.get(site, [])
    for app in ('erpnext', 'hrms', 'plus_point'):
        if app not in installed:
            run('bench', '--site', site, 'install-app', app)
    run('bench', '--site', site, 'set-config', 'allow_tests', 'True', '--parse')
    run('bench', '--site', site, 'migrate')
    run('bench', '--site', site, 'execute', 'plus_point.install.local_defaults')
    run('bench', '--site', site, 'enable-scheduler')
    run('bench', 'build', '--app', 'plus_point')
    run('bench', 'set-config', '-g', 'default_site', 'None', '--parse')
    run('bench', '--site', site, 'list-apps')
    # The container supervisor waits until initial installation is complete.
    (BENCH / 'sites/.plus-point-ready').touch()


if __name__ == '__main__':
    main()
