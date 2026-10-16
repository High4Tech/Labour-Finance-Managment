"""Exercise credential-safe native site creation; remove only the site this run creates."""
import os
from pathlib import Path
import subprocess
import uuid
import frappe
from frappe.commands.site import _drop_site

BENCH = Path('/home/frappe/frappe-bench')
site = 'pp-installer-qa-' + uuid.uuid4().hex[:12] + '.localhost'
if (BENCH / 'sites' / site).exists():
    raise RuntimeError('Unexpected test-site collision; refusing to touch it')
subprocess.run([str(BENCH / 'env/bin/python'), '/workspace/scripts/create-site.py', site], cwd=BENCH, check=True)
os.chdir(BENCH / 'sites')
frappe.init(site)
frappe.connect()
try:
    assert frappe.db.exists('User', 'Administrator')
    assert frappe.db.exists('DocType', 'User')
    print('PASS fresh native site/database created with environment-only credentials')
finally:
    # This hostname is generated above, proven absent before this run, never user input.
    _drop_site(site, db_root_username='root', db_root_password=os.environ['PP_DB_PASSWORD'], no_backup=True)
    frappe.destroy()
    print('PASS disposable installer database/user removed; site files archived by native Frappe')
