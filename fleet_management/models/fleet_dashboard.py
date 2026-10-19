from odoo import models, fields, api

class FleetBackendDashboard(models.TransientModel):
    _name = 'fleet.backend.dashboard'
    _description = 'Fleet Executive Backend Dashboard'

    name = fields.Char(default="Dashboard")
    
    # KPIs
    vehicle_count = fields.Integer(compute='_compute_kpis')
    trip_count = fields.Integer(compute='_compute_kpis')
    incident_count = fields.Integer(compute='_compute_kpis')
    maintenance_count = fields.Integer(compute='_compute_kpis')

    def _compute_kpis(self):
        for record in self:
            record.vehicle_count = self.env['fleet.vehicle'].search_count([])
            record.trip_count = self.env['fleet.trip.request'].search_count([])
            record.incident_count = self.env['fleet.incident'].search_count([])
            record.maintenance_count = self.env['fleet.maintenance.request'].search_count([])

    def action_open_vehicles(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicles',
            'res_model': 'fleet.vehicle',
            'view_mode': 'kanban,list,form',
        }

    def action_open_trips(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Trips',
            'res_model': 'fleet.trip.request',
            'view_mode': 'list,form',
        }

    def action_open_incidents(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Incidents',
            'res_model': 'fleet.incident',
            'view_mode': 'list,form',
        }

    def action_open_maintenance(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance',
            'res_model': 'fleet.maintenance.request',
            'view_mode': 'list,form',
        }
