"""Small Desk context; guidance never changes document access or business records."""
import frappe


def boot_context(bootinfo):
    platform = bool(frappe.conf.get('pp_control_plane'))
    from plus_point.navigation import product_navigation
    navigation = product_navigation(platform)
    bootinfo.plus_point = {
        'is_platform': platform,
        'home': '/desk/high4tech' if platform else '/desk/plus-point',
        'navigation': navigation,
    }
    companies=frappe.get_list('Company',fields=['name','company_name'],order_by='name',limit_page_length=0)
    default=frappe.defaults.get_user_default('Company')
    identity=next((row for row in companies if row.name==default),companies[0] if companies else None)
    bootinfo.plus_point['company_identity']=dict(name=identity.name,title=identity.company_name) if identity else dict(name=None,title='High4Tech' if platform else frappe.conf.get('pp_signup_company') or 'Your event company')
    bootinfo.plus_point['signup_company_name']=frappe.conf.get('pp_signup_company') or ''
    # One product entry per site. Retain every engine's route/dock metadata for
    # native forms and workspaces; only their separate launcher entries change.
    for app in bootinfo.get('app_data', []):
        if app.get('app_name') == 'plus_point':
            if platform:
                app.update(app_title='High4Tech admin', app_route='/desk/high4tech')
        else:
            app['on_apps_screen'] = False
            app['dock'] = []
    sidebar = dict((bootinfo.get('module_sidebars') or {}).get('PLUS POINT') or {})
    sidebar.update(label='High4Tech admin' if platform else 'PLUS POINT', app='plus_point',
                   module='PLUS POINT', items=navigation['items'])
    bootinfo.module_sidebars = {'PLUS POINT': sidebar}
    bootinfo.entity_module = {item['link_to']: 'PLUS POINT' for item in navigation['items'] if item.get('link_to')}
    bootinfo.home_shell = 'PLUS POINT'
    for kind, names in [('DocType', navigation['doctypes']), ('Report', navigation['reports']), ('Page',navigation['pages']), ('Workspace', [navigation['workspace']])]:
        bootinfo.setdefault('canonical_shell', {})[kind] = {name: 'PLUS POINT' for name in names}
