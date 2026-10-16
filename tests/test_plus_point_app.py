import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'apps'/'plus_point'/'plus_point'
DT=APP/'plus_point'/'doctype'


class PPAppTests(unittest.TestCase):
    def test_frappe_app_skeleton(self):
        for fn in ['__init__.py','hooks.py','modules.txt','finance.py','api.py']:
            self.assertTrue((APP/fn).is_file(),fn)
        self.assertEqual((APP/'modules.txt').read_text().strip(),'PLUS POINT')

    def test_valid_native_frappe_doctypes(self):
        for folder in ('pp_contract_terms','pp_site','pp_assignment','pp_work_entry','pp_milestone','pp_daily_register','pp_register_line'):
            path=DT/folder/(folder+'.json')
            doc=json.loads(path.read_text())
            self.assertEqual(doc['doctype'],'DocType')
            self.assertEqual(doc['module'],'PLUS POINT')
            self.assertEqual(len(doc['fields']),len(doc['field_order']))
            self.assertTrue((DT/folder/(folder+'.py')).is_file())
            if not doc.get('istable'):
                self.assertTrue(any(x['role']=='System Manager' for x in doc['permissions']))

    def test_bulk_register_uses_native_submittable_desk(self):
        register=json.loads((DT/'pp_daily_register'/'pp_daily_register.json').read_text())
        lines=json.loads((DT/'pp_register_line'/'pp_register_line.json').read_text())
        self.assertEqual(register['is_submittable'],1)
        self.assertEqual(lines['istable'],1)
        self.assertIn('PP Register Line',[f.get('options') for f in register['fields']])

    def test_only_domain_gaps_not_reimplement_erp(self):
        contents=' '.join(x.name for x in DT.iterdir())
        for forbidden in ('customer','employee','project','sales_invoice','payment_entry','contract'):
            self.assertNotIn('pp_'+forbidden+' ',contents+' ')


if __name__=='__main__': unittest.main()
