from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'


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
    seat_count = fields.Integer(string='Seat Count', tracking=True, help='Number of seats in the vehicle')
    
    custom_fuel_type_id = fields.Many2one('fleet.fuel.type', string='Fuel Category', tracking=True)
    has_active_request = fields.Boolean(
        string='Has Active Request',
        compute='_compute_has_active_request',
        search='_search_has_active_request',
    )

    def _compute_has_active_request(self):
        for vehicle in self:
            active_maint = self.env['fleet.maintenance.request'].search_count([
                ('vehicle_id', '=', vehicle.id),
                ('state', 'not in', ['completed', 'closed', 'rejected'])
            ])
            active_fuel = self.env['fleet.fuel.request'].search_count([
                ('vehicle_id', '=', vehicle.id),
                ('state', 'not in', ['completed', 'rejected'])
            ])
            vehicle.has_active_request = bool(active_maint or active_fuel)

    def _search_has_active_request(self, operator, value):
        active_maint_vehicles = self.env['fleet.maintenance.request'].search([
            ('state', 'not in', ['completed', 'closed', 'rejected'])
        ]).mapped('vehicle_id.id')
        active_fuel_vehicles = self.env['fleet.fuel.request'].search([
            ('state', 'not in', ['completed', 'rejected'])
        ]).mapped('vehicle_id.id')
        
        invalid_vehicle_ids = list(set(active_maint_vehicles + active_fuel_vehicles))
        
        if operator == '=' and value is False:
            return [('id', 'not in', invalid_vehicle_ids)]
        elif operator == '=' and value is True:
            return [('id', 'in', invalid_vehicle_ids)]
        
        return []

    _sql_constraints = []

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

            'engine_number',
            'ownership_type',
            'registration_certificate_number',
            'registration_date',
            'fleet_status',
            'custom_fuel_type_id',
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
