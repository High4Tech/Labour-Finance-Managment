"""Container-side trusted credential rotation. New values arrive on stdin, never argv."""
import json
import os
from pathlib import Path
import sys
import frappe
import pymysql
from frappe.utils.password import update_password


def main():
    data = json.load(sys.stdin)
    os.chdir('/home/frappe/frappe-bench/sites')
    for folder in Path('.').iterdir():
        if folder.name.endswith('.localhost') and (folder / 'site_config.json').exists():
            frappe.init(folder.name)
            frappe.connect()
            update_password('Administrator', data['admin'], logout_all_sessions=True)
            frappe.db.set_value('User', 'Administrator', 'api_key', None)
            frappe.db.commit()
            frappe.clear_cache(user='Administrator')
            frappe.destroy()
    connection = pymysql.connect(host='mariadb', user='root', password=os.environ['PP_DB_PASSWORD'], autocommit=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT Host FROM mysql.user WHERE User=%s', ('root',))
            for (host,) in cursor.fetchall():
                cursor.execute('ALTER USER %s@%s IDENTIFIED BY %s', ('root', host, data['database']))
    finally:
        connection.close()
    print('PASS all local Administrator passwords, API keys, sessions and database root credentials rotated')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Credential rotation needs operator attention ({type(error).__name__}); no secrets printed', file=sys.stderr)
        sys.exit(1)
