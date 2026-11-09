"""React transports use the existing native validators, scope and rollback rules."""
import unittest
from unittest.mock import patch
import frappe
from frappe.utils import today, add_days
from plus_point.tests.test_hierarchy import HierarchyTests
from plus_point import event_interface, interface_choices, report_interface, finance_hub, operations


class ReactMigrationTests(unittest.TestCase):
    setUpClass = classmethod(HierarchyTests.setUpClass.__func__)
    tearDownClass = classmethod(HierarchyTests.tearDownClass.__func__)
    setUp = HierarchyTests.setUp
    tearDown = HierarchyTests.tearDown
    agreement = HierarchyTests.agreement
    event = HierarchyTests.event

    def test_requirement_bulk_update_uses_native_validation(self):
        name=self.event();doc=frappe.get_doc('PP Event Plan',name);key=doc.staffing[0].name
        event_interface.requirements(name,[key],{'workers_required':2})
        self.assertEqual(frappe.get_doc('PP Event Plan',name).staffing[0].workers_required,2)
        with self.assertRaises(frappe.ValidationError):
            event_interface.requirements(name,[key],{'end_date':add_days(today(),-1)})
        self.assertEqual(str(frappe.get_doc('PP Event Plan',name).staffing[0].end_date),str(add_days(today(),4)))

    def test_foreign_rows_and_protected_fields_are_rejected(self):
        name=self.event();key=frappe.get_doc('PP Event Plan',name).staffing[0].name
        for keys,values in [(['foreign'],{'workers_required':2}),([key,key],{'workers_required':2}),([key],{'project':'foreign'})]:
            with self.assertRaises(frappe.ValidationError):event_interface.requirements(name,keys,values)

    def test_assigned_role_cannot_be_removed(self):
        name=self.event();operations.auto_assign(name);key=frappe.get_doc('PP Event Plan',name).staffing[0].name
        with self.assertRaises(frappe.ValidationError):event_interface.requirements(name,[key],remove=1)
        self.assertEqual(len(frappe.get_doc('PP Event Plan',name).staffing),1)

    def test_last_role_removal_retains_native_minimum_requirement(self):
        name=self.event();key=frappe.get_doc('PP Event Plan',name).staffing[0].name
        with self.assertRaises(frappe.ValidationError):event_interface.requirements(name,[key],remove=1)
        self.assertTrue(frappe.db.exists('PP Event Plan',name))
        self.assertEqual(len(frappe.get_doc('PP Event Plan',name).staffing),1)

    def test_link_choices_are_bounded_scoped_and_do_not_accept_arbitrary_doctypes(self):
        self.event()
        rows=interface_choices.choices('Employee',company=self.f.company.name)
        self.assertIn(self.worker.name,[r['value'] for r in rows]);self.assertLessEqual(len(rows),40)
        self.assertEqual(interface_choices.choices('Employee'),[])
        with self.assertRaises(frappe.ValidationError):interface_choices.choices('User')

    def test_report_transport_forces_current_company(self):
        with patch('frappe.desk.query_report.run',return_value={'result':[]}) as native:
            report_interface.run('PLUS POINT Project Finances',{'view':'Financial results'})
            self.assertEqual(native.call_args.kwargs['filters']['company'],self.f.company.name)
        with self.assertRaises(frappe.ValidationError):report_interface.run('Stock Balance',{})
        with self.assertRaises(frappe.ValidationError):report_interface.run('PLUS POINT Project Finances',{'company':'foreign'})

    def test_loan_choices_use_current_company(self):
        people=finance_hub.loan_workers('Ayesha')
        self.assertIn(self.worker.name,[r.name for r in people])
        self.assertTrue(all(frappe.db.get_value('Employee',r.name,'company')==self.f.company.name for r in people))

    def test_mutation_checks_native_write_permission(self):
        name=self.event();key=frappe.get_doc('PP Event Plan',name).staffing[0].name
        with patch('frappe.model.document.Document.check_permission',side_effect=frappe.PermissionError):
            with self.assertRaises(frappe.PermissionError):event_interface.requirements(name,[key],{'workers_required':2})


def run():
    if frappe.local.site!='qa.localhost' or not frappe.conf.get('allow_tests') or getattr(frappe.local,'request',None):
        raise RuntimeError('Local QA operator only')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReactMigrationTests))
    if not result.wasSuccessful():raise RuntimeError('React migration transport regressions failed')
    return dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors))


def run_regressions():
    """Local operator only: commercial, staffing, attendance and accounting checks."""
    if frappe.local.site!='qa.localhost' or not frappe.conf.get('allow_tests') or getattr(frappe.local,'request',None):
        raise RuntimeError('Local QA operator only')
    import importlib
    modules=['test_hierarchy','test_agreement_architecture','test_consolidated_architecture',
        'test_event_controls','test_event_start','test_component_validation','test_full_workflow',
        'test_drafts','test_planning_list','test_payment_overview','test_dashboard_analytics',
        'test_finance_records','test_react_migration']
    suite=unittest.TestSuite()
    for name in modules:
        module=importlib.import_module('plus_point.tests.'+name)
        for item in vars(module).values():
            if isinstance(item,type) and issubclass(item,unittest.TestCase) and item.__module__==module.__name__:
                suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(item))
    previous_in_test=frappe.flags.in_test
    frappe.flags.in_test=True
    try:
        result=unittest.TextTestRunner(verbosity=1).run(suite)
    finally:
        frappe.flags.in_test=previous_in_test
    if not result.wasSuccessful():raise RuntimeError('Company business regression tests failed')
    return dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors))
