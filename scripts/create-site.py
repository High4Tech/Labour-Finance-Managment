"""Native Frappe site installer with credentials read only from environment."""
import os
from pathlib import Path
import re
import sys
import frappe
from frappe.installer import _new_site

site = sys.argv[1]
if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.localhost', site):
    raise ValueError('Local host required')
os.chdir('/home/frappe/frappe-bench/sites')
if Path(site).exists():
    raise RuntimeError('Site already exists; refusing overwrite')
frappe.init(site, new_site=True)
try:
    _new_site(None, site, db_root_username='root', db_root_password=os.environ['PP_DB_PASSWORD'],
        admin_password=os.environ['PP_ADMIN_PASSWORD'], db_type='mariadb', db_host='mariadb',
        mariadb_user_host_login_scope='%')
except Exception:
    print('Native site installation failed; no existing data removed; credentials redacted', file=sys.stderr)
    sys.exit(1)
finally:
    frappe.destroy()
