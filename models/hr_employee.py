from odoo import api, fields, models
from odoo.exceptions import ValidationError
import re


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    _ethiopian_phone_regex = re.compile(r'^(\+251|0)[1-9]\d{8}$')

    is_fleet_driver = fields.Boolean(
        string='Fleet Driver',
    )
    is_fleet_user = fields.Boolean(
        string='Fleet User',
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
        default='employee',
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
        string='License Category',
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
            else:
                employee.driver_license_status = 'valid'

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
        for vals in vals_list:
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
        for vals, employee in zip(vals_to_create, employees):
            if 'fleet_role' in vals:
                employees_to_sync |= employee
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
        role_flag_by_selection = {
            'fleet_user': 'is_fleet_user',
            'driver': 'is_fleet_driver',
            'department_manager': 'is_department_manager',
            'fleet_manager': 'is_fleet_manager',
        }
        flag_name = role_flag_by_selection.get(self.fleet_role)
        if flag_name:
            self[flag_name] = True
            if flag_name != 'is_fleet_user':
                self.is_fleet_user = True
        elif self.fleet_role == 'employee':
            self.is_fleet_user = False
            self.is_fleet_driver = False
            self.is_department_manager = False
            self.is_fleet_manager = False

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

    @api.constrains('work_phone', 'mobile_phone')
    def _check_ethiopian_phone_numbers(self):
        for employee in self:
            employee._validate_ethiopian_phone_number(employee.work_phone, 'Work Phone')
            employee._validate_ethiopian_phone_number(employee.mobile_phone, 'Work Mobile')

    def _validate_ethiopian_phone_number(self, phone_number, field_label):
        if not phone_number:
            return

        clean_phone_number = re.sub(r'[\s\-\(\)]', '', phone_number)
        if not self._ethiopian_phone_regex.match(clean_phone_number):
            raise ValidationError(
                '%s must be a valid Ethiopian phone number format (e.g., +251911234567 or 0911234567).'
                % field_label
            )
