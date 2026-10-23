"""Cross-screen lifecycle audits. Every company, stock and ledger row rolls back."""
import unittest
import uuid
from decimal import Decimal
from unittest.mock import patch

import frappe
from frappe.utils import add_days, today
from plus_point import attendance, benefits, billing, operations, record_actions, resources
from plus_point.api import project_summary
from plus_point.tests.test_operations import fixture, insert


class FullWorkflowTests(unittest.TestCase):
    def setUp(self):
        frappe.set_user('Administrator');self.previous=frappe.flags.get('pp_test_entitlement');frappe.flags.pp_test_entitlement={'valid_until':'2099-12-31'}
        frappe.db.savepoint('pp_full_workflow');self.f=fixture('Full workflow QA '+uuid.uuid4().hex[:7])
        frappe.delete_doc('PP Assignment',self.f.assignment.name)
        self.scope=patch('plus_point.event_setup.companies',return_value=[self.f.company]);self.scope.start()

    def tearDown(self):
        frappe.set_user('Administrator');self.scope.stop();frappe.db.rollback(save_point='pp_full_workflow');frappe.flags.pp_test_entitlement=self.previous;frappe.clear_cache()

    def worker(self,person=None,**settings):
        worker=frappe.get_doc('Employee',person) if person else insert('Employee',first_name='Second journey worker',gender='Female',date_of_birth='1990-01-01',date_of_joining='2020-01-01',company=self.f.company.name,status='Active')
        worker.designation='Event crew';worker.pp_salary_basis='Daily';worker.pp_salary_amount=200;worker.pp_leaves_per_month=2
        worker.update(settings);worker.save();return worker

    def agreement(self,quantity=1,fixed=False,title='Complete lifecycle'):
        first=add_days(today(),-2);last=today()
        return operations.save_agreement(dict(customer=self.f.customer.name,agreement_title=title,scope='Crew, transport and equipment',allow_past_dates=1,billing_model='Fixed' if fixed else 'Daily',agreement_currency='PKR',fixed_amount=1000 if fixed else 0,status='Active',effective_start=first,effective_end=last,auto_invoice=0,staffing=[dict(site_name='Main stage',designation='Event crew',phase='Event',start_date=first,end_date=last,workers_required=quantity,wage_rate=200,client_rate=0 if fixed else 350)],transport_requirements=[dict(vehicle_type='Crew van',quantity=1,site_name='Main stage',start_date=first,end_date=last)]))

    def payment(self,worker,amount,account,project=None):
        doc=insert('Payment Entry',payment_type='Pay',company=self.f.company.name,party_type='Employee',party=worker,project=project,paid_from=self.f.company.default_cash_account,paid_to=account,paid_amount=amount,received_amount=amount,source_exchange_rate=1,target_exchange_rate=1,reference_no='Full lifecycle audit',reference_date=today());doc.submit();return doc

    def test_three_days_attendance_leave_loan_billing_receipts_and_reports(self):
        alice=self.worker(self.f.employee.name,pp_salary_basis='Monthly',pp_salary_amount=6000,pp_loan_allowed=1,pp_loan_wait_months=0,pp_loan_deduction_percent=25)
        bob=self.worker();agreement=self.agreement(2);plan=operations.create_plan(agreement['name'],'Three-day audit event')['name']
        self.assertEqual(operations.auto_assign(plan)['created'],2)
        site=operations.agreement(agreement['name'])['venues'][0].name
        days=[add_days(today(),-2),add_days(today(),-1),today()]
        benefits.grant_leave(alice.name,days[1],'Full day','Approved full leave')
        benefits.grant_leave(alice.name,days[2],'Half day','Approved half leave')
        registers=[]
        for day,states in zip(days,[{alice.name:'Present',bob.name:'Half day'},{alice.name:'Absent',bob.name:'Present'},{alice.name:'Half day',bob.name:'Absent'}]):
            name=attendance.prepare(site,day,agreement['project'])['name'];registers.append(name)
            marks=[dict(id=row['id'],status=states[row['employee']]) for row in attendance.detail(name)['rows']]
            before=project_summary(agreement['project'])['labour_cost'];attendance.save_marks(name,marks,approve=False)
            self.assertEqual(project_summary(agreement['project'])['labour_cost'],before,'Draft attendance must not create wages')
            attendance.save_marks(name,marks,approve=True)
            self.assertEqual(attendance.prepare(site,day,agreement['project'])['name'],name)
        totals=project_summary(agreement['project']);self.assertEqual(totals['labour_cost'],'600.00');self.assertEqual(totals['earned_revenue'],'1050.00')
        advance=self.payment(alice.name,500,self.f.company.default_receivable_account)
        loan=benefits.grant_loan(alice.name,500,25,today(),'Audited advance',advance.name)
        self.assertEqual(benefits.balances(alice.name)['proposed_deduction'],'75.00')
        recovery=benefits.apply_deduction(loan['name'],agreement['project'],today());self.assertEqual(recovery['amount'],'75.00')
        wages=self.payment(alice.name,225,self.f.company.default_payable_account,agreement['project'])
        insert('PP Wage Settlement',employee=alice.name,project=agreement['project'],payment_entry=wages.name).submit()
        self.assertEqual(benefits.balances(alice.name)['loan_outstanding'],'425.00')
        self.assertEqual(Decimal(benefits.balances(alice.name)['monthly_after_deduction']),0)
        invoice=frappe.get_doc('Sales Invoice',billing.create_invoice(agreement['name'])['name']);invoice.submit()
        self.assertEqual(Decimal(str(invoice.grand_total)),1050)
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
        for amount in [400,650]:
            payment=get_payment_entry('Sales Invoice',invoice.name,bank_account=self.f.company.default_cash_account)
            payment.project=agreement['project'];payment.paid_amount=amount;payment.received_amount=amount;payment.references[0].allocated_amount=amount;payment.reference_no='Audited receipt';payment.reference_date=today();payment.insert();payment.submit()
        supplier=insert('Supplier',supplier_name='Journey supplier '+uuid.uuid4().hex[:5],supplier_group='All Supplier Groups',supplier_type='Company')
        expense=insert('Purchase Invoice',company=self.f.company.name,supplier=supplier.name,project=agreement['project'],items=[dict(item_code=self.f.item.name,qty=1,rate=100,project=agreement['project'],expense_account=self.f.company.default_expense_account,cost_center=self.f.company.cost_center)]);expense.submit()
        totals=project_summary(agreement['project'])
        for key,value in dict(earned_revenue='1050.00',labour_cost='600.00',cash_collected_gross='1050.00',client_outstanding_gross='0.00',wages_paid='225.00',loan_recoveries='75.00',wages_outstanding='300.00',other_project_costs='100.00',operational_profit='350.00').items():
            with self.subTest(total=key):self.assertEqual(totals[key],value)
        from plus_point.reporting import worker_statement_report
        from plus_point.worker_profile import overview
        statement=worker_statement_report(dict(company=self.f.company.name,employee=alice.name,project=agreement['project']))
        with self.subTest(stage='Worker statement reconciles cash and recovery'):self.assertEqual(Decimal(str(statement[1][-1]['balance'])),0)
        profile=overview(alice.name)
        with self.subTest(stage='Worker profile reconciles cash and recovery'):self.assertEqual(profile['outstanding_after_loan'],'0.00')
        with self.subTest(stage='Full day leave remains visible after attendance approval'):
            self.assertEqual(next(row['status'] for row in profile['calendar'] if row['date']==str(days[1])),'Full day leave')
        for dt,name in [('Sales Invoice',invoice.name),('PP Daily Register',registers[0]),('Employee',alice.name),('PP Contract Terms',agreement['name'])]:
            with self.subTest(stage='Protected history',doctype=dt):
                self.assertTrue(record_actions.review(dt,name)['blocked'])
                with self.assertRaises((frappe.ValidationError,frappe.LinkExistsError)):record_actions.remove(dt,name)

    def test_resources_edits_deletion_and_availability_propagate(self):
        self.worker(self.f.employee.name);agreement=self.agreement();plan=operations.create_plan(agreement['name'],'Resource audit')['name'];site=operations.agreement(agreement['name'])['venues'][0].name
        vehicle=insert('Vehicle',license_plate='AUDIT-'+uuid.uuid4().hex[:8],make='Toyota',model='Van',company=self.f.company.name,fuel_type='Diesel',uom='Litre',last_odometer=0,pp_crew_seats=4,pp_cargo_capacity=0,pp_cargo_uom='units',pp_event_enabled=1)
        booking=resources.save_booking(agreement['project'],'vehicle',dict(vehicle=vehicle.name,site=site,start_date=today(),end_date=today(),purpose='Crew',crew_count=1,status='Planned'))
        self.assertEqual(resources.list_states('vehicles',[vehicle.name])[0]['availability'],'Assigned')
        record_actions.remove('PP Vehicle Booking',booking['name'])
        self.assertEqual(resources.list_states('vehicles',[vehicle.name])[0]['availability'],'Available')
        record_actions.remove('Vehicle',vehicle.name);self.assertEqual(resources.list_states('vehicles',[vehicle.name]),[])
        warehouse=frappe.db.get_value('Warehouse',{'company':self.f.company.name,'is_group':0},'name')
        item=insert('Item',item_code='AUDIT-STOCK-'+uuid.uuid4().hex[:8],item_name='Audit barriers',item_group='Services',stock_uom='Nos',is_stock_item=1)
        resources.count_stock(warehouse,item.name,10,50,today())
        reservation=resources.save_booking(agreement['project'],'equipment',dict(site=site,warehouse=warehouse,item=item.name,quantity=4,start_date=today(),end_date=today(),status='Planned'))
        current=next(row for row in resources.warehouse_stock(warehouse) if row['name']==item.name);self.assertEqual(current['available'],6)
        with self.assertRaises(frappe.ValidationError):resources.update_stock(warehouse,[dict(item=item.name,quantity=3,expected_quantity=10)])
        record_actions.remove('PP Equipment Booking',reservation['name'])
        current=next(row for row in resources.warehouse_stock(warehouse) if row['name']==item.name);self.assertEqual(current['available'],10)
        with self.assertRaises((frappe.ValidationError,frappe.LinkExistsError)):record_actions.remove('Item',item.name)
        operations.auto_assign(plan);assignment=frappe.db.get_value('PP Assignment',{'project':agreement['project']},'name')
        record_actions.remove('PP Assignment',assignment)
        from plus_point.worker_profile import overview
        with self.subTest(stage='Worker available after allocation deletion'):self.assertEqual(overview(self.f.employee.name)['allocation_status'],'Available')
        with self.subTest(stage='Event coverage resets after allocation deletion'):self.assertEqual(operations.plan(plan)['allocations'],[])
        record_actions.remove('PP Event Plan',plan);self.assertNotIn(plan,[row.name for row in operations.catalogue()['plans']])
