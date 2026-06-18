from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.osv import expression


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
    
    # NEW FIELDS FOR REJECTION TRACKING
    rejected_by = fields.Char(
        string='Rejected By',
        readonly=True,
        copy=False,
        tracking=True,
    )
    rejected_by_role = fields.Selection(
        selection=[
            ('department_manager', 'Department Manager'),
            ('fleet_manager', 'Fleet Manager'),
        ],
        string='Rejected By Role',
        readonly=True,
        copy=False,
        tracking=True,
    )
    rejection_details_display = fields.Html(
        string='Rejection Details',
        compute='_compute_rejection_details_display',
        readonly=True,
    )
    attachment_file = fields.Binary(string='Attachment / Document', attachment=True)
    attachment_filename = fields.Char(string='Attachment Filename')
    
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
        string='Can Finish Trip',
        compute='_compute_can_execute_current_user',
    )
    can_edit_requester = fields.Boolean(
        string='Can Edit Requester',
        compute='_compute_can_edit_requester',
    )
    can_edit_attachments = fields.Boolean(
        string='Can Edit Attachments',
        compute='_compute_can_edit_attachments',
    )
    is_editable = fields.Boolean(
        string='Is Editable',
        compute='_compute_is_editable',
        help='Determines if the record fields are editable based on state',
    )
    is_driver_assigned = fields.Boolean(
        string='Is Driver Assigned',
        compute='_compute_is_driver_assigned',
        help='Check if current user is assigned as driver for this trip',
    )
    show_reject_button = fields.Boolean(
        string='Show Reject Button',
        compute='_compute_show_reject_button',
        help='Determines if reject button should be shown based on state and user role',
    )

    @api.depends_context('uid')
    def _compute_can_edit_requester(self):
        can_edit = (
            self.env.user.has_group('fleet_management.group_department_manager')
        )
        for request in self:
            request.can_edit_requester = can_edit

    @api.depends('state')
    def _compute_is_editable(self):
        """All fields are editable ONLY in draft state for all users"""
        for request in self:
            request.is_editable = request.state == 'draft'

    @api.depends('state')
    @api.depends_context('uid')
    def _compute_can_edit_attachments(self):
        """Allow attachment editing only in draft state for all users"""
        for request in self:
            # Only editable when in draft state, regardless of user role
            request.can_edit_attachments = request.state == 'draft'

    @api.depends('assignment_ids.driver_id', 'assignment_ids.status')
    @api.depends_context('uid')
    def _compute_is_driver_assigned(self):
        """Check if current user is assigned as driver for this trip"""
        current_employee = self.env.user.employee_id
        for request in self:
            if current_employee:
                assigned_drivers = request.assignment_ids.filtered(
                    lambda a: a.status == 'assigned'
                ).mapped('driver_id')
                request.is_driver_assigned = current_employee in assigned_drivers
            else:
                request.is_driver_assigned = False

    @api.depends('state')
    @api.depends_context('uid')
    def _compute_show_reject_button(self):
        """Show reject button based on state and user role:
        - Department Manager: Show in 'submitted' state only
        - Fleet Manager: Show in 'department_approved' state only
        """
        is_dept_manager = self.env.user.has_group('fleet_management.group_department_manager')
        is_fleet_manager = self.env.user.has_group('fleet_management.group_fleet_manager')
        
        for request in self:
            if is_dept_manager and request.state == 'submitted':
                request.show_reject_button = True
            elif is_fleet_manager and request.state == 'department_approved':
                request.show_reject_button = True
            else:
                request.show_reject_button = False

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """
        Override search to implement visibility rules:
        - Fleet Manager: All requests.
        - Dept Manager: Requests in their department.
        - Regular User: Own requests only.
        - Driver: Trips assigned to them.
        """
        if not self.env.su and not self.env.user.has_group('fleet_management.group_fleet_manager'):
            user_employee = self.env.user.employee_id
            
            # Check if user is a department manager
            is_dept_manager = self.env.user.has_group('fleet_management.group_department_manager')
            
            if is_dept_manager and user_employee.department_id:
                # Department manager sees requests in their department
                domain = expression.AND([domain, [('department_id', '=', user_employee.department_id.id)]])
            else:
                # Regular users see:
                # 1. Their own requests
                # 2. Trips where they are assigned as driver
                combined_domain = [
                    '|',
                    ('requester_id.user_id', '=', self.env.uid),
                    ('assignment_ids.driver_id', '=', user_employee.id)
                ]
                domain = expression.AND([domain, combined_domain])
        
        return super()._search(domain, offset=offset, limit=limit, order=order)

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

    # NEW COMPUTE METHOD FOR REJECTION DETAILS DISPLAY
    @api.depends('rejection_reason', 'rejected_by', 'rejected_by_role', 'state')
    def _compute_rejection_details_display(self):
        for request in self:
            if request.state == 'rejected' and request.rejection_reason:
                role_display = dict(self._fields['rejected_by_role'].selection).get(
                    request.rejected_by_role, ''
                )
                request.rejection_details_display = f"""
                    <div class="alert alert-danger" role="alert">
                        <strong>Rejected by {role_display}: {request.rejected_by or 'Unknown'}</strong><br/>
                        <strong>Reason:</strong> {request.rejection_reason}
                    </div>
                """
            else:
                request.rejection_details_display = False

    @api.constrains('start_date', 'end_date')
    def _check_trip_dates(self):
        for request in self:
            if request.start_date and request.end_date and request.end_date < request.start_date:
                raise ValidationError('End Date must be after Start Date.')
            if request.start_date and request.request_date and request.start_date < request.request_date:
                raise ValidationError('Start Date must be after the Request Date.')

    # NEW CONSTRAINT FOR NUMBER OF PEOPLE
    @api.constrains('number_of_people')
    def _check_number_of_people(self):
        """Ensure number of people is greater than 0"""
        for request in self:
            if request.number_of_people <= 0:
                raise ValidationError('Number of people must be greater than 0.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.trip.request') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        # Define fields that should ALWAYS be allowed to be updated (system/state fields)
        always_allowed_fields = {
            'state', 'requester_executed', 'driver_executed', 
            'rejection_reason', 'rejected_by', 'rejected_by_role',
            'attachment_file', 'attachment_filename'
        }
        
        # Define fields that are allowed for Fleet Managers to edit after submission
        fleet_manager_allowed_fields = {
            'assignment_ids',  # Allow assignment management
        }
        
        if not self.env.context.get('skip_state_check', False):
            for request in self:
                if request.state != 'draft':
                    # Check if trying to modify any field
                    field_names = set(vals.keys())
                    
                    # Check for requester fields (fields that should not be edited after submission)
                    requester_fields = {
                        'name', 'requester_id', 'purpose', 'start_place', 
                        'destination', 'number_of_people', 'start_date', 'end_date',
                        'request_date'
                    }
                    
                    # Check if any requester fields are being modified
                    requester_field_changes = field_names & requester_fields
                    if requester_field_changes:
                        raise ValidationError(
                            f'You cannot edit fields after submission. The record is locked. '
                            f'Fields: {", ".join(requester_field_changes)} cannot be modified.'
                        )
                    
                    # Check if any other non-allowed fields are being modified
                    other_fields = field_names - always_allowed_fields - fleet_manager_allowed_fields - requester_fields
                    if other_fields:
                        # Check if user is fleet manager for assignment fields
                        if 'assignment_ids' in other_fields and self.env.user.has_group('fleet_management.group_fleet_manager'):
                            # Fleet manager can edit assignments, remove from other_fields
                            other_fields.remove('assignment_ids')
                        
                        if other_fields:
                            raise ValidationError(
                                f'You cannot edit fields after submission. The record is locked. '
                                f'Fields: {", ".join(other_fields)} cannot be modified.'
                            )
        
        if 'assignment_ids' in vals:
            for request in self:
                if request.state in ['allocated', 'completed', 'cancelled', 'rejected']:
                    raise ValidationError('You cannot add or modify vehicle assignments once the trip has been allocated or finished.')
        
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
            
            # Send notification to department manager
            request._notify_department_manager('submitted')

    def action_department_approve(self):
        self._check_group(
            'fleet_management.group_department_manager',
            'Only Department Managers can approve vehicle requests at department level.',
        )
        self.write({'state': 'department_approved'})
        
        # Send notification to fleet managers
        for request in self:
            request._notify_fleet_managers('department_approved')

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
        

    def action_finish_trip(self):
        current_employee = self.env.user.employee_id
        if not current_employee:
            raise AccessError('Your user must be linked to an employee to finish a trip.')

        for request in self:
            if request.state != 'allocated':
                raise ValidationError('Only allocated trips can be finished.')

            vals = {}
            is_requester = request.requester_id == current_employee
            
            assigned_drivers = request.assignment_ids.filtered(
                lambda assignment: assignment.status == 'assigned'
            ).mapped('driver_id')
            
            is_driver = current_employee in assigned_drivers

            if is_requester:
                vals['requester_executed'] = True
            if is_driver:
                vals['driver_executed'] = True
            if not vals:
                raise AccessError('Only the requester or assigned Driver can finish this trip.')

            request.write(vals)

            # Send notification to the other party
            if is_requester and assigned_drivers:
                # Notify all assigned drivers that requester executed
                for driver in assigned_drivers:
                    if driver.user_id:
                        request._create_notification(
                            driver.user_id,
                            f'Requester {current_employee.name} has confirmed execution of trip {request.name}.',
                            request.id,
                            request._name
                        )
            
            if is_driver and request.requester_id and request.requester_id.user_id:
                # Notify requester that driver executed
                request._create_notification(
                    request.requester_id.user_id,
                    f'Driver {current_employee.name} has confirmed execution of trip {request.name}.',
                    request.id,
                    request._name
                )

            if request.requester_executed and request.driver_executed:
                request._complete_trip()

    def _create_notification(self, user, message, res_id, res_model):
        """Helper method to create notification"""
        if user:
            # Create the mail message first
            mail_message = self.env['mail.message'].create({
                'body': message,
                'subject': 'Trip Status Update',
                'model': res_model,
                'res_id': res_id,
                'message_type': 'notification',
                'subtype_id': self.env.ref('mail.mt_note').id,
            })

            # Create the custom notification with the required message field
            self.env['custom.notification'].create({
                'title': 'Trip Status Update',
                'user_id': user.id,
                'message': message,  # Added to fulfill the mandatory field requirement
                'is_read': False,
            })


    def _complete_trip(self):
     for request in self:
        request.state = 'completed'
        # Notify requester and driver about completion
        request._notify_completion()
        # Return vehicle assignments to make vehicle available for next trip
        request._return_completed_trip_assignments()  # <-- ONLY THIS LINE ADDED

    def _return_completed_trip_assignments(self):
        for request in self.filtered(lambda trip: trip.state == 'completed'):
            assigned_assignments = request.assignment_ids.filtered(lambda assignment: assignment.status == 'assigned')
            if assigned_assignments:
                assigned_assignments.sudo().action_return_vehicle()

    def action_open_reject_wizard(self):
        self.ensure_one()
        
        # Check if current state allows rejection based on user role
        if self.state == 'submitted':
            self._check_group(
                'fleet_management.group_department_manager',
                'Only Department Managers can reject submitted vehicle requests.',
            )
        elif self.state == 'department_approved':
            self._check_group(
                'fleet_management.group_fleet_manager',
                'Only Fleet Managers can reject department approved vehicle requests.',
            )
        else:
            raise ValidationError('This request cannot be rejected in its current state.')
        
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
        """Handles the rejection of a trip request based on its current state."""
        for request in self:
            if request.state == 'submitted':
                request._check_group(
                    'fleet_management.group_department_manager',
                    'Only Department Managers can reject submitted vehicle requests.',
                )
                request.rejected_by_role = 'department_manager'
            elif request.state == 'department_approved':
                request._check_group(
                    'fleet_management.group_fleet_manager',
                    'Only Fleet Managers can reject department approved vehicle requests.',
                )
                request.rejected_by_role = 'fleet_manager'
            else:
                raise ValidationError('This request cannot be rejected in its current state.')
            
            request.rejected_by = self.env.user.name
            request.state = 'rejected'
            
            # Send notification to requester about rejection
            request._notify_requester('rejected')

    def action_cancel(self):
        """Cancels the request, restricted to the requester or department manager."""
        for request in self:
            if request.state not in ['draft']:  # Only cancel in draft state
                raise ValidationError('Vehicle requests can only be cancelled in draft state.')
            is_requester = (
                request.requester_id.user_id == self.env.user
                or request.create_uid == self.env.user
            )
            if not is_requester and not self.env.user.has_group('fleet_management.group_department_manager'):
                raise AccessError('Only the requester or Department Manager can cancel this request.')
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
            'rejection_reason': False,
            'rejected_by': False,
            'rejected_by_role': False,
        })
    
    # NOTIFICATION METHODS
    def _notify_department_manager(self, action):
        """Notify department manager about the request"""
        for request in self:
            if request.department_id and request.department_id.manager_id:
                manager_user = request.department_id.manager_id.user_id
                if manager_user:
                    request.message_subscribe(partner_ids=[manager_user.partner_id.id])
                    request.message_post(
                        body=f"<b>New Vehicle Request</b><br/>"
                             f"Request <b>{request.name}</b> has been submitted for your approval.<br/>"
                             f"<b>Destination:</b> {request.destination}<br/>"
                             f"<b>Start Date:</b> {request.start_date}<br/>"
                             f"<b>End Date:</b> {request.end_date}",
                        subject=f"Vehicle Request {request.name} - Pending Your Approval",
                        partner_ids=[manager_user.partner_id.id],
                    )

    def _notify_fleet_managers(self, action):
        """Notify fleet managers about department approval"""
        # Find all fleet managers
        fleet_manager_group = self.env.ref('fleet_management.group_fleet_manager')
        fleet_managers = fleet_manager_group.users
        
        for request in self:
            if fleet_managers:
                partner_ids = fleet_managers.mapped('partner_id').ids
                request.message_subscribe(partner_ids=partner_ids)
                request.message_post(
                    body=f"<b>Vehicle Request Department Approved</b><br/>"
                         f"Request <b>{request.name}</b> has been approved by department manager.<br/>"
                         f"<b>Department:</b> {request.department_id.name}<br/>"
                         f"<b>Requester:</b> {request.requester_id.name}<br/>"
                         f"<b>Destination:</b> {request.destination}<br/>"
                         f"<b>Start Date:</b> {request.start_date}<br/>"
                         f"<b>End Date:</b> {request.end_date}",
                    subject=f"Vehicle Request {request.name} - Department Approved - Pending Fleet Approval",
                    partner_ids=partner_ids,
                )

    def _notify_requester(self, action):
        """Notify requester about rejection"""
        for request in self:
            if request.requester_id and request.requester_id.user_id:
                requester_partner = request.requester_id.user_id.partner_id
                request.message_post(
                    body=f"<b>Vehicle Request Rejected</b><br/>"
                         f"Your request <b>{request.name}</b> has been rejected.<br/>"
                         f"<b>Rejected By:</b> {request.rejected_by}<br/>"
                         f"<b>Reason:</b> {request.rejection_reason}",
                    subject=f"Vehicle Request {request.name} - Rejected",
                    partner_ids=[requester_partner.id],
                )

    def _notify_completion(self):
        """Notify requester and driver about trip completion"""
        for request in self:
            # Notify requester
            if request.requester_id and request.requester_id.user_id:
                requester_partner = request.requester_id.user_id.partner_id
                request.message_post(
                    body=f"<b>Trip Completed</b><br/>"
                         f"Trip <b>{request.name}</b> has been completed.<br/>"
                         f"<b>Destination:</b> {request.destination}",
                    subject=f"Trip {request.name} - Completed",
                    partner_ids=[requester_partner.id],
                )
            
            # Notify assigned drivers
            assigned_drivers = request.assignment_ids.filtered(
                lambda a: a.status == 'assigned'
            ).mapped('driver_id')
            for driver in assigned_drivers:
                if driver.user_id:
                    request.message_post(
                        body=f"<b>Trip Completed</b><br/>"
                             f"Trip <b>{request.name}</b> has been completed.<br/>"
                             f"<b>Destination:</b> {request.destination}",
                        subject=f"Trip {request.name} - Completed",
                        partner_ids=[driver.user_id.partner_id.id],
                    )
    
    # NEW HELPER METHODS FOR REJECTION VISIBILITY
    def can_see_rejection_reason(self):
        """Check if current user can see the rejection reason"""
        self.ensure_one()
        current_employee = self.env.user.employee_id
        
        # Requester can always see rejection reason
        if self.requester_id == current_employee:
            return True
        
        # Department manager can see rejection reason (even if rejected by fleet manager)
        if self.env.user.has_group('fleet_management.group_department_manager'):
            return True
        
        # Fleet manager can see all rejection reasons
        if self.env.user.has_group('fleet_management.group_fleet_manager'):
            return True
        
        # Driver assigned to this trip can see rejection reason
        assigned_drivers = self.assignment_ids.filtered(
            lambda a: a.status == 'assigned'
        ).mapped('driver_id')
        if current_employee in assigned_drivers:
            return True
        
        return False

    def get_rejection_details(self):
        """Get formatted rejection details"""
        self.ensure_one()
        if not self.rejection_reason:
            return False
        
        role_display = dict(self._fields['rejected_by_role'].selection).get(
            self.rejected_by_role, 'Unknown'
        )
        
        return {
            'reason': self.rejection_reason,
            'rejected_by': self.rejected_by or 'Unknown',
            'rejected_by_role': role_display,
            'rejected_date': self.write_date if self.rejection_reason else False,
        }