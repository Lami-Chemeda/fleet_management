import logging
import re
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_fleet_driver = fields.Boolean(
        string='Fleet Driver',
        default=False,
    )
    is_fleet_user = fields.Boolean(
        string='Fleet User',
        default=True,
    )
    is_fleet_manager = fields.Boolean(
        string='Fleet Manager',
    )
    is_department_manager = fields.Boolean(
        string='Department Manager',
    )
    fleet_role = fields.Selection(
        selection=[
            ('employee', 'No Fleet Role'),
            ('fleet_user', 'Fleet User'),
            ('driver', 'Driver'),
            ('fleet_manager', 'Fleet Manager'),
            ('department_manager', 'Department Manager'),
        ],
        string='Fleet Management Role',
        default='fleet_user',
    )
    driver_source_employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        copy=False,
        domain="[('is_fleet_user', '=', False), ('is_fleet_driver', '=', False), ('is_fleet_manager', '=', False), ('is_department_manager', '=', False)]",
    )
    current_vehicle_ids = fields.One2many(
        comodel_name='fleet.vehicle',
        inverse_name='current_driver_id',
        string='Current Vehicles',
    )
    driver_license_number = fields.Char(
        string='Driver License Number',
        copy=False,
    )
    driver_license_category = fields.Selection(
        selection=[
            ('a', 'A'),
            ('b', 'B'),
            ('c', 'C'),
            ('d', 'D'),
            ('e', 'E'),
            ('other', 'Other'),
        ],
        string='License Category / Level',
    )
    driver_license_issue_date = fields.Date(
        string='License Issue Date',
    )
    driver_license_expiry_date = fields.Date(
        string='License Expiry Date',
    )
    driver_license_suspended = fields.Boolean(
        string='License Suspended',
    )
    driver_license_image = fields.Binary(
        string='Driver License Copy',
        attachment=True,
    )
    driver_license_status = fields.Selection(
        selection=[
            ('valid', 'Valid'),
            ('expired', 'Expired'),
            ('suspended', 'Suspended'),
        ],
        string='License Status',
        compute='_compute_driver_license_status',
        store=True,
    )

    @api.depends('driver_license_expiry_date', 'driver_license_suspended')
    def _compute_driver_license_status(self):
        today = fields.Date.today()
        for employee in self:
            if employee.driver_license_suspended:
                employee.driver_license_status = 'suspended'
            elif employee.driver_license_expiry_date and employee.driver_license_expiry_date < today:
                employee.driver_license_status = 'expired'
            elif employee.driver_license_expiry_date:
                employee.driver_license_status = 'valid'
            else:
                employee.driver_license_status = False

    @api.constrains('fleet_role', 'is_fleet_driver', 'driver_license_number', 'driver_license_category', 'driver_license_issue_date', 'driver_license_expiry_date', 'driver_license_image')
    def _check_driver_license_info(self):
        """Ensure all required license info is provided for employees with the Driver role."""
        for employee in self:
            if employee.fleet_role == 'driver' or employee.is_fleet_driver:
                missing_fields = []
                if not employee.driver_license_number:
                    missing_fields.append("License Number")
                if not employee.driver_license_category:
                    missing_fields.append("License Category / Level")
                if not employee.driver_license_issue_date:
                    missing_fields.append("License Issue Date")
                if not employee.driver_license_expiry_date:
                    missing_fields.append("License Expiry Date")
                if not employee.driver_license_image:
                    missing_fields.append("License Copy (Image Scan)")
                
                if missing_fields:
                    raise ValidationError(
                        _("The following fields are required for the Driver role:\n- %s") % "\n- ".join(missing_fields)
                    )

    @api.constrains('work_phone', 'mobile_phone')
    def _check_ethiopian_phone_number(self):
        """ Validates Ethiopian phone formats for +251 (13 characters) and 0 (10 characters). """
        for record in self:
            for phone in [record.work_phone, record.mobile_phone]:
                if not phone:
                    continue
                # Must start with +251 or 0
                if phone.startswith('+251'):
                    if not re.match(r'^\+251[79]\d{8}$', phone):
                        raise ValidationError(_(
                            "Invalid Phone: %s. Numbers starting with +251 must be 13 characters long "
                            "and the next digit must be 7 or 9."
                        ) % phone)
                elif phone.startswith('0'):
                    if not re.match(r'^0[79]\d{8}$', phone):
                        raise ValidationError(_(
                            "Invalid Phone: %s. Numbers starting with 0 must be 10 characters long "
                            "and the next digit must be 7 or 9."
                        ) % phone)
                else:
                    raise ValidationError(_(
                        "Invalid Phone: %s. Phone numbers must start with '+251' (13 characters) "
                        "or '0' (10 characters)."
                    ) % phone)

    @api.onchange('fleet_role')
    def _onchange_fleet_role(self):
        for employee in self:
            employee._apply_fleet_role_selection()

    @api.onchange('is_fleet_user', 'is_fleet_driver', 'is_fleet_manager', 'is_department_manager')
    def _onchange_fleet_role_flags(self):
        for employee in self:
            employee.fleet_role = employee._get_primary_fleet_role_from_flags()

    @api.onchange('driver_source_employee_id')
    def _onchange_driver_source_employee_id(self):
        fields_to_copy = (
            'name',
            'job_title',
            'work_email',
            'work_phone',
            'mobile_phone',
            'department_id',
            'job_id',
            'parent_id',
            'company_id',
            'work_contact_id',
            'user_id',
            'image_1920',
        )
        for employee in self:
            source_employee = employee.driver_source_employee_id
            if not source_employee:
                continue
            for field_name in fields_to_copy:
                employee[field_name] = source_employee[field_name]
            employee.fleet_role = 'driver'
            employee.is_fleet_driver = True
            employee.is_fleet_user = True

    @api.model_create_multi
    def create(self, vals_list):
        driver_employees = self.browse()
        vals_to_create = []
        
        # Check if current user is admin
        is_admin = self.env.is_admin() or self.env.user.has_group('base.group_system')
        
        for vals in vals_list:
            # AUTO-ASSIGN FLEET USER FOR ADMIN-CREATED EMPLOYEES
            if is_admin and not vals.get('driver_source_employee_id'):
                # Only auto-assign if no fleet role is already set
                if not vals.get('fleet_role') and not vals.get('is_fleet_user'):
                    vals['fleet_role'] = 'fleet_user'
                    vals['is_fleet_user'] = True
            
            driver_source_employee_id = vals.pop('driver_source_employee_id', False)
            if driver_source_employee_id:
                driver_employee = self.browse(driver_source_employee_id).exists()
                if driver_employee:
                    driver_employee.write(self._prepare_driver_source_employee_vals(vals))
                    driver_employees |= driver_employee
                    continue
            self._normalize_fleet_role_vals(vals, set_selection_from_flags=True)
            vals_to_create.append(vals)
        
        employees = super().create(vals_to_create) if vals_to_create else self.browse()
        employees_to_sync = employees.browse()

        # Assign default Odoo Fleet group for users linked to employees
        fleet_group = self.env.ref('fleet.group_fleet_user', raise_if_not_found=False)
        
        for employee in employees:
            if employee.fleet_role != 'employee':
                employees_to_sync |= employee
            
            if employee.user_id and fleet_group:
                employee.user_id.sudo().write({'groups_id': [fields.Command.link(fleet_group.id)]})

        if employees_to_sync:
            employees_to_sync._sync_fleet_role_to_user()
        
        return employees | driver_employees

    def write(self, vals):
        self._normalize_fleet_role_vals(vals)
        result = super().write(vals)
        if self._has_fleet_role_vals(vals):
            if 'fleet_role' not in vals and {
                'is_fleet_user',
                'is_fleet_driver',
                'is_department_manager',
                'is_fleet_manager',
            }.intersection(vals):
                self._update_fleet_role_selection_from_flags()
            self._sync_fleet_role_to_user()
        elif 'user_id' in vals:
            self.filtered(lambda employee: employee._has_any_fleet_role())._sync_fleet_role_to_user()
        return result

    def _sync_fleet_role_to_user(self):
        managed_groups = self._get_managed_fleet_groups()
        for employee in self.filtered('user_id'):
            commands = [(3, group.id) for group in managed_groups]
            for group_xmlid in employee._get_fleet_role_group_xmlids():
                role_group = self.env.ref(group_xmlid, raise_if_not_found=False)
                if role_group:
                    commands.append((4, role_group.id))
            if commands:
                employee.user_id.sudo().write({'groups_id': commands})

    def _get_managed_fleet_groups(self):
        group_xmlids = (
            'fleet_management.group_fleet_user',
            'fleet_management.group_fleet_driver',
            'fleet_management.group_department_manager',
            'fleet_management.group_fleet_manager',
        )
        return self.env['res.groups'].browse([
            group.id
            for group in (
                self.env.ref(group_xmlid, raise_if_not_found=False)
                for group_xmlid in group_xmlids
            )
            if group
        ])

    def _prepare_driver_source_employee_vals(self, vals):
        allowed_fields = {
            'driver_license_number',
            'driver_license_category',
            'driver_license_issue_date',
            'driver_license_expiry_date',
            'driver_license_suspended',
        }
        driver_vals = {
            field_name: vals[field_name]
            for field_name in allowed_fields
            if field_name in vals
        }
        driver_vals.update({
            'fleet_role': 'driver',
            'is_fleet_user': True,
            'is_fleet_driver': True,
        })
        return driver_vals

    def _apply_fleet_role_selection(self):
        self.ensure_one()
        if self.fleet_role == 'employee':
            self.is_fleet_user = False
            self.is_fleet_driver = False
            self.is_department_manager = False
            self.is_fleet_manager = False
        else:
            self.is_fleet_user = True
            self.is_fleet_driver = (self.fleet_role == 'driver')
            self.is_department_manager = (self.fleet_role == 'department_manager')
            self.is_fleet_manager = (self.fleet_role == 'fleet_manager')

    def _get_primary_fleet_role_from_flags(self):
        self.ensure_one()
        if self.is_fleet_manager:
            return 'fleet_manager'
        if self.is_department_manager:
            return 'department_manager'
        if self.is_fleet_driver:
            return 'driver'
        if self.is_fleet_user:
            return 'fleet_user'
        return 'employee'

    def _has_any_fleet_role(self):
        self.ensure_one()
        return any((
            self.is_fleet_user,
            self.is_fleet_driver,
            self.is_department_manager,
            self.is_fleet_manager,
        ))

    def _get_fleet_role_group_xmlids(self):
        self.ensure_one()
        group_xmlids = []
        if self.is_fleet_user:
            group_xmlids.append('fleet_management.group_fleet_user')
        if self.is_fleet_driver:
            group_xmlids.append('fleet_management.group_fleet_driver')
        if self.is_department_manager:
            group_xmlids.append('fleet_management.group_department_manager')
        if self.is_fleet_manager:
            group_xmlids.append('fleet_management.group_fleet_manager')
        return group_xmlids

    def _has_fleet_role_vals(self, vals):
        return bool({
            'fleet_role',
            'is_fleet_user',
            'is_fleet_driver',
            'is_department_manager',
            'is_fleet_manager',
        }.intersection(vals))

    def _normalize_fleet_role_vals(self, vals, set_selection_from_flags=False):
        if not self._has_fleet_role_vals(vals):
            return
        if vals.get('fleet_role') and not {
            'is_fleet_user',
            'is_fleet_driver',
            'is_department_manager',
            'is_fleet_manager',
        }.intersection(vals):
            role = vals['fleet_role']
            vals.update({
                'is_fleet_user': role in ('fleet_user', 'driver', 'department_manager', 'fleet_manager'),
                'is_fleet_driver': role == 'driver',
                'is_department_manager': role == 'department_manager',
                'is_fleet_manager': role == 'fleet_manager',
            })
        if vals.get('is_fleet_driver') or vals.get('is_department_manager') or vals.get('is_fleet_manager'):
            vals.setdefault('is_fleet_user', True)
        if set_selection_from_flags and any(field in vals for field in ('is_fleet_user', 'is_fleet_driver', 'is_department_manager', 'is_fleet_manager')):
            if vals.get('is_fleet_manager'):
                vals['fleet_role'] = 'fleet_manager'
            elif vals.get('is_department_manager'):
                vals['fleet_role'] = 'department_manager'
            elif vals.get('is_fleet_driver'):
                vals['fleet_role'] = 'driver'
            elif vals.get('is_fleet_user'):
                vals['fleet_role'] = 'fleet_user'
            else:
                vals['fleet_role'] = 'employee'

    def _update_fleet_role_selection_from_flags(self):
        for employee in self:
            primary_role = employee._get_primary_fleet_role_from_flags()
            if employee.fleet_role != primary_role:
                super(HrEmployee, employee).write({'fleet_role': primary_role})

    def ensure_department_managers_have_employee(self):
        """
        Ensure all department managers have employee records linked to their user.
        Call this method to fix missing employee records for department managers.
        """
        department_manager_group = self.env.ref('fleet_management.group_department_manager', raise_if_not_found=False)
        if not department_manager_group:
            _logger.warning('Department manager group not found. Skipping employee creation.')
            return
        
        created_count = 0
        for user in department_manager_group.users:
            if not user.employee_id:
                # Create employee record for this user
                self.env['hr.employee'].create({
                    'name': user.name,
                    'user_id': user.id,
                    'work_email': user.email,
                    'is_department_manager': True,
                    'fleet_role': 'department_manager',
                })
                created_count += 1
                _logger.info(f'Created employee record for department manager: {user.name}')
        
        if created_count:
            _logger.info(f'Successfully created {created_count} employee records for department managers')
        else:
            _logger.info('No new employee records needed for department managers')


