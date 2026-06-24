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
    show_print_button = fields.Boolean(
        string='Show Print Button',
        compute='_compute_show_print_button',
        help='Determines if the print button should be visible',
    )
    dept_approved_by_id = fields.Many2one(
        'res.users', string='Dept. Approved By', readonly=True, copy=False,
    )
    fleet_approved_by_id = fields.Many2one(
        'res.users', string='Fleet Approved By', readonly=True, copy=False,
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

    @api.depends('state', 'assignment_ids.driver_id', 'requester_id')
    @api.depends_context('uid')
    def _compute_show_print_button(self):
        current_employee = self.env.user.employee_id
        is_fleet_manager = self.env.user.has_group('fleet_management.group_fleet_manager')
        is_dept_manager = self.env.user.has_group('fleet_management.group_department_manager')

        for request in self:
            if request.state in ['allocated', 'awaiting_confirmation', 'completed']:
                assigned_drivers = request.assignment_ids.filtered(
                    lambda a: a.status in ['assigned', 'returned']
                ).mapped('driver_id')
                
                is_driver = current_employee in assigned_drivers
                is_requester = request.requester_id == current_employee
                
                request.show_print_button = is_driver or is_requester or is_fleet_manager or is_dept_manager
            else:
                request.show_print_button = False

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
            'driver_confirmed', 'requester_confirmed',
            'dept_approved_by_id', 'fleet_approved_by_id',
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
        self.with_context(skip_state_check=True).write({
            'state': 'department_approved',
            'dept_approved_by_id': self.env.user.id,
        })
        for request in self:
            # Notify requester and department manager
            users = request._get_department_managers()
            if request.requester_id and request.requester_id.user_id:
                users |= request.requester_id.user_id
            if users:
                request._notify_users(users, "Your request is approved by department")
            request._notify_fleet_managers('department_approved')

    def action_fleet_approve(self):
        self._check_group(
            'fleet_management.group_fleet_manager',
            'Only Fleet Managers can approve vehicle requests for fleet allocation.',
        )
        self.with_context(skip_state_check=True).write({
            'state': 'fleet_approved',
            'fleet_approved_by_id': self.env.user.id,
        })
        for request in self:
            # Notify requester and department manager
            users = request._get_department_managers()
            if request.requester_id and request.requester_id.user_id:
                users |= request.requester_id.user_id
            if users:
                request._notify_users(users, "Your request is fully approved!")

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
            
            # Notify requester and department manager
            req_users = request._get_department_managers()
            if request.requester_id and request.requester_id.user_id:
                req_users |= request.requester_id.user_id
            if req_users:
                request._notify_users(req_users, "Trip allocated with vehicle/driver details")
            
            # Notify assigned drivers
            assigned_drivers = request.assignment_ids.filtered(
                lambda assignment: assignment.status == 'assigned'
            ).mapped('driver_id')
            driver_users = self.env['res.users']
            for driver in assigned_drivers:
                if driver.user_id:
                    driver_users |= driver.user_id
            if driver_users:
                request._notify_users(driver_users, "You are assigned as driver for this trip")

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
        actor_name = current_employee.name if current_employee else ('Driver' if actor == 'driver' else 'Requester')
        
        if actor == 'driver':
            # Case 1: Driver finishes first
            # 1. Driver receives confirmation feedback
            driver_message = f"You have successfully confirmed completion of Trip {self.name}.\nWaiting for the requester to confirm."
            self._notify_users(current_user, driver_message)
            
            # 2. Requester & Department Manager receive target notification
            other_users = self._get_department_managers()
            if self.requester_id and self.requester_id.user_id:
                other_users |= self.requester_id.user_id
            if other_users:
                requester_message = f"{actor_name} has confirmed, waiting for you"
                self._notify_users(other_users, requester_message)
                
        else:  # requester confirmed first
            # Case 2: Requester finishes first
            # 1. Requester receives confirmation feedback
            requester_message = f"You have successfully confirmed completion of Trip {self.name}.\nWaiting for the assigned driver."
            self._notify_users(current_user, requester_message)
            
            # 2. Driver receives target notification
            driver_users = self.env['res.users']
            for driver in assigned_drivers:
                if driver.user_id:
                    driver_users |= driver.user_id
            if driver_users:
                driver_message = f"{actor_name} has confirmed, waiting for you"
                self._notify_users(driver_users, driver_message)

    def _get_department_managers(self):
        managers = self.env['res.users']
        if self.department_id and self.department_id.manager_id and self.department_id.manager_id.user_id:
            managers |= self.department_id.manager_id.user_id
        if self.requester_id and self.requester_id.parent_id and self.requester_id.parent_id.user_id:
            managers |= self.requester_id.parent_id.user_id
        
        dept_manager_group = self.env.ref('fleet_management.group_department_manager', raise_if_not_found=False)
        if dept_manager_group:
            managers |= dept_manager_group.users.filtered(lambda u: u.active)
        return managers

    def _notify_users(self, users, message):
        """Helper to notify users. It posts the message to the record's chatter once, 
           and creates a custom.notification record for each user."""
        if not self or not users:
            return
        self.ensure_one()
        
        # Post to chatter once (displays on itself page)
        try:
            self.message_post(
                body=message,
                partner_ids=users.mapped('partner_id').ids,
            )
        except Exception as e:
            _logger.error(f"Error posting chatter to {self.name}: {str(e)}")
            
        # Create custom notification for each user
        for user in users:
            try:
                self.env['custom.notification'].create({
                    'title': f'Trip {self.name} - Status Update',
                    'user_id': user.id,
                    'message': message,
                    'is_read': False,
                })
            except Exception as e:
                _logger.error(f"Error creating custom notification for {user.name}: {str(e)}")

    def _send_notification(self, user, message):
        """Wrapper to support existing single user notifications"""
        self._notify_users(user, message)

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
            request.sudo()._return_completed_trip_assignments()
            
            # Notify both parties about completion
            request._notify_completion()

    def _notify_completion(self):
        """Send completion notifications to both parties with exact messages"""
        self.ensure_one()
        
        assigned_drivers = self.assignment_ids.filtered(
            lambda a: a.status == 'assigned'
        ).mapped('driver_id')
        
        users = self._get_department_managers()
        if self.requester_id and self.requester_id.user_id:
            users |= self.requester_id.user_id
        for driver in assigned_drivers:
            if driver.user_id:
                users |= driver.user_id
        
        if users:
            self._notify_users(users, "Trip completed successfully")

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
            request._notify_rejection()

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
        for request in self:
            users = request._get_department_managers()
            if request.requester_id and request.requester_id.user_id:
                users |= request.requester_id.user_id
            if users:
                request._notify_users(users, "Trip request reset to draft")
    
    def _notify_department_manager(self, action):
        for request in self:
            users = request._get_department_managers()
            if request.requester_id and request.requester_id.user_id:
                users |= request.requester_id.user_id
            if users:
                request.message_subscribe(partner_ids=users.mapped('partner_id').ids)
                request._notify_users(users, "New request pending approval")

    def _notify_fleet_managers(self, action):
        fleet_manager_group = self.env.ref('fleet_management.group_fleet_manager')
        fleet_managers = fleet_manager_group.users.filtered(lambda u: u.active)
        
        for request in self:
            if fleet_managers:
                partner_ids = fleet_managers.mapped('partner_id').ids
                request.message_subscribe(partner_ids=partner_ids)
                request._notify_users(fleet_managers, "Request approved by department, pending fleet approval")

    def _notify_requester(self, action):
        # Kept for compatibility / no-op
        pass

    def _notify_rejection(self):
        for request in self:
            if request.rejected_by_role == 'department_manager':
                users = request._get_department_managers()
                if request.requester_id and request.requester_id.user_id:
                    users |= request.requester_id.user_id
                if users:
                    request._notify_users(users, "Your request was rejected by department")
            elif request.rejected_by_role == 'fleet_manager':
                if request.requester_id and request.requester_id.user_id:
                    request._notify_users(request.requester_id.user_id, "Your request was rejected by fleet")
                managers = request._get_department_managers()
                if managers:
                    request._notify_users(managers, "Request was rejected by fleet")
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
