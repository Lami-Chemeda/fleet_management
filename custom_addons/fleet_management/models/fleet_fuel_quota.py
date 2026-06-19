from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

class FleetFuelQuota(models.Model):
    _name = 'fleet.fuel.quota'
    _description = 'Fuel Type Quota Configuration'
    _rec_name = 'fuel_type'

    fuel_type = fields.Selection(
        [
            ('diesel', 'Diesel'),
            ('gasoline', 'Gasoline'),
            ('full_hybrid', 'Full Hybrid'),
            ('plug_in_hybrid_diesel', 'Plug-in Hybrid Diesel'),
            ('plug_in_hybrid_gasoline', 'Plug-in Hybrid Gasoline'),
            ('cng', 'CNG'),
            ('lpg', 'LPG'),
            ('hydrogen', 'Hydrogen'),
            ('electric', 'Electric'),
        ],
        string='Fuel Type',
        required=True,
        help="Select the fuel type for which this quota applies"
    )
    
    fuel_quota = fields.Float(
        string='Monthly Fuel Quota Per Vehicle (Liters)', 
        required=True, 
        default=0.0,
        help="Maximum monthly fuel quota per vehicle for this fuel type. Set to 0 for unlimited."
    )

    _sql_constraints = [
        ('fuel_type_unique', 'unique(fuel_type)', 'A quota configuration already exists for this fuel type.')
    ]

    @api.constrains('fuel_quota')
    def _check_fuel_quota_val(self):
        for record in self:
            if record.fuel_quota < 0:
                raise ValidationError('Fuel Quota cannot be negative.')

    @api.constrains('fuel_type')
    def _check_electric_quota(self):
        """Prevent setting quota for electric vehicles as they don't use fuel"""
        for record in self:
            if record.fuel_type == 'electric':
                raise ValidationError('Electric vehicles do not require fuel quota as they do not use fuel.')

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