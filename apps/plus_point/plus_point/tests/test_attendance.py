"""Real register, roster, approval and worker-profile tests; every fixture rolls back."""
import unittest,uuid
import frappe
from frappe.utils import today,add_days
from plus_point import attendance,worker_profile
from plus_point.tests.test_operations import fixture,insert
from plus_point.api import project_summary


class AttendanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user('Administrator');cls.old=frappe.flags.get('pp_test_entitlement')
        frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
        frappe.db.savepoint('pp_attendance_suite');cls.f=fixture('Attendance QA '+uuid.uuid4().hex[:8])
        cls.people=[cls.f.employee]
        for name,rate in [('Ayesha Attendance QA',1000),('Sana Attendance QA',500)]:
            worker=insert('Employee',first_name=name,gender='Female',date_of_birth='1990-01-01',date_of_joining='2020-01-01',status='Active',company=cls.f.company.name)
            cls.people.append(worker)
            insert('PP Assignment',employee=worker.name,site=cls.f.site.name,project=cls.f.project.name,contract_terms=cls.f.terms.name,start_date=today(),wage_rate=rate,client_rate=1500)
    @classmethod
    def tearDownClass(cls):
        frappe.set_user('Administrator');frappe.db.rollback(save_point='pp_attendance_suite');frappe.flags.pp_test_entitlement=cls.old
    def setUp(self):frappe.set_user('Administrator');frappe.db.savepoint('pp_attendance_case')
    def tearDown(self):frappe.set_user('Administrator');frappe.db.rollback(save_point='pp_attendance_case')
    def prepare(self,day=None):return attendance.prepare(self.f.site.name,day or today(),self.f.project.name)['name']
    def marks(self,name,states=None):
        states=states or {self.people[0].name:'Present',self.people[1].name:'Half day',self.people[2].name:'Absent'}
        return [dict(id=r['id'],status=states.get(r['employee'],'Absent')) for r in attendance.detail(name)['rows']]
    def plan(self,start=None,end=None):
        start=start or today();end=end or add_days(start,2)
        return insert('PP Event Plan',event_name='Attendance event',project=self.f.project.name,company=self.f.company.name,
            contract_terms=self.f.terms.name,start_date=start,end_date=end,wage_rate=2000,client_rate=3000,
            staffing=[dict(site=self.f.site.name,phase='Event',start_date=start,end_date=end,workers_required=3)])

    def test_generation_is_idempotent_unmarked_and_has_no_financial_effect(self):
        name=self.prepare();self.assertEqual(name,self.prepare())
        detail=attendance.detail(name);self.assertEqual(len(detail['rows']),3)
        self.assertTrue(all(r['status']=='Not marked' for r in detail['rows']))
        self.assertEqual(project_summary(self.f.project.name)['labour_cost'],'0.00')
        self.assertEqual(frappe.db.count('PP Work Entry',{'project':self.f.project.name}),0)

    def test_daily_generation_and_active_site_phases(self):
        self.plan();self.assertEqual(attendance.ensure_today(self.f.company.name)['created'],1)
        self.assertEqual(attendance.ensure_today(self.f.company.name)['created'],0)
        self.assertEqual(len(attendance.detail(self.prepare())['rows']),3)

    def test_future_phase_does_not_create_today_or_approve_early(self):
        self.plan(start=add_days(today(),1),end=add_days(today(),2))
        self.assertEqual(attendance.ensure_today(self.f.company.name)['created'],0)
        name=self.prepare(add_days(today(),1))
        with self.assertRaises(frappe.ValidationError):attendance.save_marks(name,self.marks(name),approve=1)
        self.assertEqual(frappe.db.count('PP Work Entry',{'project':self.f.project.name}),0)

    def test_present_half_and_absent_update_finances_only_after_approval(self):
        name=self.prepare();marks=self.marks(name)
        attendance.save_marks(name,marks)
        self.assertEqual(project_summary(self.f.project.name)['labour_cost'],'0.00')
        attendance.save_marks(name,marks,approve=1)
        totals=project_summary(self.f.project.name)
        self.assertEqual(totals['labour_cost'],'2500.00');self.assertEqual(totals['earned_revenue'],'3750.00')
        rows=frappe.get_all('PP Work Entry',filters={'project':self.f.project.name},fields=['units','wage_amount'])
        self.assertEqual(len(rows),3);self.assertEqual(sorted(float(r.units) for r in rows),[0,.5,1])
        with self.assertRaises(frappe.ValidationError):attendance.save_marks(name,marks,approve=1)
        self.assertEqual(frappe.db.count('PP Work Entry',{'project':self.f.project.name}),3)

    def test_unmarked_approval_and_forged_line_ids_are_refused(self):
        name=self.prepare();marks=self.marks(name);marks[0]['status']='Not marked'
        with self.assertRaises(frappe.ValidationError):attendance.save_marks(name,marks,approve=1)
        marks[0]['id']='another-register-line'
        with self.assertRaises(frappe.ValidationError):attendance.save_marks(name,marks)
        self.assertFalse(attendance.detail(name)['approved'])

    def test_budget_failure_rolls_back_marks_and_all_wages(self):
        name=self.prepare();project=frappe.get_doc('Project',self.f.project.name);project.update(dict(estimated_costing=1000,pp_enforce_spending_budget=1));project.save()
        with self.assertRaises(frappe.ValidationError):attendance.save_marks(name,self.marks(name),approve=1)
        self.assertEqual(frappe.db.count('PP Work Entry',{'project':self.f.project.name}),0)
        self.assertTrue(all(r['status']=='Not marked' for r in attendance.detail(name)['rows']))

    def test_manual_approved_work_is_reused_without_double_wages_or_budget(self):
        work=insert('PP Work Entry',assignment=self.f.assignment.name,work_date=today(),units=.5,status='Draft');work.status='Approved';work.save()
        project=frappe.get_doc('Project',self.f.project.name);project.update(dict(estimated_costing=1000,pp_enforce_spending_budget=1));project.save()
        name=self.prepare();rows=attendance.detail(name)['rows'];row=next(r for r in rows if r['employee']==self.f.employee.name)
        self.assertTrue(row['locked']);self.assertEqual(row['status'],'Half day')
        marks=self.marks(name,{self.f.employee.name:'Half day'})
        attendance.save_marks(name,marks,approve=1)
        self.assertEqual(project_summary(self.f.project.name)['labour_cost'],'1000.00')
        self.assertEqual(frappe.db.count('PP Work Entry',{'assignment':self.f.assignment.name}),1)

    def test_roster_refresh_preserves_saved_marks_and_adds_only_allocated_people(self):
        name=self.prepare();attendance.save_marks(name,self.marks(name))
        worker=insert('Employee',first_name='New Attendance Crew',gender='Female',date_of_birth='1990-01-01',date_of_joining='2020-01-01',status='Active',company=self.f.company.name)
        insert('PP Assignment',employee=worker.name,site=self.f.site.name,project=self.f.project.name,contract_terms=self.f.terms.name,start_date=today(),wage_rate=300,client_rate=500)
        attendance.refresh_roster(name);rows=attendance.detail(name)['rows']
        self.assertEqual(len(rows),4);self.assertEqual(next(r for r in rows if r['employee']==worker.name)['status'],'Not marked')
        self.assertEqual(next(r for r in rows if r['employee']==self.f.employee.name)['status'],'Present')

    def test_profile_uses_approved_attendance_and_exposes_unmarked_days_separately(self):
        name=self.prepare();attendance.save_marks(name,self.marks(name))
        before=worker_profile.overview(self.f.employee.name);self.assertEqual(before['full_days'],0);self.assertEqual(before['earned'],'0.00')
        self.assertEqual(before['calendar'][-1]['status'],'Pending approval')
        attendance.save_marks(name,self.marks(name),approve=1)
        present=worker_profile.overview(self.people[0].name);half=worker_profile.overview(self.people[1].name);absent=worker_profile.overview(self.people[2].name)
        self.assertEqual(present['full_days'],1);self.assertEqual(present['earned'],'2000.00');self.assertEqual(present['outstanding'],'2000.00')
        self.assertEqual(half['half_days'],1);self.assertEqual(half['paid_days'],'0.5');self.assertEqual(half['earned'],'500.00')
        self.assertEqual(absent['absent_days'],1);self.assertEqual(absent['earned'],'0.00')
        self.assertEqual(len(worker_profile.overview(self.f.employee.name,366)['calendar']),366)
        self.assertTrue(any(day['status']=='No scheduled work' for day in present['calendar']))

    def test_wrong_event_and_unauthorized_access_are_refused(self):
        with self.assertRaises(frappe.ValidationError):attendance.prepare(self.f.site.name,today(),'another-event')
        frappe.set_user('Guest')
        for call in (lambda:worker_profile.overview(self.f.employee.name),lambda:attendance.ensure_today(self.f.company.name),lambda:self.prepare()):
            with self.assertRaises(frappe.PermissionError):call()

    def test_cannot_drop_an_allocated_worker_to_bypass_marking(self):
        name=self.prepare();doc=frappe.get_doc('PP Daily Register',name)
        for line in doc.entries:line.attendance_status='Present';line.units='1'
        doc.remove(doc.entries[-1])
        with self.assertRaises(frappe.ValidationError):doc.submit()
        self.assertEqual(frappe.db.count('PP Work Entry',{'project':self.f.project.name}),0)

    def test_unused_allocation_can_be_released_from_generated_roster(self):
        name=self.prepare()
        target=next(r for r in frappe.get_doc('PP Daily Register',name).entries if r.employee==self.people[2].name)
        frappe.delete_doc('PP Assignment',target.assignment)
        self.assertEqual(len(attendance.detail(name)['rows']),2)
