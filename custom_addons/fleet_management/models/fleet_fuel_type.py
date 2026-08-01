from odoo import models, fields, api


class FleetFuelType(models.Model):
    _name = 'fleet.fuel.type'
    _description = 'Vehicle Fuel Type'

    name = fields.Char('Fuel Type', required=True)
    is_electric = fields.Boolean('Is Electric', default=False, help='Check this box if this fuel type does not require fuel quotas (e.g. Electric)')

    @api.onchange('is_electric')
    def _onchange_is_electric(self):
        if self.is_electric:
            self.name = 'Electric'

    @api.constrains('is_electric')
    def _check_electric_name(self):
        for record in self:
            if record.is_electric and record.name != 'Electric':
                record.name = 'Electric'
