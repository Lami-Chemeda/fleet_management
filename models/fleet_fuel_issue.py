from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class FleetFuelIssue(models.Model):
    _name = 'fleet.fuel.issue'
    _description = 'Fuel and Lubricant Issue'
    _order = 'issue_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    fuel_request_id = fields.Many2one('fleet.fuel.request', string='Fuel Request', required=True, ondelete='cascade', tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', related='fuel_request_id.vehicle_id', store=True, readonly=True)
    driver_id = fields.Many2one('hr.employee', string='Driver', related='fuel_request_id.driver_id', store=True, readonly=True)
    issued_quantity = fields.Float(string='Issued Quantity', required=True, tracking=True)
    issue_date = fields.Datetime(string='Issue Date', default=fields.Datetime.now, required=True, tracking=True)
    issuer_id = fields.Many2one('res.users', string='Issuer', default=lambda self: self.env.user, required=True, tracking=True)
    cost = fields.Monetary(string='Cost', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)
    notes = fields.Text(string='Notes')

    @api.constrains('issued_quantity', 'cost')
    def _check_issue_values(self):
        for issue in self:
            if issue.issued_quantity <= 0:
                raise ValidationError('Issued Quantity must be greater than zero.')
            if issue.cost < 0:
                raise ValidationError('Cost cannot be negative.')

    def action_confirm_issue(self):
        if not self.env.is_superuser() and not self.env.user.has_group('fleet_management.group_fleet_manager'):
            raise AccessError('Only Fleet Managers can confirm fuel issuance.')
        for issue in self:
            if issue.fuel_request_id.state not in ['approved', 'issued']:
                raise ValidationError('Fuel request must be approved before fuel can be issued.')
            issue.fuel_request_id.action_issue()
            self.env['fleet.vehicle.history'].create({
                'vehicle_id': issue.vehicle_id.id,
                'event_type': 'fuel_issued',
                'event_date': issue.issue_date,
                'driver_id': issue.driver_id.id,
                'description': 'Issued %s of %s.' % (
                    issue.issued_quantity,
                    issue.fuel_request_id.fuel_type,
                ),
                'odometer': issue.vehicle_id.current_odometer,
            })
