"""Real HTTP suspension/expiry/seat-quota tests on the disposable local QA tenant."""
from datetime import date, timedelta
import json
from pathlib import Path
import subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import uuid

ROOT = Path(__file__).resolve().parents[1]
SITE = 'qa.localhost'


def bench(*args):
    result = subprocess.run(['docker', 'compose', 'exec', '-T', '-w', '/home/frappe/frappe-bench',
        'frappe', 'bench', '--site', SITE, *args], cwd=ROOT, text=True, capture_output=True, check=True)
    return result.stdout


def main():
    original = json.loads(bench('execute', 'plus_point.testing.current_entitlement'))
    token = json.loads(bench('execute', 'plus_point.testing.temporary_token'))
    base = 'http://127.0.0.1:8000'
    created = []
    def call(path, method='GET', data=None):
        request = Request(base + path, method=method, data=json.dumps(data).encode() if data is not None else None,
            headers={'Host': SITE, 'Content-Type': 'application/json',
                     'Authorization': f"token {token['api_key']}:{token['api_secret']}"})
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    def configure(value):
        bench('set-config', 'pp_entitlement', repr(value), '--parse')
    def rejects_write():
        assert 'data' in call('/api/resource/Company')
        try:
            result = call('/api/resource/ToDo', 'POST', {'description': 'PP subscription QA blocked write'})
            created.append(('ToDo', result['data']['name']))
            raise AssertionError('Suspended/expired write was accepted')
        except HTTPError as error:
            assert error.code == 403
    from urllib.parse import urlencode
    query = urlencode(dict(filters=json.dumps({'enabled': 1, 'user_type': 'System User',
        'name': ['not in', ['Administrator', 'Guest']]}), limit_page_length=0))
    seats = len(call('/api/resource/User?' + query)['data'])
    active = {'valid_until': str(date.today() + timedelta(days=2)), 'suspended': False, 'limits': {'users': seats + 1}}
    try:
        configure(dict(active, suspended=True))
        rejects_write()
        print('PASS real suspended tenant: reads retained, HTTP writes rejected')
        configure(dict(active, valid_until='2000-01-01'))
        rejects_write()
        print('PASS real expired tenant: reads retained, HTTP writes rejected')
        configure(active)
        for n in range(2):
            email = 'pp-seat-qa-' + uuid.uuid4().hex[:10] + '@example.invalid'
            try:
                result = call('/api/resource/User', 'POST', dict(email=email, first_name='PP Seat QA',
                    enabled=1, user_type='System User', send_welcome_email=0, roles=[{'role': 'Employee'}]))
                created.append(('User', result['data']['name']))
                assert n == 0, 'Seat quota accepted second active user'
            except HTTPError as error:
                assert n == 1 and error.code == 403
        print('PASS real plan seat limit through native User REST API')
        result = call('/api/resource/ToDo', 'POST', {'description': 'PP reactivation QA'})
        created.append(('ToDo', result['data']['name']))
        print('PASS tenant reactivation restores HTTP writes')
    finally:
        configure(active)
        for doctype, name in reversed(created):
            from urllib.parse import quote
            call('/api/resource/' + quote(doctype) + '/' + quote(name), 'DELETE')
        configure(original)
        print('PASS original QA entitlement restored and temporary data removed')


if __name__ == '__main__':
    main()
