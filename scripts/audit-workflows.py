"""Rollback-only local QA runner with per-case audit evidence on stdout."""
import json
import sys
import time
import unittest

import frappe


class AuditResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.evidence={};self.started={}

    def entry(self,test):
        return self.evidence.setdefault(test.id(),dict(test=test.id(),status='running',details=''))

    def startTest(self,test):
        super().startTest(test);self.started[test.id()]=time.monotonic();self.entry(test)

    def stopTest(self,test):
        self.entry(test)['seconds']=round(time.monotonic()-self.started.get(test.id(),time.monotonic()),3)
        super().stopTest(test)

    def addSuccess(self,test):
        self.entry(test)['status']='passed';super().addSuccess(test)

    def addFailure(self,test,err):
        self.entry(test).update(status='failed',details=self._exc_info_to_string(err,test));super().addFailure(test,err)

    def addError(self,test,err):
        self.entry(test).update(status='error',details=self._exc_info_to_string(err,test));super().addError(test,err)

    def addSkip(self,test,reason):
        self.entry(test).update(status='skipped',details=reason);super().addSkip(test,reason)

    def addSubTest(self,test,subtest,err):
        if err:self.entry(test).update(status='failed',details=self._exc_info_to_string(err,test))
        super().addSubTest(test,subtest,err)


def main():
    site=sys.argv[1] if len(sys.argv)>1 else 'qa.localhost'
    if site not in ('qa.localhost','platform.localhost'):raise RuntimeError('Only local test sites are allowed')
    frappe.init(site=site);frappe.connect()
    if not frappe.conf.get('allow_tests'):raise RuntimeError('Tests must be enabled')
    frappe.flags.in_test=True
    names=['test_signup'] if site=='platform.localhost' else ['test_finance','test_register','test_operations','test_events','test_attendance','test_currency_billing','test_forms','test_hierarchy','test_setup_imports','test_full_workflow','test_component_validation','test_planning','test_drafts']
    if '--journey' in sys.argv:names=['test_full_workflow']
    if '--components' in sys.argv:names=['test_component_validation']
    if '--draft-repairs' in sys.argv:names=['test_hierarchy','test_drafts']
    if '--drafts' in sys.argv:names=['test_drafts']
    if '--inline-drafts' in sys.argv:names=['test_planning_list','test_drafts']
    if '--event-start' in sys.argv:names=['test_event_start','test_drafts','test_planning_list']
    if '--release-controls' in sys.argv:names=['test_agreement_sharing','test_event_controls','test_hierarchy','test_component_validation','test_event_start','test_drafts','test_planning_list','test_full_workflow','test_planning','test_profiles_billing']
    if '--event-controls' in sys.argv:names=['test_event_controls','test_event_start','test_drafts','test_planning_list']
    if '--sharing-regression' in sys.argv:names=['test_agreement_sharing','test_hierarchy','test_component_validation','test_event_start','test_drafts','test_planning_list','test_full_workflow']
    if '--sharing-only' in sys.argv:names=['test_agreement_sharing']
    if '--sharing' in sys.argv:names=['test_agreement_sharing','test_planning','test_profiles_billing']
    if '--ui-stability' in sys.argv:names=['test_component_validation','test_event_start','test_drafts','test_planning_list']
    if '--planning' in sys.argv:names=['test_planning']
    if '--profiles' in sys.argv:names=['test_profiles_billing','test_drafts','test_hierarchy','test_component_validation']
    if '--planning-repairs' in sys.argv:names=['test_setup_imports','test_planning','test_attendance']
    started=time.monotonic()
    try:
        suite=unittest.defaultTestLoader.loadTestsFromNames(['plus_point.tests.'+name for name in names])
        result=unittest.TextTestRunner(verbosity=1,resultclass=AuditResult).run(suite)
        evidence=dict(site=site,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),seconds=round(time.monotonic()-started,3),cases=list(result.evidence.values()))
    finally:
        frappe.db.rollback();frappe.destroy()
    print('AUDIT_RESULT='+json.dumps(evidence,default=str))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':sys.exit(main())
