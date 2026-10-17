app_name = "plus_point"
app_title = "PLUS POINT"
app_publisher = "High4Tech"
app_description = "Labour contracting extension for ERPNext and Frappe HRMS"
app_email = "support@high4tech.com"
app_license = "MIT"
required_apps = ["frappe/erpnext", "frappe/hrms"]
after_install = "plus_point.install.after_install"
after_migrate = "plus_point.install.after_migrate"
before_install = "plus_point.install.before_install"
extend_bootinfo = "plus_point.onboarding.boot_context"
app_include_js = ["/assets/plus_point/js/dashboard.js?v=20261017-activity-1",
                  "/assets/plus_point/js/activity.js?v=20261017-activity-1",
                  "/assets/plus_point/js/sections.js?v=20261017-activity-1",
                  "/assets/plus_point/js/conditions.js?v=20261017-activity-1",
                  "/assets/plus_point/js/imports.js?v=20261017-activity-1",
                  "/assets/plus_point/js/setup_flow.js?v=20261017-activity-1",
                  "/assets/plus_point/js/onboarding.js?v=20261017-activity-1"]
app_include_css = "/assets/plus_point/css/onboarding.css?v=20261017-activity-1"
scheduler_events = {"hourly": ["plus_point.support.purge_results"]}

doc_events = {
    "Project": {"validate": "plus_point.budget.validate_project"},
    "Purchase Invoice": {"before_submit": "plus_point.budget.enforce", "before_update_after_submit": "plus_point.budget.enforce"},
    "Expense Claim": {"before_submit": "plus_point.budget.enforce", "before_update_after_submit": "plus_point.budget.enforce"},
    "Payment Entry": {"before_cancel": "plus_point.plus_point.doctype.pp_wage_settlement.pp_wage_settlement.protect_payment"},
    "*": {
        "before_insert": "plus_point.tenancy.enforce_write",
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