class ResUsers(models.Model):
    _inherit = 'res.users'

    fleet_role = fields.Selection(
        selection=[
            ('employee', 'No Fleet Role'),
            ('fleet_user', 'Fleet User'),
            ('driver', 'Driver'),
            ('fleet_manager', 'Fleet Manager'),
            ('department_manager', 'Department Manager'),
        ],
        string='Fleet Management Role',
        default='fleet_user',
    )
    is_fleet_user = fields.Boolean(
        string='Fleet User',
        default=True,
    )
    is_fleet_driver = fields.Boolean(
        string='Is a Driver',
        default=False,
    )
    is_fleet_manager = fields.Boolean(
        string='Fleet Manager',
        default=False,
    )
    is_department_manager = fields.Boolean(
        string='Department Manager',
        default=False,
    )

    driver_license_number = fields.Char(
        string='Driver License Number',
        copy=False,
    )
    driver_license_category = fields.Selection(
        selection=[
            ('a', 'A'),
            ('b', 'B'),
            ('c', 'C'),
            ('d', 'D'),
            ('e', 'E'),
            ('other', 'Other'),
        ],
        string='License Category / Level',
    )
    driver_license_issue_date = fields.Date(
        string='License Issue Date',
    )
    driver_license_expiry_date = fields.Date(
        string='License Expiry Date',
    )
    driver_license_suspended = fields.Boolean(
        string='License Suspended',
    )
    driver_license_image = fields.Binary(
        string='Driver License Copy',
        attachment=True,
    )
    driver_license_status = fields.Selection(
        selection=[
            ('valid', 'Valid'),
            ('expired', 'Expired'),
            ('suspended', 'Suspended'),
        ],
        string='License Status',
        compute='_compute_driver_license_status',
        store=True,
    )

    @api.depends('driver_license_expiry_date', 'driver_license_suspended')
    def _compute_driver_license_status(self):
        today = fields.Date.today()
        for user in self:
            if user.driver_license_suspended:
                user.driver_license_status = 'suspended'
            elif user.driver_license_expiry_date and user.driver_license_expiry_date < today:
                user.driver_license_status = 'expired'
            elif user.driver_license_expiry_date:
                user.driver_license_status = 'valid'
            else:
                user.driver_license_status = False

    @api.onchange('fleet_role')
    def _onchange_fleet_role(self):
        for user in self:
            if user.fleet_role == 'employee':
                user.is_fleet_user = False
                user.is_fleet_driver = False
                user.is_department_manager = False
                user.is_fleet_manager = False
            else:
                user.is_fleet_user = True
                user.is_fleet_driver = (user.fleet_role == 'driver')
                user.is_department_manager = (user.fleet_role == 'department_manager')
                user.is_fleet_manager = (user.fleet_role == 'fleet_manager')

    @api.onchange('is_fleet_user', 'is_fleet_driver', 'is_fleet_manager', 'is_department_manager')
    def _onchange_fleet_role_flags(self):
        for user in self:
            if user.is_fleet_manager:
                user.fleet_role = 'fleet_manager'
            elif user.is_department_manager:
                user.fleet_role = 'department_manager'
            elif user.is_fleet_driver:
                user.fleet_role = 'driver'
            elif user.is_fleet_user:
                user.fleet_role = 'fleet_user'
            else:
                user.fleet_role = 'employee'

    @api.constrains('fleet_role', 'is_fleet_driver', 'driver_license_number', 'driver_license_category', 'driver_license_issue_date', 'driver_license_expiry_date', 'driver_license_image')
    def _check_driver_license_info(self):
        for user in self:
            if user.fleet_role == 'driver' or user.is_fleet_driver:
                missing_fields = []
                if not user.driver_license_number:
                    missing_fields.append("License Number")
                if not user.driver_license_category:
                    missing_fields.append("License Category / Level")
                if not user.driver_license_issue_date:
                    missing_fields.append("License Issue Date")
                if not user.driver_license_expiry_date:
                    missing_fields.append("License Expiry Date")
                if not user.driver_license_image:
                    missing_fields.append("License Copy (Image Scan)")
                
                if missing_fields:
                    raise ValidationError(
                        _("The following fields are required for the Driver role:\n- %s") % "\n- ".join(missing_fields)
                    )

    def _get_fleet_role_group_xmlids(self):
        self.ensure_one()
        group_xmlids = []
        if self.is_fleet_user:
            group_xmlids.append('fleet_management.group_fleet_user')
        if self.is_fleet_driver:
            group_xmlids.append('fleet_management.group_fleet_driver')
        if self.is_department_manager:
            group_xmlids.append('fleet_management.group_department_manager')
        if self.is_fleet_manager:
            group_xmlids.append('fleet_management.group_fleet_manager')
        return group_xmlids

    def _sync_fleet_role_to_groups(self):
        group_xmlids = (
            'fleet_management.group_fleet_user',
            'fleet_management.group_fleet_driver',
            'fleet_management.group_department_manager',
            'fleet_management.group_fleet_manager',
        )
        managed_groups = self.env['res.groups'].browse([
            group.id
            for group in (
                self.env.ref(group_xmlid, raise_if_not_found=False)
                for group_xmlid in group_xmlids
            )
            if group
        ])
        for user in self:
            commands = [(3, group.id) for group in managed_groups]
            for group_xmlid in user._get_fleet_role_group_xmlids():
                role_group = self.env.ref(group_xmlid, raise_if_not_found=False)
                if role_group:
                    commands.append((4, role_group.id))
            if commands:
                user.sudo().write({'groups_id': commands})

    def _sync_to_employee(self):
        for user in self:
            employee = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
            if employee:
                employee.write({
                    'fleet_role': user.fleet_role,
                    'is_fleet_user': user.is_fleet_user,
                    'is_fleet_driver': user.is_fleet_driver,
                    'is_fleet_manager': user.is_fleet_manager,
                    'is_department_manager': user.is_department_manager,
                    'driver_license_number': user.driver_license_number,
                    'driver_license_category': user.driver_license_category,
                    'driver_license_issue_date': user.driver_license_issue_date,
                    'driver_license_expiry_date': user.driver_license_expiry_date,
                    'driver_license_suspended': user.driver_license_suspended,
                    'driver_license_image': user.driver_license_image,
                })

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        for user in users:
            user._sync_fleet_role_to_groups()
            user._sync_to_employee()
        return users

    def write(self, vals):
        res = super().write(vals)
        role_fields = {
            'fleet_role', 'is_fleet_user', 'is_fleet_driver', 'is_fleet_manager', 'is_department_manager',
            'driver_license_number', 'driver_license_category', 'driver_license_issue_date',
            'driver_license_expiry_date', 'driver_license_suspended', 'driver_license_image'
        }
        if role_fields.intersection(vals):
            for user in self:
                user._sync_fleet_role_to_groups()
                user._sync_to_employee()
        return res