from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.osv import expression


class FleetMaintenanceRequest(models.Model):
    _name = 'fleet.maintenance.request'
    _description = 'Vehicle Maintenance Request'
    _order = 'request_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Request Number', required=True, copy=False, readonly=True, default='New')
    is_manager = fields.Boolean(compute='_compute_is_manager')
    is_editable = fields.Boolean(compute='_compute_is_editable', store=False)
    show_as_label = fields.Boolean(compute='_compute_show_as_label', store=False)
    
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True)
    requested_by_id = fields.Many2one(
        'hr.employee',
        string='Requested By',
        default=lambda self: self.env.user.employee_id,
        tracking=True,
    )
    problem_description = fields.Text(string='Problem Description', required=True)
    request_date = fields.Datetime(
        string='Request Date', 
        default=fields.Datetime.now, 
        required=True,
        readonly=True  # Always readonly, auto-set from PC
    )
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
    notes = fields.Text(string='Maintenance Notes', tracking=True)
    
    attachment_file = fields.Binary(string='Attachment', attachment=True)
    attachment_filename = fields.Char(string='Attachment Filename')
    
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
    fleet_approved_by_id = fields.Many2one(
        'res.users', 
        string='Approved by (Fleet Manager)', 
        readonly=True, 
        copy=False
    )

    @api.depends('state')
    def _compute_is_editable(self):
        """
        Determine if fields should be editable:
        - Only problem_description and priority are editable
        - And only in draft state
        - vehicle_id, requested_by_id, request_date are ALWAYS locked
        """
        for request in self:
            # Only editable in draft state
            request.is_editable = request.state == 'draft'

    @api.depends('state')
    def _compute_show_as_label(self):
        """
        Determine if fields should show as labels (readonly text) instead of dropdowns
        - vehicle_id, requested_by_id, request_date ALWAYS show as labels
        - problem_description and priority show as editable in draft, labels after submission
        """
        for request in self:
            # vehicle, requested_by, request_date always show as labels
            request.show_as_label = True

    @api.depends('service_ids.cost')
    def _compute_total_service_cost(self):
        for request in self:
            request.total_service_cost = sum(request.service_ids.mapped('cost'))

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """
        Override search to implement visibility rules:
        - Fleet Manager: All requests.
        - Dept Manager: Requests from employees in their department.
        - Regular User: Own maintenance requests only.
        """
        if not self.env.su and not self.env.user.has_group('fleet_management.group_fleet_manager'):
            user_employee = self.env.user.employee_id
            if self.env.user.has_group('fleet_management.group_department_manager') and user_employee.department_id:
                domain = expression.AND([domain, [('requested_by_id.department_id', '=', user_employee.department_id.id)]])
            else:
                domain = expression.AND([domain, [('requested_by_id.user_id', '=', self.env.uid)]])
        
        return super()._search(domain, offset=offset, limit=limit, order=order)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.maintenance.request') or 'New'
            
            # Auto-set request_date to current time
            vals['request_date'] = fields.Datetime.now()
            
            # Auto-set requested_by from current user if not provided
            if not vals.get('requested_by_id'):
                employee = self.env.user.employee_id
                if employee:
                    vals['requested_by_id'] = employee.id
            
            # Auto-set vehicle from current driver if not provided
            if not vals.get('vehicle_id') and vals.get('requested_by_id'):
                employee = self.env['hr.employee'].browse(vals['requested_by_id'])
                vehicle = self.env['fleet.vehicle'].search([('current_driver_id', '=', employee.id)], limit=1)
                if vehicle:
                    vals['vehicle_id'] = vehicle.id
            
            # Auto-set priority if not provided
            if not vals.get('priority'):
                vals['priority'] = 'normal'
        
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
                    'title': f'Maintenance Request {self.name} - Status Update',
                    'user_id': user.id,
                    'message': message,
                    'is_read': False,
                })
            except Exception as e:
                pass

    def action_preview_attachment(self):
        self.ensure_one()
        if not self.attachment_file:
            return
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        attachment_url = f"/web/content/{self._name}/{self.id}/attachment_file/{self.attachment_filename}?download=false"
        
        return {
            'type': 'ir.actions.act_url',
            'url': attachment_url,
            'target': 'new',
        }


    def action_submit(self):
        for request in self:
            if not request.problem_description:
                raise ValidationError('Problem Description is required before submitting.')
            request._check_driver_vehicle()
            request.state = 'submitted'
            # Notify Fleet Manager
            fleet_manager_group = self.env.ref('fleet_management.group_fleet_manager')
            fleet_managers = fleet_manager_group.users.filtered(lambda u: u.active)
            if fleet_managers:
                request._notify_users(fleet_managers, "New maintenance request pending approval")
            # Notify Driver
            if request.requested_by_id and request.requested_by_id.user_id:
                request._notify_users(request.requested_by_id.user_id, "Your maintenance request has been submitted")

    def action_approve(self):
        self._check_fleet_manager()
        for request in self:
            if request.vehicle_id.fleet_status == 'retired':
                raise ValidationError('Retired vehicles cannot be sent for maintenance.')
            request.state = 'approved'
            request.fleet_approved_by_id = self.env.user.id
            # Notify Driver
            if request.requested_by_id and request.requested_by_id.user_id:
                request._notify_users(request.requested_by_id.user_id, "Your maintenance request has been approved")
            # Notify Fleet Managers
            fleet_manager_group = self.env.ref('fleet_management.group_fleet_manager')
            fleet_managers = fleet_manager_group.users.filtered(lambda u: u.active)
            if fleet_managers:
                request._notify_users(fleet_managers, f"Maintenance request {request.name} approved")
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
        # Notify Driver
        if self.requested_by_id and self.requested_by_id.user_id:
            self._notify_users(self.requested_by_id.user_id, "Your maintenance request has been rejected")
        # Notify Fleet Managers
        fleet_manager_group = self.env.ref('fleet_management.group_fleet_manager')
        fleet_managers = fleet_manager_group.users.filtered(lambda u: u.active)
        if fleet_managers:
            self._notify_users(fleet_managers, f"Maintenance request {self.name} has been rejected")

    def action_reset_to_draft(self):
        self._check_fleet_manager()
        self.write({'state': 'draft'})

    @api.depends_context('uid')
    def _compute_is_manager(self):
        for request in self:
            request.is_manager = self.env.user.has_group('fleet_management.group_fleet_manager')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        employee = self.env.user.employee_id
        if employee:
            vehicle = self.env['fleet.vehicle'].search([('current_driver_id', '=', employee.id)], limit=1)
            if vehicle:
                if 'vehicle_id' in fields_list and not res.get('vehicle_id'):
                    res['vehicle_id'] = vehicle.id
            # Set default priority
            if 'priority' in fields_list and not res.get('priority'):
                res['priority'] = 'normal'
        return res

    @api.model
    def write(self, vals):
        # Block editing of request_date (always readonly)
        if 'request_date' in vals:
            raise AccessError('Request Date cannot be modified. It is auto-set when the request is created.')
        
        # Block editing of vehicle_id and requested_by_id (ALWAYS locked)
        restricted_fields = ['vehicle_id', 'requested_by_id']
        if any(field in vals for field in restricted_fields):
            raise AccessError('Vehicle and Requested By cannot be modified. They are auto-assigned.')
        
        # Check if user is a driver (not manager)
        is_driver = not self.env.user.has_group('fleet_management.group_fleet_manager')
        
        # Only allow problem_description and priority edits in draft state
        editable_fields = ['problem_description', 'priority']
        if any(field in vals for field in editable_fields):
            non_draft_records = self.filtered(lambda r: r.state != 'draft')
            if non_draft_records:
                raise AccessError('You can only modify fields when the request is in Draft state.')
        
        return super().write(vals)