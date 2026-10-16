"""Run from the host using any Python 3. No credentials printed or persisted."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from http.cookiejar import CookieJar
import json
import os
import re
from pathlib import Path
import statistics
import subprocess
import sys
import time
from threading import Barrier
from urllib.request import Request, build_opener, HTTPCookieProcessor, urlopen
from urllib.error import HTTPError
from urllib.parse import quote
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', default='demo.localhost')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--other-site', help='Optional second local test-enabled site for isolation checks')
    parser.add_argument('--attendance-race', action='store_true', help='Race 10 draft attendance writes against local demo allocations')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.localhost', args.site):
        raise ValueError('Tests support local site hostnames only')
    if args.other_site and not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.localhost', args.other_site):
        raise ValueError('Second site must be a local hostname')
    base = f'http://127.0.0.1:{args.port}'
    def call(path, method='GET', payload=None, token=None, site=None):
        headers = {'Host': site or args.site, 'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f"token {token['api_key']}:{token['api_secret']}"
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(base + path, headers=headers, data=data, method=method)
        with urlopen(request, timeout=60) as response:
            content = response.read()
            return json.loads(content) if response.headers.get_content_type() == 'application/json' else content
    def check(label, fn):
        fn()
        print('PASS ' + label, flush=True)
    deadline = time.monotonic() + 180
    while True:
        try:
            assert call('/api/method/ping')['message'] == 'pong'
            break
        except Exception:
            if time.monotonic() > deadline:
                raise RuntimeError('Local Frappe site did not become ready') from None
            time.sleep(3)
    print('PASS actual Frappe API ping')
    settings = dict(line.split('=', 1) for line in (ROOT / '.env').read_text().splitlines()
                    if '=' in line and not line.lstrip().startswith('#'))
    login = build_opener(HTTPCookieProcessor(CookieJar()))
    request = Request(base + '/api/method/login', data=json.dumps(dict(usr='Administrator',
        pwd=settings['PP_ADMIN_PASSWORD'])).encode(), headers={'Host': args.site, 'Content-Type': 'application/json'})
    with login.open(request, timeout=60) as response:
        assert json.load(response)['message'] == 'Logged In'
    print('PASS actual Administrator login (fresh local credentials)')
    def get_token(site):
        result = subprocess.run(['docker', 'compose', 'exec', '-T', 'frappe', 'bash', '-lc',
            f'cd /home/frappe/frappe-bench && bench --site {site} execute plus_point.testing.temporary_token'],
            cwd=ROOT, text=True, capture_output=True, check=True)
        return json.loads(result.stdout)
    token = get_token(args.site)
    for doctype in ('Company', 'Employee', 'Project', 'PP Site', 'PP Assignment', 'PP Daily Register', 'PP Tenant'):
        assert 'data' in call('/api/resource/' + quote(doctype), token=token)
    print('PASS native ERPNext, HRMS and custom DocType API reads')
    marker = 'PLUS POINT HTTP QA ' + uuid.uuid4().hex
    created = call('/api/resource/ToDo', 'POST', dict(description=marker), token)
    name = created['data']['name']
    path = '/api/resource/ToDo/' + quote(name)
    try:
        assert call(path, token=token)['data']['description'] == marker
        call(path, 'PUT', dict(description=marker + ' updated'), token)
        assert call(path, token=token)['data']['description'].endswith(' updated')
        try:
            call(path)
            raise AssertionError('Anonymous read unexpectedly succeeded')
        except HTTPError as error:
            assert error.code in (401, 403)
        print('PASS actual database CRUD and anonymous access rejection')
    finally:
        call(path, 'DELETE', token=token)
    try:
        call(path, token=token)
        raise AssertionError('Deleted record still exists')
    except HTTPError as error:
        assert error.code == 404
    print('PASS temporary HTTP fixture deleted')
    if args.other_site:
        other_token = get_token(args.other_site)
        first = second = None
        try:
            first = call('/api/resource/ToDo', 'POST', dict(description=marker), token)['data']['name']
            second = call('/api/resource/ToDo', 'POST', dict(description=marker + ' tenant B'), other_token, args.other_site)['data']['name']
            for wrong_token, site in ((token, args.other_site), (other_token, args.site)):
                try:
                    call('/api/resource/ToDo', token=wrong_token, site=site)
                    raise AssertionError('Foreign tenant token was accepted')
                except HTTPError as error:
                    assert error.code in (401, 403)
            try:
                call('/api/resource/ToDo/' + quote(first), token=other_token, site=args.other_site)
                raise AssertionError('Foreign tenant record was visible')
            except HTTPError as error:
                assert error.code == 404
            print('PASS actual cross-site API token rejection and database record isolation')
        finally:
            if first:
                call('/api/resource/ToDo/' + quote(first), 'DELETE', token=token)
            if second:
                call('/api/resource/ToDo/' + quote(second), 'DELETE', token=other_token, site=args.other_site)
    assert b'<!doctype html>' in call('/login').lower()
    print('PASS actual login frontend HTML')
    if args.attendance_race:
        assignments = call('/api/resource/PP%20Assignment?limit_page_length=1', token=token)['data']
        if not assignments:
            raise RuntimeError('Attendance race requires the labelled local demo seed')
        assignment = assignments[0]['name']
        barrier = Barrier(10)
        def post_attendance(_):
            barrier.wait(timeout=30)
            try:
                result = call('/api/resource/PP%20Work%20Entry', 'POST', dict(assignment=assignment,
                    work_date=str(date.today() + timedelta(days=1000)), units=1, status='Draft', remarks=marker), token)
                return result['data']['name']
            except HTTPError as error:
                return {'status': error.code}
            except Exception as error:
                return {'error': type(error).__name__}
        successes = []
        rejections = []
        try:
            with ThreadPoolExecutor(max_workers=10) as pool:
                for result in pool.map(post_attendance, range(10)):
                    if isinstance(result, str):
                        successes.append(result)
                    else:
                        rejections.append(result)
            assert len(successes) == 1, f'Expected exactly one attendance winner, got {len(successes)}'
            assert rejections == [{'status': 417}] * 9, f'Unexpected attendance errors: {rejections}'
            print('PASS actual simultaneous attendance writes: 1 created, 9 duplicates rejected')
        finally:
            for name in successes:
                call('/api/resource/PP%20Work%20Entry/' + quote(name), 'DELETE', token=token)
            print('PASS temporary draft attendance cleaned')
    def latency(_):
        start = time.perf_counter()
        assert call('/api/resource/PP%20Site?limit_page_length=20', token=token)['data'] is not None
        return (time.perf_counter() - start) * 1000
    with ThreadPoolExecutor(max_workers=5) as pool:
        times = sorted(pool.map(latency, range(60)))
    print(json.dumps(dict(authenticated_reads=60, concurrency=5, errors=0,
        median_ms=round(statistics.median(times), 1), p95_ms=round(times[56], 1), max_ms=round(max(times), 1))))


if __name__ == '__main__':
    main()
