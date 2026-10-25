"""Local operator only: isolated upload audit site, never the working company site."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

BENCH=Path('/home/frappe/frappe-bench')


def command(args):
    result=subprocess.run(args,cwd=BENCH,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if result.returncode:
        output=result.stdout
        for key in ('PP_DB_PASSWORD','PP_ADMIN_PASSWORD'):
            if os.environ.get(key):output=output.replace(os.environ[key],'[redacted]')
        print(output[-6000:],file=sys.stderr)
        raise RuntimeError('Local audit site command failed')


def main():
    action,run=sys.argv[1:3]
    if not re.fullmatch('[a-f0-9]{12}',run):raise RuntimeError('Exact audit run required')
    site='upload-audit-'+run+'.localhost'
    folder=(BENCH/'sites'/site).resolve()
    if folder.parent!=(BENCH/'sites').resolve():raise RuntimeError('Invalid audit site path')
    marker=folder/'private'/'pp-upload-audit.json'
    if action=='create':
        if folder.exists():raise RuntimeError('Audit site already exists')
        command(['bench','--site','qa.localhost','backup','--compress'])
        backup=max((BENCH/'sites/qa.localhost/private/backups').glob('*database.sql.gz'),key=lambda p:p.stat().st_mtime)
        command(['bench','new-site',site,'--source-sql',str(backup),'--db-root-password',os.environ['PP_DB_PASSWORD'],'--admin-password',os.environ['PP_ADMIN_PASSWORD']])
        config=json.loads((folder/'site_config.json').read_text())
        original=json.loads((BENCH/'sites/qa.localhost/site_config.json').read_text())
        config.update(encryption_key=original['encryption_key'],allow_tests=True,developer_mode=1,pause_scheduler=1,
                      pp_control_plane=False,pp_entitlement=dict(valid_until='2099-12-31',limits={}))
        (folder/'site_config.json').write_text(json.dumps(config,indent=2))
        marker.parent.mkdir(exist_ok=True,parents=True)
        marker.write_text(json.dumps(dict(run=run,site=site,database=config['db_name'])))
        print(json.dumps(dict(site=site,created=True)))
    elif action=='drop':
        if not marker.exists():raise RuntimeError('Audit ownership marker absent; cleanup refused')
        owned=json.loads(marker.read_text());config=json.loads((folder/'site_config.json').read_text())
        if owned!=dict(run=run,site=site,database=config['db_name']):raise RuntimeError('Audit database identity changed; cleanup refused')
        command(['bench','drop-site',site,'--no-backup','--force','--db-root-password',os.environ['PP_DB_PASSWORD']])
        print(json.dumps(dict(site=site,removed=True)))
    else:raise RuntimeError('Use create or drop')


if __name__=='__main__':main()
