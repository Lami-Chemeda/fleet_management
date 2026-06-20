from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)


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
            ('awaiting_confirmation', 'Awaiting Confirmation'),
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
    
    driver_confirmed = fields.Boolean(string='Driver Confirmed', default=False, tracking=True)
    requester_confirmed = fields.Boolean(string='Requester Confirmed', default=False, tracking=True)
    
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
        """Show reject button based on state and user role"""
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
        """Override search to implement visibility rules"""
        if not self.env.su and not self.env.user.has_group('fleet_management.group_fleet_manager'):
            user_employee = self.env.user.employee_id
            is_dept_manager = self.env.user.has_group('fleet_management.group_department_manager')
            
            if is_dept_manager and user_employee.department_id:
                domain = expression.AND([domain, [('department_id', '=', user_employee.department_id.id)]])
            else:
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
            allowed_states = ['allocated', 'awaiting_confirmation']
            assigned_drivers = request.assignment_ids.filtered(
                lambda assignment: assignment.status == 'assigned'
            ).mapped('driver_id')
            request.can_execute_current_user = bool(
                request.state in allowed_states
                and current_employee
                and not is_fleet_manager
                and (
                    request.requester_id == current_employee
                    or current_employee in assigned_drivers
                )
            )

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

    @api.constrains('number_of_people')
    def _check_number_of_people(self):
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
        # CRITICAL FIX: Check if we're in a completion flow to prevent recursion
        if self.env.context.get('_skip_completion_flow'):
            return super().write(vals)
        
        always_allowed_fields = {
            'state', 'requester_executed', 'driver_executed', 
            'rejection_reason', 'rejected_by', 'rejected_by_role',
            'attachment_file', 'attachment_filename',
            'driver_confirmed', 'requester_confirmed'
        }
        
        fleet_manager_allowed_fields = {
            'assignment_ids',
        }
        
        if not self.env.context.get('skip_state_check', False):
            for request in self:
                if request.state != 'draft':
                    field_names = set(vals.keys())
                    requester_fields = {
                        'name', 'requester_id', 'purpose', 'start_place', 
                        'destination', 'number_of_people', 'start_date', 'end_date',
                        'request_date'
                    }
                    
                    requester_field_changes = field_names & requester_fields
                    if requester_field_changes:
                        raise ValidationError(
                            f'You cannot edit fields after submission. The record is locked. '
                            f'Fields: {", ".join(requester_field_changes)} cannot be modified.'
                        )
                    
                    other_fields = field_names - always_allowed_fields - fleet_manager_allowed_fields - requester_fields
                    if other_fields:
                        if 'assignment_ids' in other_fields and self.env.user.has_group('fleet_management.group_fleet_manager'):
                            other_fields.remove('assignment_ids')
                        
                        if other_fields:
                            raise ValidationError(
                                f'You cannot edit fields after submission. The record is locked. '
                                f'Fields: {", ".join(other_fields)} cannot be modified.'
                            )
        
        if 'assignment_ids' in vals:
            for request in self:
                if request.state in ['allocated', 'awaiting_confirmation', 'completed', 'cancelled', 'rejected']:
                    raise ValidationError('You cannot add or modify vehicle assignments once the trip has been allocated or finished.')
        
        result = super().write(vals)
        
        # IMPORTANT: When state changes to completed, return the vehicle
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
            request._notify_department_manager('submitted')

    def action_department_approve(self):
        self._check_group(
            'fleet_management.group_department_manager',
            'Only Department Managers can approve vehicle requests at department level.',
        )
        self.write({'state': 'department_approved'})
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
            
            # Reset confirmation flags when allocating
            request.write({
                'state': 'allocated',
                'requester_executed': False,
                'driver_executed': False,
                'requester_confirmed': False,
                'driver_confirmed': False,
            })

    def action_complete(self):
        self._check_group(
            'fleet_management.group_fleet_manager',
            'Only Fleet Managers can manually complete a trip.',
        )
        self._complete_trip()

    def action_finish_trip(self):
        """Handles the Finish Trip button with two-confirmation flow"""
        current_employee = self.env.user.employee_id
        if not current_employee:
            raise AccessError('Your user must be linked to an employee to finish a trip.')

        for request in self:
            if request.state not in ['allocated', 'awaiting_confirmation']:
                raise ValidationError('Only allocated trips can be finished.')

            if request.state == 'completed':
                raise ValidationError('This trip is already completed.')
            
            is_requester = request.requester_id == current_employee
            
            assigned_drivers = request.assignment_ids.filtered(
                lambda assignment: assignment.status == 'assigned'
            ).mapped('driver_id')
            
            is_driver = current_employee in assigned_drivers

            if not is_requester and not is_driver:
                raise AccessError('Only the requester or assigned Driver can finish this trip.')

            if is_requester and request.requester_confirmed:
                raise ValidationError('You have already confirmed this trip.')
            if is_driver and request.driver_confirmed:
                raise ValidationError('You have already confirmed this trip.')

            vals = {}
            if is_requester:
                vals['requester_confirmed'] = True
                vals['requester_executed'] = True
                actor = 'requester'
            if is_driver:
                vals['driver_confirmed'] = True
                vals['driver_executed'] = True
                actor = 'driver'

            request.write(vals)

            if request.requester_confirmed and request.driver_confirmed:
                request._complete_trip()
            else:
                request.state = 'awaiting_confirmation'
                request._notify_awaiting_confirmation(actor)

    def _notify_awaiting_confirmation(self, actor):
        """Send notifications when one party confirms and waiting for the other"""
        self.ensure_one()
        
        assigned_drivers = self.assignment_ids.filtered(
            lambda a: a.status == 'assigned'
        ).mapped('driver_id')
        
        current_user = self.env.user
        current_employee = current_user.employee_id
        
        if actor == 'driver':
            # Case 1: Driver finishes first
            driver_name = current_employee.name if current_employee else 'Driver'
            
            # 1. Driver receives: "You have successfully confirmed completion of Trip TRIP-001. Waiting for the requester to confirm."
            driver_message = f"You have successfully confirmed completion of Trip {self.name}.\nWaiting for the requester to confirm."
            self._send_notification(current_user, driver_message)
            
            # 2. Requester receives: "Driver John has confirmed execution of Trip TRIP-001. Please confirm the trip to complete it."
            if self.requester_id and self.requester_id.user_id:
                requester_message = f"Driver {driver_name} has confirmed execution of Trip {self.name}.\nPlease confirm the trip to complete it."
                self._send_notification(self.requester_id.user_id, requester_message)
                
        else:  # requester confirmed first
            # Case 2: Requester finishes first
            requester_name = current_employee.name if current_employee else 'Requester'
            
            # 1. Requester receives: "You have successfully confirmed completion of Trip TRIP-001. Waiting for the assigned driver."
            requester_message = f"You have successfully confirmed completion of Trip {self.name}.\nWaiting for the assigned driver."
            self._send_notification(current_user, requester_message)
            
            # 2. Driver receives: "Requester John has confirmed execution of Trip TRIP-001. Please confirm the trip."
            for driver in assigned_drivers:
                if driver.user_id:
                    driver_message = f"Requester {requester_name} has confirmed execution of Trip {self.name}.\nPlease confirm the trip."
                    self._send_notification(driver.user_id, driver_message)

    def _send_notification(self, user, message):
        """Helper method to send notification to a specific user"""
        if not user:
            return
        
        try:
            # Replace newlines with HTML line breaks for chatter
            html_message = message.replace('\n', '<br/>')
            
            # Post to chatter
            self.message_post(
                body="<b>Trip Status Update</b><br/>" + html_message,
                subject=f"Trip {self.name} - Status Update",
                partner_ids=[user.partner_id.id],
            )
            
            # Create custom notification
            try:
                self.env['custom.notification'].create({
                    'title': f'Trip {self.name} - Status Update',
                    'user_id': user.id,
                    'message': message,
                    'is_read': False,
                })
            except Exception:
                pass
        except Exception as e:
            _logger.error(f"Error sending notification to {user.name}: {str(e)}")

    def _complete_trip(self):
        """Complete the trip and send completion notifications"""
        for request in self:
            if request.state == 'completed':
                return
            
            _logger.info(f"=== _complete_trip called for {request.name} ===")
            
            # Use context flag to prevent recursion
            request.with_context(_skip_completion_flow=True).write({
                'state': 'completed'
            })
            
            # CRITICAL: Immediately return the vehicle assignment
            request._return_completed_trip_assignments()
            
            # Notify both parties about completion
            request._notify_completion()

    def _notify_completion(self):
        """Send completion notifications to both parties with exact messages"""
        self.ensure_one()
        
        assigned_drivers = self.assignment_ids.filtered(
            lambda a: a.status == 'assigned'
        ).mapped('driver_id')
        
        # Notify requester
        if self.requester_id and self.requester_id.user_id:
            # Requester receives: "Trip TRIP-001 has been completed successfully."
            requester_message = f"Trip {self.name} has been completed successfully."
            self._send_notification(self.requester_id.user_id, requester_message)
            
            # Requester also receives: "Driver has confirmed. Trip TRIP-001 is now completed."
            requester_second_message = f"Driver has confirmed.\nTrip {self.name} is now completed."
            self._send_notification(self.requester_id.user_id, requester_second_message)
        
        # Notify assigned drivers
        for driver in assigned_drivers:
            if driver.user_id:
                # Driver receives: "Trip TRIP-001 has been completed successfully."
                driver_message = f"Trip {self.name} has been completed successfully."
                self._send_notification(driver.user_id, driver_message)
                
                # Driver also receives: "Requester has confirmed. Trip TRIP-001 is now completed."
                driver_second_message = f"Requester has confirmed.\nTrip {self.name} is now completed."
                self._send_notification(driver.user_id, driver_second_message)

    def _return_completed_trip_assignments(self):
        """Return vehicle assignments and make vehicles available"""
        _logger.info("=== _return_completed_trip_assignments called ===")
        
        for request in self.filtered(lambda trip: trip.state == 'completed'):
            _logger.info(f"Processing completed trip: {request.name}")
            
            # Get all assigned assignments for this trip
            assigned_assignments = request.assignment_ids.filtered(
                lambda assignment: assignment.status == 'assigned'
            )
            
            _logger.info(f"Found {len(assigned_assignments)} assigned assignments")
            
            if not assigned_assignments:
                _logger.warning(f"No assigned assignments found for trip {request.name}")
                continue
            
            for assignment in assigned_assignments:
                try:
                    _logger.info(f"Processing assignment {assignment.id}")
                    
                    # Step 1: Update vehicle status to 'available'
                    if assignment.vehicle_id:
                        assignment.vehicle_id.sudo().write({
                            'fleet_status': 'available'
                        })
                        _logger.info(f"Updated vehicle {assignment.vehicle_id.name} status to 'available'")
                    
                    # Step 2: Update assignment status to 'returned'
                    assignment.sudo().write({
                        'status': 'returned',
                        'return_date': fields.Datetime.now()
                    })
                    _logger.info(f"Updated assignment {assignment.id} status to 'returned'")
                    
                    # Step 3: Create vehicle history entry
                    try:
                        self.env['fleet.vehicle.history'].sudo().create({
                            'vehicle_id': assignment.vehicle_id.id,
                            'event_type': 'returned',
                            'event_date': fields.Datetime.now(),
                            'driver_id': assignment.driver_id.id if assignment.driver_id else False,
                            'description': f'Vehicle returned from completed trip {request.name}.',
                            'odometer': assignment.vehicle_id.current_odometer if assignment.vehicle_id else 0,
                        })
                        _logger.info(f"Created vehicle history entry")
                    except Exception as e:
                        _logger.warning(f"Could not create vehicle history entry: {str(e)}")
                    
                except Exception as e:
                    _logger.error(f"Error returning vehicle assignment {assignment.id}: {str(e)}")
                    # Continue with next assignment even if one fails

    def action_open_reject_wizard(self):
        self.ensure_one()
        
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
            request._notify_requester('rejected')

    def action_cancel(self):
        for request in self:
            if request.state not in ['draft']:
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
            'requester_confirmed': False,
            'driver_confirmed': False,
        })
    
    def _notify_department_manager(self, action):
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
    
    def can_see_rejection_reason(self):
        self.ensure_one()
        current_employee = self.env.user.employee_id
        
        if self.requester_id == current_employee:
            return True
        
        if self.env.user.has_group('fleet_management.group_department_manager'):
            return True
        
        if self.env.user.has_group('fleet_management.group_fleet_manager'):
            return True
        
        assigned_drivers = self.assignment_ids.filtered(
            lambda a: a.status == 'assigned'
        ).mapped('driver_id')
        if current_employee in assigned_drivers:
            return True
        
        return False

    def get_rejection_details(self):
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