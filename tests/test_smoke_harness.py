"""The API test harness exercised against a synthetic local HTTP fixture.

IMPORTANT: this validates the *test code*, NOT Frappe/ERPNext APIs.
"""
from __future__ import annotations

import importlib.util
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("api_smoke", SCRIPTS / "api_smoke.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class FakeFrappe(BaseHTTPRequestHandler):
    records = {}
    counter = 0

    def log_message(self, *_):  # Silence test HTTP traffic.
        pass

    def respond(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        if self.headers.get("Authorization") == "token testkey:testsecret":
            return True
        self.respond(401, {"error": "AuthenticationError"})
        return False

    def do_GET(self):
        route = urlsplit(self.path).path
        if route == "/api/method/ping":
            self.respond(200, {"message": "pong"})
        elif route.startswith("/api/resource/"):
            if not self.authorized():
                return
            if route == "/api/resource/Company":
                self.respond(200, {"data": []})
            elif route == "/api/resource/ToDo":
                self.respond(200, {"data": list(self.records.values())})
            elif route.startswith("/api/resource/ToDo/"):
                name = unquote(route.split("/")[-1])
                if name not in self.records:
                    self.respond(404, {"error": "Not found"})
                else:
                    self.respond(200, {"data": self.records[name]})
            else:
                self.respond(404, {"error": "Unknown"})
        else:
            self.respond(404, {"error": "Unknown"})

    def do_POST(self):
        if not self.authorized():
            return
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).counter += 1
        name = f"fake-{type(self).counter}"
        doc = {"name": name, **body}
        self.records[name] = doc
        self.respond(201, {"data": doc})

    def do_PUT(self):
        if not self.authorized():
            return
        name = unquote(urlsplit(self.path).path.split("/")[-1])
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.records[name].update(data)
        self.respond(200, {"data": self.records[name]})

    def do_DELETE(self):
        if not self.authorized():
            return
        name = unquote(urlsplit(self.path).path.split("/")[-1])
        self.records.pop(name, None)
        self.respond(200, {"data": "ok"})


class APITestHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeFrappe)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)
        cls.server.server_close()

    def test_crud_harness_and_cleanup(self):
        smoke.run(self.base, "testkey", "testsecret", True)
        self.assertFalse(FakeFrappe.records)

    def test_rejects_missing_credential_for_write(self):
        with self.assertRaises(RuntimeError):
            smoke.run(self.base, None, None, True)


if __name__ == "__main__":
    unittest.main()
