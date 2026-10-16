"""Small Desk context; guidance never changes document access or business records."""
import frappe


def boot_context(bootinfo):
    platform = bool(frappe.conf.get('pp_control_plane'))
    bootinfo.plus_point = {
        'is_platform': platform,
        'home': '/desk/high4tech' if platform else '/desk/plus-point',
    }
    if platform:
        # The same extension serves two separate sites. Its platform tile should
        # open subscriber administration rather than the contractor workspace.
        for app in bootinfo.get('app_data', []):
            if app.get('app_name') == 'plus_point':
                app.update(app_title='High4Tech admin', app_route='/desk/high4tech')
