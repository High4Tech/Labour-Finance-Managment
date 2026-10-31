app_name = "plus_point"
app_title = "PLUS POINT"
app_publisher = "High4Tech"
app_description = "Event operations, crew and finance extension for ERPNext and Frappe HRMS"
app_email = "support@high4tech.com"
app_license = "MIT"
required_apps = ["frappe/erpnext", "frappe/hrms"]
# Receipts preserve source IDs and hashes after an unused target is deleted.
# They are audit references, not operational dependencies. Replay checks still
# reject a missing target; submitted documents and all other links stay guarded.
ignore_links_on_delete = ["PP Import Record"]
after_install = "plus_point.install.after_install"
after_migrate = "plus_point.install.after_migrate"
before_install = "plus_point.install.before_install"
extend_bootinfo = "plus_point.onboarding.boot_context"
web_include_js = ["/assets/plus_point/js/website.js?v=20261021-complete-forms-4"]
website_route_rules = [{"from_route":"/signup","to_route":"plans"}]
app_include_js = ["/assets/plus_point/js/choices.js?v=20261029-event-review-2","/assets/plus_point/js/icons.js?v=20261031-scene-demo-1","/assets/plus_point/js/runtime.js?v=20261029-upload-assets-2",
                  "/assets/plus_point/js/feedback.js?v=20261027-refinement-1","/assets/plus_point/js/appearance.js?v=20261028-echarts-2",
                  "/assets/plus_point/js/selectors.js?v=20261029-upload-assets-2",
                  "/assets/plus_point/js/forms.js?v=20261029-event-review-2",
                  "/assets/plus_point/js/attendance.js?v=20261023-finance-3",
                  "/assets/plus_point/js/worker_profile.js?v=20261029-upload-assets-2",
                  "/assets/plus_point/js/dashboard_motion.js?v=20261028-dashboard-final-1",
                  "/assets/plus_point/js/dashboard.js?v=20261028-dashboard-final-1",
                  "/assets/plus_point/js/activity.js?v=20261023-finance-3",
                  "/assets/plus_point/js/crew.js?v=20261027-ui-2",
                  "/assets/plus_point/js/events.js?v=20261027-refinement-1",
                  "/assets/plus_point/js/sections.js?v=20261027-consolidated-3",
                  "/assets/plus_point/js/conditions.js?v=20261021-complete-forms-4",
                  "/assets/plus_point/js/setup_flow.js?v=20261025-freddy-2",
                  "/assets/plus_point/js/event_setup.js?v=20261025-freddy-2",
                  "/assets/plus_point/js/onboarding.js?v=20261028-figma-parity-1"]
app_include_css = ["/assets/plus_point/css/onboarding.css?v=20261025-agreement-import-2",
                   "/assets/plus_point/css/events.css?v=20261021-complete-forms-4",
                   "/assets/plus_point/css/dashboard_motion.css?v=20261021-complete-forms-4",
                   "/assets/plus_point/css/interface.css?v=20261027-consolidated-3"]
app_include_css += ["/assets/plus_point/css/attendance.css?v=20261023-finance-3"]
app_include_js += ["/assets/plus_point/js/drafts.js?v=20261028-booking-controls-2",
                   "/assets/plus_point/js/daily_billing.js?v=20261029-table-controls-3"]
app_include_js += ["/assets/plus_point/js/agreement_profile.js?v=20261029-upload-assets-2", "/assets/plus_point/js/profiles.js?v=20261029-upload-assets-2", "/assets/plus_point/js/operations.js?v=20261031-scene-demo-1"]
app_include_css += ["/assets/plus_point/css/operations.css?v=20261031-scene-demo-1", "/assets/plus_point/css/feedback.css?v=20261027-ui-2"]
scheduler_events = {"cron":{"* * * * *":["plus_point.drafts.run_scheduled"],"*/15 * * * *":["plus_point.daily_billing.run_recurring"]},"hourly": ["plus_point.agreement_lifecycle.close_expired", "plus_point.support.purge_results", "plus_point.activation.purge_results", "plus_point.attendance.generate_today"]}
extend_doctype_class = {"Subscription": ["plus_point.subscription.DemoWorkspaceSubscription"]}

