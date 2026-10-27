no_cache=1
no_sitemap=1
def get_context(context):
    context.no_cache=1
    # A company user may open a client link in their existing Desk session.
    # Keep the native request protection for acceptance instead of disabling CSRF.
    from frappe.sessions import get_csrf_token
    context.csrf_token=get_csrf_token()
