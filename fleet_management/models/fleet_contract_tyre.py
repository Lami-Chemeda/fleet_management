from odoo import models, fields, api
from datetime import timedelta, date

class FleetVehicleContract(models.Model):
    _name = 'fleet.vehicle.contract'
    _description = 'Vehicle Contract (Lease/Rental)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Contract Reference', required=True, tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True)
    contract_type = fields.Selection([
        ('purchase', 'Purchase Agreement'),
        ('lease', 'Lease'),
        ('rental', 'Rental')
    ], string='Contract Type', required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor / Leasing Company', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    monthly_cost = fields.Monetary(string='Monthly Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    notes = fields.Text(string='Terms and Conditions')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)


class FleetVehicleTyre(models.Model):
    _name = 'fleet.vehicle.tyre'
    _description = 'Vehicle Tyre Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tyre Reference', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    position = fields.Selection([
        ('fl', 'Front Left'),
        ('fr', 'Front Right'),
        ('rl', 'Rear Left'),
        ('rr', 'Rear Right'),
        ('spare', 'Spare')
    ], string='Position', required=True)
    install_date = fields.Date(string='Installation Date', default=fields.Date.context_today)
    install_mileage = fields.Float(string='Mileage at Install (km)')
    expected_life = fields.Float(string='Expected Life (km)', default=50000.0)
    current_mileage = fields.Float(string='Current Tyre Mileage', compute='_compute_current_mileage')
    replacement_alert = fields.Boolean(string='Replacement Alert', compute='_compute_replacement_alert', store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('vehicle_id.odometer', 'install_mileage')
    def _compute_current_mileage(self):
        for tyre in self:
            if tyre.vehicle_id and tyre.vehicle_id.odometer:
                # Assuming vehicle model has 'odometer', if not this will need adjustment
                # Typically fleet.vehicle in Odoo has an odometer field or model
                tyre.current_mileage = max(0, tyre.vehicle_id.odometer - tyre.install_mileage)
            else:
                tyre.current_mileage = 0.0

    @api.depends('current_mileage', 'expected_life')
    def _compute_replacement_alert(self):
        for tyre in self:
            tyre.replacement_alert = tyre.current_mileage >= tyre.expected_life

    @api.model
    def _cron_check_tyre_replacement(self):
        tyres = self.search([('replacement_alert', '=', True)])
        for tyre in tyres:
            tyre.activity_schedule(
                'mail.mail_activity_data_todo',
                summary='Tyre Replacement Due',
                note=f'Tyre {tyre.name} on {tyre.vehicle_id.name} needs replacement.'
            )


class FleetSparePartUsage(models.Model):
    _name = 'fleet.spare.part.usage'
    _description = 'Spare Part Usage'

    name = fields.Char(string='Part Name/Code', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    maintenance_id = fields.Many2one('fleet.maintenance.service', string='Maintenance Service')
    quantity = fields.Float(string='Quantity', default=1.0)
    cost = fields.Monetary(string='Total Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
