from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class FleetVehicleAssignment(models.Model):
    _name = 'fleet.vehicle.assignment'
    _description = 'Vehicle Assignment'
    _order = 'assignment_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    trip_request_id = fields.Many2one('fleet.trip.request', string='Trip Request', required=True, ondelete='cascade', tracking=True)
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehicle',
        required=True,
        domain="[('fleet_status', '=', 'available'), ('current_driver_id', '!=', False)]",
        tracking=True,
    )
    vehicle_driver_id = fields.Many2one(
        'hr.employee',
        string='Vehicle Driver',
        related='vehicle_id.current_driver_id',
        readonly=True,
    )
    driver_id = fields.Many2one(
        'hr.employee',
        string='Driver',
        required=True,
        domain="[('id', '=', vehicle_driver_id)]",
        tracking=True,
    )
    assignment_date = fields.Datetime(string='Assignment Date', default=fields.Datetime.now, required=True, tracking=True)
    return_date = fields.Datetime(string='Return Date', tracking=True)
    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('assigned', 'Assigned'),
            ('returned', 'Returned'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    notes = fields.Text(string='Notes')

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        for assignment in self:
            if assignment.vehicle_id and assignment.vehicle_id.current_driver_id:
                assignment.driver_id = assignment.vehicle_id.current_driver_id
            else:
                assignment.driver_id = False

    @api.constrains('vehicle_id', 'status')
    def _check_vehicle_has_single_active_assignment(self):
        for assignment in self.filtered(lambda record: record.vehicle_id and record.status == 'assigned'):
            active_assignment = self.search([
                ('id', '!=', assignment.id),
                ('vehicle_id', '=', assignment.vehicle_id.id),
                ('status', '=', 'assigned'),
            ], limit=1)
            if active_assignment:
                raise ValidationError('This vehicle is already assigned to another active trip.')

    @api.constrains('assignment_date', 'return_date')
    def _check_assignment_dates(self):
        for assignment in self:
            if assignment.assignment_date and assignment.return_date and assignment.return_date < assignment.assignment_date:
                raise ValidationError('Return Date must be after Assignment Date.')

    @api.model_create_multi
    def create(self, vals_list):
        self._set_vehicle_driver_defaults(vals_list)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('vehicle_id') and not vals.get('driver_id'):
            vals = dict(vals)
            vals_list = [vals]
            self._set_vehicle_driver_defaults(vals_list)
            vals = vals_list[0]
        return super().write(vals)

    def _set_vehicle_driver_defaults(self, vals_list):
        vehicle_ids = {
            vals['vehicle_id']
            for vals in vals_list
            if vals.get('vehicle_id') and not vals.get('driver_id')
        }
        vehicles = self.env['fleet.vehicle'].browse(list(vehicle_ids))
        drivers_by_vehicle = {
            vehicle.id: vehicle.current_driver_id.id
            for vehicle in vehicles
            if vehicle.current_driver_id
        }
        for vals in vals_list:
            driver_id = drivers_by_vehicle.get(vals.get('vehicle_id'))
            if driver_id:
                vals['driver_id'] = driver_id

    def _check_fleet_manager(self):
        if not self.env.is_superuser() and not self.env.user.has_group('fleet_management.group_fleet_manager'):
            raise AccessError('Only Fleet Managers can assign, update, or cancel vehicle assignments.')

    def action_return_vehicle(self):
        for assignment in self:
            if assignment.status != 'assigned':
                raise ValidationError('Only assigned vehicles can be returned.')
            is_driver = assignment.driver_id.user_id == self.env.user
            if (
                not self.env.is_superuser()
                and not is_driver
                and not self.env.user.has_group('fleet_management.group_fleet_manager')
            ):
                raise AccessError('Only the assigned Driver or a Fleet Manager can return the vehicle.')
            assignment.status = 'returned'
            assignment.return_date = fields.Datetime.now()
            assignment.vehicle_id.fleet_status = 'available'
            self.env['fleet.vehicle.history'].create({
                'vehicle_id': assignment.vehicle_id.id,
                'event_type': 'returned',
                'event_date': fields.Datetime.now(),
                'driver_id': assignment.driver_id.id,
                'description': 'Vehicle returned from trip assignment.',
                'odometer': assignment.vehicle_id.current_odometer,
            })

    def action_cancel(self):
        self._check_fleet_manager()
        for assignment in self:
            if assignment.status == 'assigned':
                assignment.vehicle_id.fleet_status = 'available'
            assignment.status = 'cancelled'

    def action_assign_vehicle(self):
        self._check_fleet_manager()
        for assignment in self:
            if assignment.trip_request_id.state != 'fleet_approved':
                raise ValidationError('Vehicle requests must be approved by the Fleet Manager before assignment.')
            active_assignment = self.search([
                ('id', '!=', assignment.id),
                ('vehicle_id', '=', assignment.vehicle_id.id),
                ('status', '=', 'assigned'),
            ], limit=1)
            if active_assignment:
                raise ValidationError('Selected vehicle is already assigned to another active trip.')
            if assignment.vehicle_id.fleet_status != 'available':
                raise ValidationError('Selected vehicle is not available.')
            if not assignment.vehicle_id.current_driver_id:
                raise ValidationError('Selected vehicle must have an assigned driver before it can be allocated.')
            if assignment.vehicle_id.current_driver_id and assignment.driver_id != assignment.vehicle_id.current_driver_id:
                raise ValidationError('The assigned driver must match the driver linked to the selected vehicle.')
            if not assignment.driver_id.is_fleet_driver:
                raise ValidationError('Selected driver must be marked as Fleet Driver.')
            assignment.status = 'assigned'
            assignment.vehicle_id.fleet_status = 'assigned'
            assignment.vehicle_id.current_driver_id = assignment.driver_id.id
            if assignment.trip_request_id.state == 'fleet_approved' and not self.env.context.get('skip_trip_allocate'):
                assignment.trip_request_id.action_allocate()
            self.env['fleet.vehicle.history'].create({
                'vehicle_id': assignment.vehicle_id.id,
                'event_type': 'assigned',
                'event_date': fields.Datetime.now(),
                'driver_id': assignment.driver_id.id,
                'description': 'Vehicle assigned for trip request %s.' % assignment.trip_request_id.name,
                'odometer': assignment.vehicle_id.current_odometer,
            })
