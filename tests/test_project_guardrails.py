"""Offline tests of the starter's static architecture and simple statistics helpers.

These do NOT test Frappe/ERPNext/HRMS. Run scripts/api_smoke.py and
scripts/load_test.py after local Docker installation for integration evidence.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StarterGuardrails(unittest.TestCase):
    def test_required_artifacts_exist(self):
        for item in ["MVP_ARCHITECTURE.md", "LOCAL_RUNBOOK.md", "TEST_PLAN.md",
                     "scripts/bootstrap-local.sh", "scripts/create-tenant.sh",
                     "scripts/api_smoke.py", "scripts/load_test.py", ".env.example", ".gitignore"]:
            with self.subTest(item=item):
                self.assertTrue((ROOT / item).exists(), item)

    def test_doc_identifies_both_billing_methods(self):
        architecture = (ROOT / "MVP_ARCHITECTURE.md").read_text()
        for wording in ["per worker-day", "fixed price", "site", "subscription", "isolated", "read-only", "milestone"]:
            with self.subTest(wording=wording):
                self.assertIn(wording, architecture)

    def test_live_tenant_data_is_gitignored(self):
        ignored = (ROOT / ".gitignore").read_text()
        for fragment in [".local/", ".env", "site_config.json", "private/", "backups/"]:
            self.assertIn(fragment, ignored)

    def test_load_percentiles(self):
        spec = importlib.util.spec_from_file_location("pp_load", ROOT / "scripts" / "load_test.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.percentile([1, 2, 3, 4, 5], 50), 3)
        self.assertEqual(module.percentile([1, 2, 3, 4, 5], 100), 5)
        self.assertEqual(module.percentile([1, 2, 3, 4, 5], 0), 1)


if __name__ == "__main__":
    unittest.main()
