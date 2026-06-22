from odoo import models, fields

class FleetFuelType(models.Model):
    _name = 'fleet.fuel.type'
    _description = 'Vehicle Fuel Type'

    name = fields.Char('Fuel Type', required=True)
    is_electric = fields.Boolean('Is Electric', default=False, help='Check this box if this fuel type does not require fuel quotas (e.g. Electric)')
