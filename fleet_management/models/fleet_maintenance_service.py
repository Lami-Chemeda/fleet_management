from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class FleetMaintenanceService(models.Model):
    _name = 'fleet.maintenance.service'
    _description = 'Maintenance Service Record'
    _order = 'start_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    maintenance_request_id = fields.Many2one('fleet.maintenance.request', string='Maintenance Request', required=True, ondelete='cascade', tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', related='maintenance_request_id.vehicle_id', store=True, readonly=True)
    vendor_id = fields.Many2one(
        'res.partner',
        string='Garage / Vendor',
        required=True,
        domain="[('is_company', '=', True), ('is_garage_vendor', '=', True), ('garage_approval_status', '=', 'approved')]",
        tracking=True,
    )
    service_description = fields.Text(string='Service Description', required=True)
    start_date = fields.Datetime(string='Start Date', default=fields.Datetime.now, required=True, tracking=True)
    completion_date = fields.Datetime(string='Completion Date', tracking=True)
    cost = fields.Monetary(string='Cost', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)
    notes = fields.Text(string='Notes')

    @api.constrains('start_date', 'completion_date', 'cost')
    def _check_service_values(self):
        for service in self:
            if service.completion_date and service.completion_date < service.start_date:
                raise ValidationError('Completion Date must be after Start Date.')
            if service.cost < 0:
                raise ValidationError('Cost cannot be negative.')

    def action_mark_completed(self):
        if not self.env.is_superuser() and not self.env.user.has_group('fleet_management.group_fleet_manager'):
            raise AccessError('Only Fleet Managers can complete maintenance service records.')
        for service in self:
            service.completion_date = fields.Datetime.now()
            service.maintenance_request_id.action_complete()
