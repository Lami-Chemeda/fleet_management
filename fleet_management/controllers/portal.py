from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class FleetPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'incident_count' in counters:
            values['incident_count'] = request.env['fleet.incident'].search_count([])
        if 'inspection_count' in counters:
            values['inspection_count'] = request.env['fleet.vehicle.inspection'].search_count([])
        return values

    @http.route(['/my/incidents', '/my/incidents/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_incidents(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        Incident = request.env['fleet.incident']
        domain = []
        
        pager = portal_pager(
            url="/my/incidents",
            total=Incident.search_count(domain),
            page=page,
            step=self._items_per_page
        )
        
        incidents = Incident.search(domain, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'incidents': incidents,
            'page_name': 'incident',
            'pager': pager,
            'default_url': '/my/incidents',
        })
        return request.render("fleet_management.portal_my_incidents", values)

    @http.route(['/my/inspections', '/my/inspections/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_inspections(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        Inspection = request.env['fleet.vehicle.inspection']
        domain = []
        
        pager = portal_pager(
            url="/my/inspections",
            total=Inspection.search_count(domain),
            page=page,
            step=self._items_per_page
        )
        
        inspections = Inspection.search(domain, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'inspections': inspections,
            'page_name': 'inspection',
            'pager': pager,
            'default_url': '/my/inspections',
        })
        return request.render("fleet_management.portal_my_inspections", values)
