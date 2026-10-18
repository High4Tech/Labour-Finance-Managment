"""Keep the local app and platform worker attached to the Docker lifecycle."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.request import Request, urlopen

BENCH = Path('/home/frappe/frappe-bench')
READY = BENCH / 'sites/.plus-point-ready'


def healthcheck():
    request = Request('http://127.0.0.1:8000/api/method/ping',
                      headers={'Host': os.environ.get('LOCAL_SITE', 'demo.localhost')})
    try:
        with urlopen(request, timeout=3) as response:
            return 0 if json.load(response).get('message') == 'pong' else 1
    except Exception:
        return 1


def main():
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print('Waiting for local setup to finish. On first use, run START_PLUS_POINT_DEV.cmd.', flush=True)
    while not stopping and not READY.exists():
        time.sleep(0.5)
    if stopping:
        return 0

    children, logs = [], []
    try:
        for name, command in (
            ('bench-start', ['bench', 'start', '-c', 'watch=0']),
            ('platform-worker', [sys.executable, '/workspace/scripts/platform-worker.py']),
        ):
            log = (BENCH / f'logs/{name}.log').open('a')
            logs.append(log)
            children.append(subprocess.Popen(command, cwd=BENCH, stdout=log,
                                              stderr=subprocess.STDOUT, start_new_session=True))
        print('PLUS POINT app and platform worker started.', flush=True)
        while not stopping:
            if any(child.poll() is not None for child in children):
                print('An app process stopped; Docker will restart the local app.', flush=True)
                return 1
            time.sleep(0.5)
        return 0
    finally:
        # Stop both process groups, including queue/server children, before exit.
        for child in children:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + 8
        for child in children:
            try:
                child.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
        for log in logs:
            log.close()


if __name__ == '__main__':
    sys.exit(healthcheck() if '--healthcheck' in sys.argv else main())
