from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class FleetFuelRequest(models.Model):
    _name = 'fleet.fuel.request'
    _description = 'Fuel and Lubricant Request'
    _order = 'request_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Request Number', required=True, copy=False, readonly=True, default='New')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True)
    driver_id = fields.Many2one(
        'hr.employee',
        string='Driver',
        default=lambda self: self.env.user.employee_id if self.env.user.employee_id.is_fleet_driver else False,
        required=True,
        domain="[('is_fleet_driver', '=', True)]",
        tracking=True,
    )
    fuel_type = fields.Selection(
        [
            ('petrol', 'Petrol'),
            ('diesel', 'Diesel'),
            ('hybrid', 'Hybrid'),
            ('electric', 'Electric'),
            ('engine_oil', 'Engine Oil'),
            ('gear_oil', 'Gear Oil'),
            ('grease', 'Grease'),
            ('other', 'Other'),
        ],
        string='Fuel / Lubricant Type',
        required=True,
        tracking=True,
    )
    requested_quantity = fields.Float(string='Requested Quantity', required=True, tracking=True)
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, required=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('issued', 'Issued'),
            ('completed', 'Completed'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True, copy=False, tracking=True)
    issue_ids = fields.One2many('fleet.fuel.issue', 'fuel_request_id', string='Fuel Issues')
    total_issued_quantity = fields.Float(
        string='Total Issued Quantity',
        compute='_compute_issue_totals',
        store=True,
    )
    total_fuel_cost = fields.Monetary(
        string='Total Fuel Cost',
        compute='_compute_issue_totals',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    @api.depends('issue_ids.issued_quantity', 'issue_ids.cost')
    def _compute_issue_totals(self):
        for request in self:
            request.total_issued_quantity = sum(request.issue_ids.mapped('issued_quantity'))
            request.total_fuel_cost = sum(request.issue_ids.mapped('cost'))

    @api.constrains('requested_quantity')
    def _check_requested_quantity(self):
        for request in self:
            if request.requested_quantity <= 0:
                raise ValidationError('Requested Quantity must be greater than zero.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.fuel.request') or 'New'
        return super().create(vals_list)

    def _check_fleet_manager(self):
        if not self.env.is_superuser() and not self.env.user.has_group('fleet_management.group_fleet_manager'):
            raise AccessError('Only Fleet Managers can approve, reject, and issue fuel requests.')

    def _get_active_assignment(self):
        self.ensure_one()
        return self.env['fleet.vehicle.assignment'].search([
            ('vehicle_id', '=', self.vehicle_id.id),
            ('driver_id', '=', self.driver_id.id),
            ('status', '=', 'assigned'),
            ('trip_request_id.state', '=', 'allocated'),
        ], limit=1)

    def _check_active_trip_assignment(self):
        for request in self:
            if (
                request.driver_id != self.env.user.employee_id
                and not self.env.user.has_group('fleet_management.group_fleet_manager')
            ):
                raise AccessError('Drivers can only submit fuel requests for themselves.')
            if not request.driver_id.is_fleet_driver:
                raise ValidationError('Fuel can only be requested by an employee registered as a Fleet Driver.')
            if not request._get_active_assignment():
                raise ValidationError('Fuel requests require an active allocated trip for the selected vehicle and driver.')

    def action_submit(self):
        self._check_active_trip_assignment()
        self.write({'state': 'submitted'})

    def action_approve(self):
        self._check_fleet_manager()
        self.write({'state': 'approved'})

    def action_issue(self):
        self._check_fleet_manager()
        for request in self:
            if not request.issue_ids:
                raise ValidationError('Please create at least one fuel issue before marking as issued.')
            request.state = 'issued'

    def action_complete(self):
        self._check_fleet_manager()
        for request in self:
            if request.state != 'issued':
                raise ValidationError('Only issued requests can be completed.')
            request.state = 'completed'

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
