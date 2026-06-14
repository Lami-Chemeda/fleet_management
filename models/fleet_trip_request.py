from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class FleetTripRequest(models.Model):
    _name = 'fleet.trip.request'
    _description = 'Vehicle Trip Request'
    _order = 'request_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Request Number', required=True, copy=False, readonly=True, default='New')
    requester_id = fields.Many2one(
        'hr.employee',
        string='Requester',
        default=lambda self: self.env.user.employee_id,
        required=True,
        tracking=True,
    )
    department_id = fields.Many2one('hr.department', string='Department', related='requester_id.department_id', store=True, readonly=True)
    purpose = fields.Text(string='Purpose', required=True)
    start_place = fields.Char(string='Start Place', tracking=True)
    destination = fields.Char(string='Destination', required=True)
    number_of_people = fields.Integer(string='Number of People', tracking=True)
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, required=True)
    start_date = fields.Datetime(string='Start Date', required=True, tracking=True)
    end_date = fields.Datetime(string='End Date', required=True, tracking=True)
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True, copy=False, tracking=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('department_approved', 'Department Approved'),
            ('fleet_approved', 'Fleet Approved'),
            ('allocated', 'Allocated'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    assignment_ids = fields.One2many('fleet.vehicle.assignment', 'trip_request_id', string='Vehicle Assignments')
    requester_executed = fields.Boolean(string='Requester Executed', copy=False, tracking=True)
    driver_executed = fields.Boolean(string='Driver Executed', copy=False, tracking=True)
    can_execute_current_user = fields.Boolean(
        string='Can Execute',
        compute='_compute_can_execute_current_user',
    )
    can_edit_requester = fields.Boolean(
        string='Can Edit Requester',
        compute='_compute_can_edit_requester',
    )

    @api.depends_context('uid')
    def _compute_can_edit_requester(self):
        can_edit = (
            self.env.user.has_group('fleet_management.group_department_manager')
            or self.env.user.has_group('fleet_management.group_fleet_manager')
        )
        for request in self:
            request.can_edit_requester = can_edit

    @api.depends('state', 'requester_id', 'assignment_ids.status', 'assignment_ids.driver_id')
    @api.depends_context('uid')
    def _compute_can_execute_current_user(self):
        current_employee = self.env.user.employee_id
        is_fleet_manager = self.env.user.has_group('fleet_management.group_fleet_manager')
        for request in self:
            assigned_drivers = request.assignment_ids.filtered(
                lambda assignment: assignment.status == 'assigned'
            ).mapped('driver_id')
            request.can_execute_current_user = bool(
                request.state == 'allocated'
                and current_employee
                and not is_fleet_manager
                and (
                    request.requester_id == current_employee
                    or current_employee in assigned_drivers
                )
            )

    @api.constrains('start_date', 'end_date')
    def _check_trip_dates(self):
        for request in self:
            if request.start_date and request.end_date and request.end_date < request.start_date:
                raise ValidationError('End Date must be after Start Date.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.trip.request') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        if vals.get('state') == 'completed':
            self._return_completed_trip_assignments()
        return result

    def _check_group(self, group_xmlid, message):
        if not self.env.is_superuser() and not self.env.user.has_group(group_xmlid):
            raise AccessError(message)

    def action_submit(self):
        for request in self:
            if (
                request.requester_id != self.env.user.employee_id
                and not self.env.user.has_group('fleet_management.group_department_manager')
            ):
                raise AccessError('You can only submit vehicle requests for yourself.')
            if not request.purpose or not request.destination:
                raise ValidationError('Purpose and Destination are required before submitting.')
            request.state = 'submitted'

    def action_department_approve(self):
        self._check_group(
            'fleet_management.group_department_manager',
            'Only Department Managers can approve vehicle requests at department level.',
        )
        self.write({'state': 'department_approved'})

    def action_fleet_approve(self):
        self._check_group(
            'fleet_management.group_fleet_manager',
            'Only Fleet Managers can approve vehicle requests for fleet allocation.',
        )
        self.write({'state': 'fleet_approved'})

    def action_allocate(self):
        self._check_group(
            'fleet_management.group_fleet_manager',
            'Only Fleet Managers can allocate vehicles and drivers.',
        )
        for request in self:
            if not request.assignment_ids:
                raise ValidationError('Please create a vehicle assignment before marking the request as allocated.')
            draft_assignments = request.assignment_ids.filtered(lambda assignment: assignment.status == 'draft')
            if draft_assignments:
                draft_assignments.with_context(skip_trip_allocate=True).action_assign_vehicle()
            request.write({
                'state': 'allocated',
                'requester_executed': False,
                'driver_executed': False,
            })

    def action_complete(self):
        self._check_group(
            'fleet_management.group_fleet_manager',
            'Only Fleet Managers can manually complete a trip.',
        )
        self._complete_trip()

    def action_execute(self):
        current_employee = self.env.user.employee_id
        if not current_employee:
            raise AccessError('Your user must be linked to an employee to execute a trip.')

        for request in self:
            if request.state != 'allocated':
                raise ValidationError('Only allocated trips can be executed.')

            vals = {}
            is_requester = request.requester_id == current_employee
            is_driver = current_employee in request.assignment_ids.filtered(
                lambda assignment: assignment.status == 'assigned'
            ).mapped('driver_id')

            if is_requester:
                vals['requester_executed'] = True
            if is_driver:
                vals['driver_executed'] = True
            if not vals:
                raise AccessError('Only the requester or assigned Driver can execute this trip.')

            request.write(vals)
            if request.requester_executed and request.driver_executed:
                request._complete_trip()

    def _complete_trip(self):
        for request in self:
            request.state = 'completed'

    def _return_completed_trip_assignments(self):
        for request in self.filtered(lambda trip: trip.state == 'completed'):
            assigned_assignments = request.assignment_ids.filtered(lambda assignment: assignment.status == 'assigned')
            if assigned_assignments:
                assigned_assignments.sudo().action_return_vehicle()

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
        for request in self:
            if request.state == 'submitted':
                request._check_group(
                    'fleet_management.group_department_manager',
                    'Only Department Managers can reject submitted vehicle requests.',
                )
            else:
                request._check_group(
                    'fleet_management.group_fleet_manager',
                    'Only Fleet Managers can reject requests after department approval.',
                )
            request.state = 'rejected'

    def action_cancel(self):
        for request in self:
            if request.state not in ['draft', 'submitted']:
                raise ValidationError('Vehicle requests can only be cancelled before approval.')
            is_requester = (
                request.requester_id.user_id == self.env.user
                or request.create_uid == self.env.user
            )
            if not is_requester and not self.env.user.has_group('fleet_management.group_department_manager'):
                raise AccessError('Only the requester or Department Manager can cancel this request before approval.')
            request.state = 'cancelled'

    def action_reset_to_draft(self):
        self._check_group(
            'fleet_management.group_fleet_manager',
            'Only Fleet Managers can reset rejected or cancelled vehicle requests.',
        )
        self.write({
            'state': 'draft',
            'requester_executed': False,
            'driver_executed': False,
        })
