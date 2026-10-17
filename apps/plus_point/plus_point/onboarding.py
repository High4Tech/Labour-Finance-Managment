"""Small Desk context; guidance never changes document access or business records."""
import frappe


def boot_context(bootinfo):
    platform = bool(frappe.conf.get('pp_control_plane'))
    bootinfo.plus_point = {
        'is_platform': platform,
        'home': '/desk/high4tech' if platform else '/desk/plus-point',
    }
    # One product entry per site. Retain every engine's route/dock metadata for
    # native forms and workspaces; only their separate launcher entries change.
    for app in bootinfo.get('app_data', []):
        if app.get('app_name') == 'plus_point':
            if platform:
                app.update(app_title='High4Tech admin', app_route='/desk/high4tech')
        else:
            app['on_apps_screen'] = False
