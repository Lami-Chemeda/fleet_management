from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

class FleetFuelQuota(models.Model):
    _name = 'fleet.fuel.quota'
    _description = 'Vehicle Fuel Quota Configuration'
    _rec_name = 'vehicle_id'

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehicle',
        required=True,
        ondelete='cascade',
        domain="[('current_driver_id', '!=', False)]"
    )
    driver_id = fields.Many2one(
        'hr.employee',
        string='Driver',
        related='vehicle_id.current_driver_id',
        readonly=True,
        store=True,
    )
    fuel_quota = fields.Float(string='Monthly Fuel Quota (Liters)', required=True, default=0.0)

    _sql_constraints = [
        ('vehicle_unique', 'unique(vehicle_id)', 'A fuel quota configuration already exists for this vehicle.')
    ]

    @api.constrains('fuel_quota')
    def _check_fuel_quota_val(self):
        for record in self:
            if record.fuel_quota < 0:
                raise ValidationError('Fuel Quota cannot be negative.')

    def _check_fleet_manager_access(self):
        if self.env.is_superuser():
            return
        if not self.env.user.has_group('fleet_management.group_fleet_manager'):
            raise AccessError('Only Fleet Managers can configure fuel quotas.')

    @api.model_create_multi
    def create(self, vals_list):
        self._check_fleet_manager_access()
        return super().create(vals_list)

    def write(self, vals):
        self._check_fleet_manager_access()
        return super().write(vals)

    def unlink(self):
        self._check_fleet_manager_access()
        return super().unlink()
