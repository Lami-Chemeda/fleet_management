from odoo import models, fields, api

class FleetVehicleGpsLog(models.Model):
    _name = 'fleet.vehicle.gps.log'
    _description = 'Vehicle GPS Log'
    _order = 'timestamp desc'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, index=True)
    latitude = fields.Float(string='Latitude', digits=(10, 7), required=True)
    longitude = fields.Float(string='Longitude', digits=(10, 7), required=True)
    speed = fields.Float(string='Speed (km/h)')
    timestamp = fields.Datetime(string='Timestamp', required=True, index=True)
    source = fields.Char(string='Source Device/API')
    geofence_alert = fields.Boolean(string='Geofence Alert', default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
