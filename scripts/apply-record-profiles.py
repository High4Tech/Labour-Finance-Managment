"""Local operator update: sync jobs and close expired agreements, without posting invoices."""
import json,sys
import frappe


def main():
    site=sys.argv[1] if len(sys.argv)==2 else ''
    if site not in ('qa.localhost','demo.localhost','high4tech-events-fd166a217c.localhost'):
        raise RuntimeError('Choose an existing local company app site.')
    frappe.init(site=site);frappe.connect()
    try:
        frappe.set_user('Administrator');frappe.clear_cache()
        from plus_point.imports import check_installation
        check_installation('agreements')
        from frappe.core.doctype.scheduled_job_type.scheduled_job_type import sync_jobs
        sync_jobs()
        from plus_point.agreement_lifecycle import close_expired
        closed=close_expired()
        jobs=frappe.get_all('Scheduled Job Type',filters={'method':['in',['plus_point.daily_billing.run_recurring','plus_point.agreement_lifecycle.close_expired']]},fields=['method','frequency','cron_format','stopped'])
        if len(jobs)!=2 or any(job.stopped for job in jobs):raise RuntimeError('The agreement jobs were not registered correctly.')
        frappe.clear_cache();frappe.db.commit()
        print(json.dumps(dict(site=site,expired_agreements_closed=closed,jobs=jobs,scheduler_enabled=bool(frappe.db.get_single_value('System Settings','enable_scheduler')),scheduler_paused=bool(frappe.conf.get('pause_scheduler')),financial_postings_created=False)))
    except Exception:frappe.db.rollback();raise
    finally:frappe.destroy()


if __name__=='__main__':main()