doc_events = {
    "Contract": {"validate":"plus_point.agreement_updates.protect_contract"},
    "PP Contract Terms": {"on_trash":"plus_point.signing.cleanup_unsigned"},
    "PP Milestone": {"on_update":["plus_point.operations.milestone_invoice","plus_point.signing.milestone_changed"]},
    "PP Assignment": {"after_insert":"plus_point.attendance.assignment_started","on_trash":"plus_point.attendance.release_unmarked_roster"},
    "Company": {"before_insert":"plus_point.workspace.prevent_extra_company","after_insert":"plus_point.workspace.company_created"},
    "Employee": {"validate":"plus_point.people.validate_worker"},
    "Vehicle": {"validate":"plus_point.events.validate_vehicle"},
    "Stock Reconciliation": {"before_submit":"plus_point.events.protect_stock_snapshot"},
    "Stock Entry": {"before_submit":"plus_point.events.protect_stock_issue"},
    "Journal Entry": {"before_cancel":"plus_point.benefits.protect_finance"},
    "Project": {"validate": "plus_point.budget.validate_project", "on_update":"plus_point.events.project_cancelled"},
    "Purchase Invoice": {"before_submit": "plus_point.budget.enforce", "before_update_after_submit": "plus_point.budget.enforce"},
    "Expense Claim": {"before_submit": "plus_point.budget.enforce", "before_update_after_submit": "plus_point.budget.enforce"},
    "Payment Entry": {"before_cancel": ["plus_point.plus_point.doctype.pp_wage_settlement.pp_wage_settlement.protect_payment","plus_point.benefits.protect_finance"]},
    "*": {
        "before_validate": ["plus_point.input_rules.validate_document","plus_point.workflows.protect_reference"],
        "before_insert": ["plus_point.tenancy.enforce_write","plus_point.workflows.before_insert"],
        "validate": "plus_point.tenancy.enforce_write",
        "on_trash": "plus_point.tenancy.enforce_write",
        "before_cancel": "plus_point.tenancy.enforce_write",
        "before_submit": "plus_point.tenancy.enforce_write",
        "before_update_after_submit": "plus_point.tenancy.enforce_write",
    },
    "Sales Invoice": {
        "validate": "plus_point.billing.validate_invoice",
        "on_submit": "plus_point.billing.on_submit",
        "on_cancel": "plus_point.billing.release_invoice",
        "on_trash": "plus_point.billing.release_invoice",
        "on_update": "plus_point.billing.reserve_invoice",
    }
}
permission_query_conditions={"PP Planning Draft":"plus_point.drafts.query","Company":"plus_point.workspace.company_query","Warehouse":"plus_point.workspace.warehouse_query","Vehicle":"plus_point.workspace.vehicle_query",
                             "PP Worker Loan":"plus_point.workspace.loan_query","PP Loan Recovery":"plus_point.workspace.recovery_query"}
has_permission={"PP Planning Draft":"plus_point.drafts.permission","Company":"plus_point.workspace.company_permission","Warehouse":"plus_point.workspace.resource_permission","Vehicle":"plus_point.workspace.resource_permission",
                "PP Worker Loan":"plus_point.workspace.resource_permission","PP Loan Recovery":"plus_point.workspace.resource_permission"}

# Existing Frappe Desk handles the frontend automatically; this adds an app entry.
app_home = "/desk/plus-point"
add_to_apps_screen = [
    {
        "name": "plus_point",
        "logo": "/assets/plus_point/images/plus-point.svg",
        "title": "PLUS POINT",
        "route": app_home,
        "sequence_id": 14,
    }
]

app_include_js += ["/assets/plus_point/js/event_pay.js?v=20261029-event-review-2"]
app_include_js += ["/assets/plus_point/js/experience.js?v=20261028-booking-controls-2"]
app_include_css += ["/assets/plus_point/css/experience.css?v=20261027-refinement-1"]

app_include_js += ["/assets/plus_point/js/record_actions.js?v=20261029-commercial-flow-3"]
app_include_css += ["/assets/plus_point/css/record_ui.css?v=20261028-figma-parity-1"]

app_include_js += ["/assets/plus_point/js/people.js?v=20261028-figma-parity-1"]
app_include_css += ["/assets/plus_point/css/people.css?v=20261027-consolidated-3"]

app_include_js += ["/assets/plus_point/js/worker_actions.js?v=20261028-booking-controls-2"]

app_include_js += ["/assets/plus_point/js/resources.js?v=20261029-table-controls-3"]
app_include_js += ["/assets/plus_point/js/finance_hub.js?v=20261027-consolidated-3"]
app_include_css += ["/assets/plus_point/css/finance_hub.css?v=20261023-finance-3"]
app_include_js += ["/assets/plus_point/js/business_reports.js?v=20261023-report-layout-2"]
app_include_css += ["/assets/plus_point/css/business_reports.css?v=20261023-report-layout-2"]

app_include_css += ["/assets/plus_point/css/agreement_profile.css?v=20261028-booking-controls-2"]

app_include_js += ["/assets/plus_point/js/event_profile.js?v=20261031-scene-demo-1"]
app_include_css += ["/assets/plus_point/css/event_profile.css?v=20261031-scene-demo-1"]

app_include_js += ["/assets/plus_point/js/planning_list.js?v=20261029-table-controls-3"]

app_include_js += ["/assets/plus_point/js/agreement_share.js?v=20261029-upload-assets-2"]

app_include_js += ["/assets/plus_point/js/design_assets.js?v=20261029-upload-assets-2"]
app_include_js += ["/assets/plus_point/js/ui_components.js?v=20261029-upload-assets-2"]
app_include_css += ["/assets/plus_point/css/ui_components.css?v=20261029-upload-assets-2"]
app_include_css += ["/assets/plus_point/css/upload_assets.css?v=20261029-upload-assets-2"]

app_include_js += ["/assets/plus_point/js/lazy_features.js?v=20261031-scene-demo-1"]
