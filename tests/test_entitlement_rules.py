import importlib.util
from pathlib import Path
import sys
import types
import unittest
from datetime import date
from unittest.mock import patch


class EntitlementRules(unittest.TestCase):
    def test_status_boundaries(self):
        fake = types.ModuleType('frappe')
        fake.whitelist = lambda *a, **k: lambda fn: fn
        utils = types.ModuleType('frappe.utils')
        utils.getdate = date.today
        with patch.dict(sys.modules, {'frappe': fake, 'frappe.utils': utils}):
            path = Path(__file__).resolve().parents[1] / 'apps/plus_point/plus_point/tenancy.py'
            spec = importlib.util.spec_from_file_location('pp_entitlement_unit', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        self.assertEqual(module.entitlement_status({}), 'Development')
        self.assertEqual(module.entitlement_status({'suspended': True}), 'Suspended')
        self.assertEqual(module.entitlement_status({'limits': {}}), 'Expired')
        self.assertEqual(module.entitlement_status({'valid_until': '2026-10-16'}, date(2026, 10, 16)), 'Active')
        self.assertEqual(module.entitlement_status({'valid_until': '2026-10-16'}, date(2026, 10, 17)), 'Expired')
