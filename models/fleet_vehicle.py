from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    chassis_number = fields.Char(string='VIN / Chassis Number', required=True, copy=False, index=True)
    engine_number = fields.Char(string='Engine Number', copy=False)
    ownership_type = fields.Selection(
        [
            ('company', 'Company'),
            ('government', 'Government'),
            ('leased', 'Leased'),
            ('rented', 'Rented'),
        ],
        string='Ownership Type',
    )
    registration_certificate_number = fields.Char(string='Registration Certificate Number', copy=False)
    registration_date = fields.Date(string='Official Registration Date')
    fleet_status = fields.Selection(
        [
            ('available', 'Available'),
            ('assigned', 'Assigned'),
            ('maintenance', 'Maintenance'),
            ('inactive', 'Inactive'),
            ('retired', 'Retired'),
        ],
        string='Fleet Status',
        default='available',
        required=True,
        tracking=True,
    )
    current_driver_id = fields.Many2one('hr.employee', string='Current Driver', tracking=True)
    current_odometer = fields.Float(string='Current Odometer')
    special_case = fields.Boolean(string='Special Case', default=False, tracking=True)

    _sql_constraints = [
        (
            'fleet_vehicle_chassis_number_unique',
            'unique(chassis_number)',
            'The VIN / Chassis Number must be unique for each vehicle.',
        ),
    ]

    @api.constrains('registration_date', 'create_date')
    def _check_registration_dates(self):
        for vehicle in self:
            if vehicle.registration_date and vehicle.create_date and vehicle.registration_date < vehicle.create_date.date():
                raise ValidationError('The Official Registration Date must be on or after the date the vehicle was registered in the system.')

    def _check_fleet_vehicle_manager_access(self):
        if self.env.is_superuser():
            return
        if not self.env.user.has_group('fleet_management.group_fleet_manager'):
            raise AccessError(
                'Only Fleet Managers can create, edit, or delete vehicles.'
            )

    @api.model_create_multi
    def create(self, vals_list):
        self._check_fleet_vehicle_manager_access()
        vehicles = super().create(vals_list)
        for vehicle in vehicles:
            self.env['fleet.vehicle.history'].create({
                'vehicle_id': vehicle.id,
                'event_type': 'registered',
                'event_date': fields.Datetime.now(),
                'driver_id': vehicle.current_driver_id.id,
                'description': 'Vehicle registered in the fleet system.',
                'odometer': vehicle.current_odometer,
            })
        return vehicles

    def write(self, vals):
        protected_fields = {
            'name',
            'license_plate',
            'model_id',
            'chassis_number',
            'engine_number',
            'ownership_type',
            'registration_certificate_number',
            'registration_date',
            'fleet_status',
            'current_driver_id',
            'current_odometer',
            'special_case',
        }
        if protected_fields.intersection(vals):
            self._check_fleet_vehicle_manager_access()
        return super().write(vals)

    def unlink(self):
        self._check_fleet_vehicle_manager_access()
        return super().unlink()
