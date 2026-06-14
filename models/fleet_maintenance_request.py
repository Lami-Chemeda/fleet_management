from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class FleetMaintenanceRequest(models.Model):
    _name = 'fleet.maintenance.request'
    _description = 'Vehicle Maintenance Request'
    _order = 'request_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Request Number', required=True, copy=False, readonly=True, default='New')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True)
    requested_by_id = fields.Many2one(
        'hr.employee',
        string='Requested By',
        default=lambda self: self.env.user.employee_id,
        tracking=True,
    )
    problem_description = fields.Text(string='Problem Description', required=True)
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, required=True)
    priority = fields.Selection(
        [
            ('low', 'Low'),
            ('normal', 'Normal'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ],
        string='Priority',
        default='normal',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('sent_to_garage', 'Sent To Garage'),
            ('completed', 'Completed'),
            ('closed', 'Closed'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True, copy=False, tracking=True)
    service_ids = fields.One2many('fleet.maintenance.service', 'maintenance_request_id', string='Maintenance Services')
    total_service_cost = fields.Monetary(
        string='Total Service Cost',
        compute='_compute_total_service_cost',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    @api.depends('service_ids.cost')
    def _compute_total_service_cost(self):
        for request in self:
            request.total_service_cost = sum(request.service_ids.mapped('cost'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.maintenance.request') or 'New'
        return super().create(vals_list)

    def _check_fleet_manager(self):
        if not self.env.is_superuser() and not self.env.user.has_group('fleet_management.group_fleet_manager'):
            raise AccessError('Only Fleet Managers can approve and manage maintenance processing.')

    def _check_driver_vehicle(self):
        for request in self:
            if self.env.user.has_group('fleet_management.group_fleet_manager'):
                continue
            if request.requested_by_id != self.env.user.employee_id:
                raise AccessError('Drivers can only submit maintenance requests for themselves.')
            if not request.requested_by_id or not request.requested_by_id.is_fleet_driver:
                raise ValidationError('Maintenance can only be requested by a registered Fleet Driver.')
            if request.vehicle_id.current_driver_id != request.requested_by_id:
                raise ValidationError('Drivers can only request maintenance for their assigned vehicle.')

    def action_submit(self):
        for request in self:
            if not request.problem_description:
                raise ValidationError('Problem Description is required before submitting.')
            request._check_driver_vehicle()
            request.state = 'submitted'

    def action_approve(self):
        self._check_fleet_manager()
        for request in self:
            if request.vehicle_id.fleet_status == 'retired':
                raise ValidationError('Retired vehicles cannot be sent for maintenance.')
            request.state = 'approved'
            request.vehicle_id.fleet_status = 'maintenance'
            self.env['fleet.vehicle.history'].create({
                'vehicle_id': request.vehicle_id.id,
                'event_type': 'maintenance_started',
                'event_date': fields.Datetime.now(),
                'driver_id': request.vehicle_id.current_driver_id.id,
                'description': request.problem_description,
                'odometer': request.vehicle_id.current_odometer,
            })

    def action_send_to_garage(self):
        self._check_fleet_manager()
        for request in self:
            if not request.service_ids:
                raise ValidationError('Please create a service record with a garage/vendor before sending to garage.')
            request.state = 'sent_to_garage'

    def action_complete(self):
        self._check_fleet_manager()
        for request in self:
            if not request.service_ids:
                raise ValidationError('Please record maintenance service details before completing.')
            incomplete_services = request.service_ids.filtered(lambda service: not service.completion_date)
            if incomplete_services:
                raise ValidationError('All service records must have a Completion Date before completing maintenance.')
            request.state = 'completed'

    def action_close(self):
        self._check_fleet_manager()
        for request in self:
            if request.state != 'completed':
                raise ValidationError('Only completed maintenance requests can be closed.')
            request.state = 'closed'
            request.vehicle_id.fleet_status = 'available'
            self.env['fleet.vehicle.history'].create({
                'vehicle_id': request.vehicle_id.id,
                'event_type': 'maintenance_completed',
                'event_date': fields.Datetime.now(),
                'driver_id': request.vehicle_id.current_driver_id.id,
                'description': 'Maintenance completed and request closed.',
                'odometer': request.vehicle_id.current_odometer,
            })

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Request',
            'res_model': 'fleet.reject.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_model': self._name,
                'default_request_id': self.id,
            },
        }

    def action_reject(self):
        self._check_fleet_manager()
        self.write({'state': 'rejected'})

    def action_reset_to_draft(self):
        self._check_fleet_manager()
        self.write({'state': 'draft'})
