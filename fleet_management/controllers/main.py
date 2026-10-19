from odoo import http
from odoo.http import request

class FleetDashboardController(http.Controller):

    @http.route(['/', '/fleet'], type='http', auth="public", website=True)
    def fleet_dashboard(self, **kwargs):
        # Gather basic stats to display on the dashboard
        values = {
            'vehicle_count': request.env['fleet.vehicle'].sudo().search_count([]),
            'trip_count': request.env['fleet.trip.request'].sudo().search_count([]),
            'incident_count': request.env['fleet.incident'].sudo().search_count([]),
        }
        return request.render("fleet_management.fleet_public_dashboard", values)

from odoo.addons.web.controllers.home import Home

class FleetLoginRedirect(Home):
    def _login_redirect(self, uid, redirect=None):
        url = super()._login_redirect(uid, redirect=redirect)
        if not redirect and url in ('/web', '/odoo', '/'):
            # Redirect to the spectacular backend dashboard
            action = request.env.ref('fleet_management.action_fleet_backend_dashboard', raise_if_not_found=False)
            if action:
                return f'/odoo/action-{action.id}'
        return url
