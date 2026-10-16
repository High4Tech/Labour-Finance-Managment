"""Same-host local operator worker. Syncs registry entries every 60 seconds.

The worker owns provisioning credentials; the web API never receives them.
Failures are redacted and leave existing data untouched.
"""
import json
import subprocess
import time
from pathlib import Path

BENCH = Path('/home/frappe/frappe-bench')
PLATFORM = 'platform.localhost'


def main():
    while True:
        try:
            if (BENCH / 'sites' / PLATFORM / 'site_config.json').exists():
                result = subprocess.run(['bench', '--site', PLATFORM, 'execute',
                    'plus_point.platform.export_all'], cwd=BENCH, text=True, capture_output=True, check=True)
                for entry in json.loads(result.stdout):
                    # provision.py re-reads authoritative tenant/subscription state itself.
                    subprocess.run(['python', '/workspace/scripts/provision.py', '--tenant', entry['site']],
                        cwd=BENCH, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as error:
            print(f'Platform sync needs operator attention ({type(error).__name__})', flush=True)
        time.sleep(60)


if __name__ == '__main__':
    main()
