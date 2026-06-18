from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.osv import expression


class FleetFuelRequest(models.Model):
    _name = 'fleet.fuel.request'
    _description = 'Fuel and Lubricant Request'
    _order = 'request_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Request Number', required=True, copy=False, readonly=True, default='New')
    is_manager = fields.Boolean(compute='_compute_is_manager')
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
    requester_number = fields.Char(string='Requester Number', compute='_compute_requester_number', store=True)
    requested_quantity = fields.Float(string='Requested Quantity (Liters)', required=True, tracking=True)
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

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """
        Override search to implement visibility rules:
        - Fleet Manager: All requests.
        - Dept Manager: Requests from drivers in their department.
        - Regular User: Own fuel requests only.
        """
        if not self.env.su and not self.env.user.has_group('fleet_management.group_fleet_manager'):
            user_employee = self.env.user.employee_id
            if self.env.user.has_group('fleet_management.group_department_manager') and user_employee.department_id:
                domain = expression.AND([domain, [('driver_id.department_id', '=', user_employee.department_id.id)]])
            else:
                domain = expression.AND([domain, [('driver_id.user_id', '=', self.env.uid)]])
        
        return super()._search(domain, offset=offset, limit=limit, order=order)

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

    @api.depends_context('uid')
    def _compute_is_manager(self):
        for request in self:
            request.is_manager = self.env.user.has_group('fleet_management.group_fleet_manager')

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            vehicle_fuel = self.vehicle_id.fuel_type
            if vehicle_fuel == 'diesel':
                self.fuel_type = 'diesel'
            elif vehicle_fuel == 'gasoline':
                self.fuel_type = 'petrol'
            elif vehicle_fuel in ['full_hybrid', 'plug_in_hybrid_diesel', 'plug_in_hybrid_gasoline']:
                self.fuel_type = 'hybrid'
            elif vehicle_fuel == 'electric':
                self.fuel_type = 'electric'
            elif vehicle_fuel in ['cng', 'lpg', 'hydrogen']:
                self.fuel_type = 'other'

    @api.constrains('vehicle_id', 'driver_id')
    def _check_driver_assigned_vehicle(self):
        for request in self:
            if not self.env.user.has_group('fleet_management.group_fleet_manager') and not self.env.su:
                user_employee = self.env.user.employee_id
                if request.vehicle_id.current_driver_id != user_employee:
                    raise ValidationError("You can only request fuel for your assigned vehicle.")
                if request.driver_id != user_employee:
                    raise ValidationError("You can only request fuel for yourself.")

    @api.constrains('vehicle_id', 'fuel_type')
    def _check_fuel_type_match(self):
        for request in self:
            if request.vehicle_id:
                vehicle_fuel = request.vehicle_id.fuel_type
                req_fuel = request.fuel_type
                if req_fuel in ['petrol', 'diesel', 'hybrid', 'electric']:
                    is_match = False
                    if vehicle_fuel == 'diesel' and req_fuel == 'diesel':
                        is_match = True
                    elif vehicle_fuel == 'gasoline' and req_fuel == 'petrol':
                        is_match = True
                    elif vehicle_fuel in ['full_hybrid', 'plug_in_hybrid_diesel', 'plug_in_hybrid_gasoline'] and req_fuel == 'hybrid':
                        is_match = True
                    elif vehicle_fuel == 'electric' and req_fuel == 'electric':
                        is_match = True
                    elif vehicle_fuel in ['cng', 'lpg', 'hydrogen'] and req_fuel == 'other':
                        is_match = True
                    
                    if not is_match:
                        vehicle_fuel_label = dict(request.vehicle_id._fields['fuel_type'].selection).get(vehicle_fuel, vehicle_fuel)
                        raise ValidationError("You can only request the fuel type that your vehicle uses (%s)." % vehicle_fuel_label)

    @api.constrains('requested_quantity', 'vehicle_id', 'state', 'request_date')
    def _check_fuel_quota(self):
        for request in self:
            if request.state != 'rejected' and request.vehicle_id and not request.vehicle_id.special_case and request.request_date:
                # Resolve virtual/NewId to real database ID if in onchange/draft state
                vehicle_id = request.vehicle_id.id
                if not isinstance(vehicle_id, int) and vehicle_id:
                    if hasattr(vehicle_id, 'origin') and isinstance(vehicle_id.origin, int):
                        vehicle_id = vehicle_id.origin
                    elif hasattr(request.vehicle_id, '_origin') and request.vehicle_id._origin:
                        vehicle_id = request.vehicle_id._origin.id

                quota_rec = self.env['fleet.fuel.quota'].sudo().search([('vehicle_id', '=', vehicle_id)], limit=1)
                quota_val = quota_rec.fuel_quota if quota_rec else 0.0
                
                # Enforce monthly quota based on the request_date of fuel requests
                req_date = request.request_date
                year = req_date.year
                month = req_date.month
                
                import datetime
                month_start = datetime.datetime(year, month, 1, 0, 0, 0)
                if month == 12:
                    month_end = datetime.datetime(year + 1, 1, 1, 0, 0, 0)
                else:
                    month_end = datetime.datetime(year, month + 1, 1, 0, 0, 0)
                
                existing_requests = self.search([
                    ('vehicle_id', '=', vehicle_id),
                    ('state', 'in', ['approved', 'issued', 'completed']),
                    ('id', '!=', request.id),
                    ('request_date', '>=', month_start),
                    ('request_date', '<', month_end),
                ])
                total_used = sum(
                    r.total_issued_quantity if r.state in ['issued', 'completed'] else r.requested_quantity
                    for r in existing_requests
                )
                if total_used + request.requested_quantity > quota_val:
                    raise ValidationError(
                        "The requested quantity of %s Liters exceeds the vehicle's monthly fuel quota (%s Liters) for %s/%s. "
                        "Total requested/used in this month: %s Liters, remaining monthly quota: %s Liters." % (
                            request.requested_quantity,
                            quota_val,
                            month,
                            year,
                            total_used,
                            max(0.0, quota_val - total_used)
                        )
                    )

    @api.constrains('vehicle_id')
    def _check_electric_vehicle(self):
        for request in self:
            if request.vehicle_id and request.vehicle_id.fuel_type == 'electric':
                raise ValidationError("Vehicles with electric fuel type cannot request fuel.")

    @api.depends('driver_id')
    def _compute_requester_number(self):
        for request in self:
            if request.driver_id:
                request.requester_number = request.driver_id.mobile_phone or request.driver_id.driver_license_number or ''
            else:
                request.requester_number = ''

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        employee = self.env.user.employee_id
        if employee:
            vehicle = self.env['fleet.vehicle'].search([('current_driver_id', '=', employee.id)], limit=1)
            if vehicle:
                if 'vehicle_id' in fields_list and not res.get('vehicle_id'):
                    res['vehicle_id'] = vehicle.id
                if 'fuel_type' in fields_list and not res.get('fuel_type'):
                    vehicle_fuel = vehicle.fuel_type
                    if vehicle_fuel == 'diesel':
                        res['fuel_type'] = 'diesel'
                    elif vehicle_fuel == 'gasoline':
                        res['fuel_type'] = 'petrol'
                    elif vehicle_fuel in ['full_hybrid', 'plug_in_hybrid_diesel', 'plug_in_hybrid_gasoline']:
                        res['fuel_type'] = 'hybrid'
                    elif vehicle_fuel == 'electric':
                        res['fuel_type'] = 'electric'
                    elif vehicle_fuel in ['cng', 'lpg', 'hydrogen']:
                        res['fuel_type'] = 'other'
        return res
