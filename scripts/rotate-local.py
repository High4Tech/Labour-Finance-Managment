"""Host wrapper: rotate local credentials, then update ignored .env without printing values."""
import json
from pathlib import Path
import re
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[1]
pending = ROOT / '.local/credential-rotation.pending.json'
data = json.loads(pending.read_text()) if pending.exists() else dict(admin=secrets.token_urlsafe(32), database=secrets.token_urlsafe(32))
pending.parent.mkdir(exist_ok=True)
pending.write_text(json.dumps(data))
subprocess.run(['docker', 'compose', 'exec', '-T', 'frappe',
    '/home/frappe/frappe-bench/env/bin/python', '/workspace/scripts/rotate-credentials.py'],
    input=json.dumps(data), text=True, cwd=ROOT, check=True)
env_file = ROOT / '.env'
settings = env_file.read_text()
for key, value in [('PP_ADMIN_PASSWORD', data['admin']), ('PP_DB_PASSWORD', data['database'])]:
    settings = re.sub(rf'(?m)^{key}=.*$', f'{key}={value}', settings)
env_file.write_text(settings)
pending.unlink()
print('PASS fresh local credentials saved to ignored .env; restart the stack with the launcher')
