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
    is_editable = fields.Boolean(compute='_compute_is_editable', store=False)
    show_as_label = fields.Boolean(compute='_compute_show_as_label', store=False)
    
    vehicle_id = fields.Many2one(
        'fleet.vehicle', 
        string='Vehicle', 
        required=True, 
        tracking=True,
        readonly=True,  # Locked - auto-filled from driver
    )
    driver_id = fields.Many2one(
        'hr.employee',
        string='Driver',
        default=lambda self: self.env.user.employee_id if self.env.user.employee_id.is_fleet_driver else False,
        required=True,
        domain="[('is_fleet_driver', '=', True)]",
        tracking=True,
        readonly=True,  # Locked - auto-filled from logged in user
    )
    
    # This is the fuel type from the vehicle (display only)
    vehicle_fuel_type = fields.Char(
        string='Vehicle Fuel Type',
        compute='_compute_vehicle_fuel_type',
        store=False,
        help='Fuel type from the vehicle registration'
    )
    
    # Fuel Type for the request (mapped from vehicle)
    fuel_type_id = fields.Many2one(
        'fleet.fuel.type',
        string='Fuel Type',
        required=True,
        readonly=True,  # Locked - auto-filled from vehicle
        tracking=True,
    )
    
    requester_number = fields.Char(string='Requester Number', compute='_compute_requester_number', store=True)
    product_name = fields.Char(string='Product Name', compute='_compute_product_fields')
    product_type = fields.Char(string='Product Type', compute='_compute_product_fields')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    requested_quantity = fields.Float(string='Requested Quantity (Liters)', required=True)
    issued_quantity = fields.Float(string='Issued Quantity', help='Quantity issued after approval')
    issue_date = fields.Datetime(string='Issue Date', help='Date the fuel was issued')
    issuer_id = fields.Many2one('res.users', string='Issuer', help='Person who issued the fuel')
    dept_authorized_by_id = fields.Many2one('res.users', string='Authorized by (Dept. Manager)', help='Department Manager who authorized this request', readonly=True, copy=False)
    fleet_approved_by_id = fields.Many2one('res.users', string='Approved by (Fleet Manager)', help='Fleet Manager who approved this request', readonly=True, copy=False)
    request_date = fields.Datetime(
        string='Request Date', 
        default=fields.Datetime.now, 
        required=True,
        readonly=True
    )
    
    priority = fields.Selection(
        [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ],
        string='Priority',
        default='medium',
        required=True,
        tracking=True,
    )
    
    reason = fields.Text(
        string='Reason for Request',
        required=True,
        tracking=True,
        help='Please provide the reason for this fuel request'
    )
    
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

    @api.depends('vehicle_id')
    def _compute_vehicle_fuel_type(self):
        """Get the fuel type from the vehicle registration"""
        for request in self:
            if request.vehicle_id and request.vehicle_id.custom_fuel_type_id:
                request.vehicle_fuel_type = request.vehicle_id.custom_fuel_type_id.name
            else:
                request.vehicle_fuel_type = ''

    @api.depends('state')
    def _compute_is_editable(self):
        for request in self:
            request.is_editable = request.state == 'draft'

    @api.depends('state')
    def _compute_show_as_label(self):
        for request in self:
            request.show_as_label = request.state != 'draft'

    @api.depends('issue_ids.issued_quantity', 'issue_ids.cost')
    def _compute_issue_totals(self):
        for request in self:
            request.total_issued_quantity = sum(request.issue_ids.mapped('issued_quantity'))
            request.total_fuel_cost = sum(request.issue_ids.mapped('cost'))

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
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

    @api.constrains('reason')
    def _check_reason(self):
        for request in self:
            if request.reason and len(request.reason.strip()) < 5:
                raise ValidationError('Please provide a detailed reason (minimum 5 characters).')

    def _get_driver_vehicle(self, driver_id=None):
        """Helper method to get the vehicle assigned to a driver"""
        if not driver_id:
            employee = self.env.user.employee_id
            if not employee or not employee.is_fleet_driver:
                return None
            driver_id = employee.id
        
        vehicle = self.env['fleet.vehicle'].search([
            ('current_driver_id', '=', driver_id),
        ], limit=1)
        
        return vehicle

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.fuel.request') or 'New'
            
            vals['request_date'] = fields.Datetime.now()
            
            # Auto-set driver from current user if not provided
            if not vals.get('driver_id'):
                employee = self.env.user.employee_id
                if employee and employee.is_fleet_driver:
                    vals['driver_id'] = employee.id
            
            # Auto-set vehicle from driver if not provided
            if not vals.get('vehicle_id') and vals.get('driver_id'):
                vehicle = self._get_driver_vehicle(vals['driver_id'])
                if vehicle:
                    # Check if vehicle is electric
                    if vehicle.custom_fuel_type_id.is_electric:
                        raise ValidationError(
                            f"This vehicle ({vehicle.name}) cannot request fuel because its fuel type is Electric."
                        )
                    vals['vehicle_id'] = vehicle.id
                    if vehicle.custom_fuel_type_id:
                        vals['fuel_type_id'] = vehicle.custom_fuel_type_id.id
                else:
                    raise ValidationError(
                        "You do not have any vehicle assigned to you. Please contact your Fleet Manager."
                    )
            
            # If vehicle_id is provided but fuel_type is not, auto-set from vehicle
            if vals.get('vehicle_id') and not vals.get('fuel_type_id'):
                vehicle = self.env['fleet.vehicle'].browse(vals['vehicle_id'])
                if vehicle:
                    if vehicle.custom_fuel_type_id.is_electric:
                        raise ValidationError(
                            f"This vehicle ({vehicle.name}) cannot request fuel because its fuel type is Electric."
                        )
                    vals['fuel_type_id'] = vehicle.custom_fuel_type_id.id
            
            if not vals.get('priority'):
                vals['priority'] = 'medium'
        
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
    def _notify_users(self, users, message):
        if not self or not users:
            return
        self.ensure_one()
        
        try:
            self.message_post(
                body=message,
                partner_ids=users.mapped('partner_id').ids,
            )
        except Exception as e:
            pass
            
        for user in users:
            try:
                self.env['custom.notification'].create({
                    'title': f'Fuel Request {self.name} - Status Update',
                    'user_id': user.id,
                    'message': message,
                    'is_read': False,
                })
            except Exception as e:
                pass


    def action_submit(self):
        # Check all conditions before submitting
        for request in self:
            if not request.vehicle_id:
                raise ValidationError("Please select a vehicle before submitting.")
            if not request.fuel_type_id:
                raise ValidationError("Fuel type could not be determined from the vehicle.")
            if not request.reason:
                raise ValidationError("Please provide a reason for the fuel request.")
            if request.requested_quantity <= 0:
                raise ValidationError("Requested Quantity must be greater than zero.")
            
            # Check if vehicle is electric
            if request.vehicle_id.custom_fuel_type_id.is_electric:
                raise ValidationError(
                    f"This vehicle ({request.vehicle_id.name}) cannot request fuel because its fuel type is Electric."
                )
            
            # Check quota (will also check special_case)
            self._check_fuel_quota_single(request)
        
        self._check_active_trip_assignment()
        self.write({'state': 'submitted'})
        for request in self:
            # Notify Fleet Manager
            fleet_manager_group = self.env.ref('fleet_management.group_fleet_manager')
            fleet_managers = fleet_manager_group.users.filtered(lambda u: u.active)
            if fleet_managers:
                request._notify_users(fleet_managers, "New fuel request pending approval")
            # Notify Driver
            if request.driver_id and request.driver_id.user_id:
                request._notify_users(request.driver_id.user_id, "Your fuel request has been submitted")

    def _check_fuel_quota_single(self, request):
        """Check fuel quota for a single request"""
        # Special case vehicles have unlimited quota - skip quota check
        if request.vehicle_id.special_case:
            return
            
        # Check if quota exists for this fuel type
        quota_rec = self.env['fleet.fuel.quota'].sudo().search([
            ('fuel_type_id', '=', request.fuel_type_id.id)
        ], limit=1)
        
        if quota_rec:
            quota_val = quota_rec.fuel_quota
            
            # If quota is 0, it means unlimited - skip check
            if quota_val == 0:
                return
                
            # Enforce monthly quota per vehicle for this fuel type
            req_date = request.request_date
            year = req_date.year
            month = req_date.month
            
            import datetime
            month_start = datetime.datetime(year, month, 1, 0, 0, 0)
            if month == 12:
                month_end = datetime.datetime(year + 1, 1, 1, 0, 0, 0)
            else:
                month_end = datetime.datetime(year, month + 1, 1, 0, 0, 0)
            
            # Get requests for THIS SPECIFIC VEHICLE with this fuel type
            existing_requests = self.search([
                ('vehicle_id', '=', request.vehicle_id.id),
                ('fuel_type_id', '=', request.fuel_type_id.id),
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
                    f"The requested quantity of {request.requested_quantity} Liters exceeds the vehicle's monthly fuel quota "
                    f"for {request.fuel_type_id} ({quota_val} Liters per vehicle) for {month}/{year}.\n"
                    f"Vehicle: {request.vehicle_id.name}\n"
                    f"Total used by this vehicle this month: {total_used} Liters\n"
                    f"Remaining quota: {max(0.0, quota_val - total_used)} Liters"
                )

    def action_dept_authorize(self):
        """Department Manager authorizes the fuel request."""
        if not self.env.user.has_group('fleet_management.group_department_manager'):
            raise AccessError('Only Department Managers can authorize fuel requests.')
        for request in self:
            if request.state != 'submitted':
                raise ValidationError('Only submitted requests can be authorized.')
        self.with_context(skip_state_check=True).write({
            'dept_authorized_by_id': self.env.user.id,
        })

    def action_approve(self):
        self._check_fleet_manager()
        for request in self:
            if request.vehicle_id and request.vehicle_id.custom_fuel_type_id.is_electric:
                raise ValidationError(
                    f"This vehicle ({request.vehicle_id.name}) cannot request fuel because its fuel type is Electric."
                )
        self.with_context(skip_state_check=True).write({
            'state': 'approved',
            'issue_date': fields.Datetime.now(),
            'issuer_id': self.env.user.id,
            'fleet_approved_by_id': self.env.user.id,
        })
        for request in self:
            # Notify Driver
            if request.driver_id and request.driver_id.user_id:
                request._notify_users(request.driver_id.user_id, "Your fuel request has been approved")
            # Notify Fleet Managers
            fleet_manager_group = self.env.ref('fleet_management.group_fleet_manager')
            fleet_managers = fleet_manager_group.users.filtered(lambda u: u.active)
            if fleet_managers:
                request._notify_users(fleet_managers, f"Fuel request {request.name} approved")


    def action_issue(self):
        self._check_fleet_manager()
        for request in self:
            if request.vehicle_id and request.vehicle_id.custom_fuel_type_id.is_electric:
                raise ValidationError(
                    f"This vehicle ({request.vehicle_id.name}) cannot request fuel because its fuel type is Electric."
                )
            if request.issued_quantity <= 0:
                raise ValidationError("Please set an Issued Quantity greater than zero before marking as issued.")
                
            # Auto-create the Fuel Issue record so it shows up in Fuel Consumption reports
            # Check if one hasn't already been created manually
            if not request.issue_ids:
                self.env['fleet.fuel.issue'].create({
                    'fuel_request_id': request.id,
                    'issued_quantity': request.issued_quantity,
                    'issue_date': request.issue_date or fields.Datetime.now(),
                    'issuer_id': self.env.user.id,
                })
                
            request.with_context(skip_state_check=True).write({'state': 'issued'})

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
        for request in self:
            # Notify Driver
            if request.driver_id and request.driver_id.user_id:
                request._notify_users(request.driver_id.user_id, "Your fuel request has been rejected")
            # Notify Fleet Managers
            fleet_manager_group = self.env.ref('fleet_management.group_fleet_manager')
            fleet_managers = fleet_manager_group.users.filtered(lambda u: u.active)
            if fleet_managers:
                request._notify_users(fleet_managers, f"Fuel request {request.name} has been rejected")

    def action_reset_to_draft(self):
        self._check_fleet_manager()
        self.write({'state': 'draft'})

    @api.depends_context('uid')
    def _compute_is_manager(self):
        for request in self:
            request.is_manager = self.env.user.has_group('fleet_management.group_fleet_manager')

    @api.onchange('driver_id')
    def _onchange_driver_id(self):
        """Auto-set vehicle when driver changes"""
        if self.driver_id and self.state == 'draft':
            vehicle = self._get_driver_vehicle(self.driver_id.id)
            if vehicle:
                # Only show warning if vehicle is electric, but don't block
                if vehicle.custom_fuel_type_id.is_electric:
                    self.vehicle_id = vehicle.id
                    self.fuel_type_id = False
                    return {
                        'warning': {
                            'title': 'Electric Vehicle',
                            'message': f"This vehicle ({vehicle.name}) is electric and cannot request fuel. Please contact your Fleet Manager."
                        }
                    }
                self.vehicle_id = vehicle.id
                if vehicle.custom_fuel_type_id:
                    self.fuel_type_id = vehicle.custom_fuel_type_id.id
            else:
                self.vehicle_id = False
                self.fuel_type_id = False

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id and self.state == 'draft':
            # Only show warning if vehicle is electric, but don't block
            if self.vehicle_id.custom_fuel_type_id.is_electric:
                self.fuel_type_id = False
                return {
                    'warning': {
                        'title': 'Electric Vehicle',
                        'message': f"This vehicle ({self.vehicle_id.name}) is electric and cannot request fuel. Please contact your Fleet Manager."
                    }
                }
            if self.vehicle_id.custom_fuel_type_id:
                self.fuel_type_id = self.vehicle_id.custom_fuel_type_id.id

    @api.constrains('vehicle_id', 'driver_id')
    def _check_driver_assigned_vehicle(self):
        for request in self:
            if not self.env.user.has_group('fleet_management.group_fleet_manager') and not self.env.su:
                user_employee = self.env.user.employee_id
                if request.vehicle_id.current_driver_id != user_employee:
                    raise ValidationError("You can only request fuel for your assigned vehicle.")
                if request.driver_id != user_employee:
                    raise ValidationError("You can only request fuel for yourself.")

    @api.constrains('vehicle_id', 'fuel_type_id')
    def _check_fuel_type_match(self):
        for request in self:
            if request.vehicle_id and request.fuel_type_id:
                if request.vehicle_id.custom_fuel_type_id.is_electric:
                    raise ValidationError(
                        f"This vehicle ({request.vehicle_id.name}) cannot request fuel because its fuel type is Electric."
                    )
                
                if request.fuel_type_id != request.vehicle_id.custom_fuel_type_id:
                    raise ValidationError(
                        f"You can only request the fuel type that your vehicle uses ({request.vehicle_id.custom_fuel_type_id.name})."
                    )

    @api.constrains('requested_quantity', 'vehicle_id', 'state', 'request_date', 'fuel_type_id')
    def _check_fuel_quota(self):
        for request in self:
            if request.state in ['rejected', 'draft']:
                continue
                
            if not request.vehicle_id or not request.fuel_type_id:
                continue
                
            if request.vehicle_id.custom_fuel_type_id.is_electric:
                raise ValidationError(
                    f"This vehicle ({request.vehicle_id.name}) cannot request fuel because its fuel type is Electric."
                )
            
            # Special case vehicles have unlimited quota - skip quota check
            if request.vehicle_id.special_case:
                continue
            
            quota_rec = self.env['fleet.fuel.quota'].sudo().search([
                ('fuel_type_id', '=', request.fuel_type_id.id)
            ], limit=1)
            
            if quota_rec:
                quota_val = quota_rec.fuel_quota
                if quota_val == 0:
                    continue
                    
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
                    ('vehicle_id', '=', request.vehicle_id.id),
                    ('fuel_type_id', '=', request.fuel_type_id.id),
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
                        f"The requested quantity of {request.requested_quantity} Liters exceeds the vehicle's monthly fuel quota "
                        f"for {request.fuel_type_id} ({quota_val} Liters per vehicle) for {month}/{year}.\n"
                        f"Vehicle: {request.vehicle_id.name}\n"
                        f"Total used by this vehicle this month: {total_used} Liters\n"
                        f"Remaining quota: {max(0.0, quota_val - total_used)} Liters"
                    )

    @api.constrains('vehicle_id')
    def _check_electric_vehicle(self):
        for request in self:
            if request.vehicle_id and request.vehicle_id.custom_fuel_type_id.is_electric:
                raise ValidationError(
                    f"This vehicle ({request.vehicle_id.name}) cannot request fuel because its fuel type is Electric."
                )

    @api.depends('driver_id')
    def _compute_requester_number(self):
        for request in self:
            request.requester_number = request.driver_id.user_id.id

    @api.depends('vehicle_fuel_type')
    def _compute_product_fields(self):
        for request in self:
            request.product_name = 'Fuel'
            request.product_type = request.vehicle_fuel_type or ''


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        employee = self.env.user.employee_id
        
        if employee and employee.is_fleet_driver:
            if 'driver_id' in fields_list and not res.get('driver_id'):
                res['driver_id'] = employee.id
            
            vehicle = self._get_driver_vehicle(employee.id)
            if vehicle:
                if not vehicle.custom_fuel_type_id.is_electric:
                    if 'vehicle_id' in fields_list and not res.get('vehicle_id'):
                        res['vehicle_id'] = vehicle.id
                    if 'fuel_type_id' in fields_list and not res.get('fuel_type_id'):
                        if vehicle.custom_fuel_type_id:
                            res['fuel_type_id'] = vehicle.custom_fuel_type_id.id
                else:
                    # For electric vehicles, set the vehicle but not fuel type
                    if 'vehicle_id' in fields_list and not res.get('vehicle_id'):
                        res['vehicle_id'] = vehicle.id
        
        if 'priority' in fields_list and not res.get('priority'):
            res['priority'] = 'medium'
        
        return res

    @api.model
    def write(self, vals):
        # Allow skip_state_check context to bypass restrictions (used internally by approve/issue actions)
        if self.env.context.get('skip_state_check'):
            return super().write(vals)

        if 'request_date' in vals:
            raise AccessError('Request Date cannot be modified. It is auto-set when the request is created.')
        
        if 'driver_id' in vals:
            raise AccessError('Driver cannot be modified manually. It is auto-set from the logged in user.')
        if 'vehicle_id' in vals:
            raise AccessError('Vehicle cannot be modified manually. It is auto-set from the driver.')
        if 'fuel_type_id' in vals:
            raise AccessError('Fuel Type cannot be modified manually. It is auto-filled from the vehicle.')
        
        # Fleet managers can freely update issue_date, issuer_id, issued_quantity, state
        is_fleet_manager = self.env.user.has_group('fleet_management.group_fleet_manager') or self.env.is_superuser()
        fleet_manager_fields = {'state', 'issue_date', 'issuer_id', 'issued_quantity', 'uom_id'}

        if is_fleet_manager:
            # For fleet managers, only restrict changes to draft-only fields when record is not draft
            draft_only_fields = ['requested_quantity', 'priority', 'reason']
            restricted_vals = {k: v for k, v in vals.items() if k in draft_only_fields}
            if restricted_vals:
                non_draft_records = self.filtered(lambda r: r.state != 'draft')
                if non_draft_records:
                    raise AccessError('You can only modify these fields when the request is in Draft state.')
        else:
            # Drivers can only edit limited fields in draft
            editable_fields = ['requested_quantity', 'priority', 'reason', 'uom_id']
            if any(field in vals for field in editable_fields):
                non_draft_records = self.filtered(lambda r: r.state != 'draft')
                if non_draft_records:
                    raise AccessError('You can only modify fields when the request is in Draft state.')
        
        return super().write(vals)
