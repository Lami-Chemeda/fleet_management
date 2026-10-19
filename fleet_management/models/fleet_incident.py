from odoo import models, fields, api

class FleetIncident(models.Model):
    _name = 'fleet.incident'
    _description = 'Vehicle Incident / Accident'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('fleet.incident') or 'New')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True)
    driver_id = fields.Many2one('hr.employee', string='Driver', required=True, tracking=True)
    date = fields.Datetime(string='Date and Time', required=True, default=fields.Datetime.now)
    location = fields.Char(string='Location', required=True)
    incident_type = fields.Selection([
        ('accident', 'Accident'),
        ('theft', 'Theft'),
        ('damage', 'Damage'),
        ('violation', 'Traffic Violation'),
        ('other', 'Other')
    ], string='Type', required=True, tracking=True)
    severity = fields.Selection([
        ('minor', 'Minor'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('critical', 'Critical')
    ], string='Severity', required=True, tracking=True)
    description = fields.Text(string='Description of Incident', required=True)
    repair_cost = fields.Monetary(string='Estimated Repair Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    claim_ids = fields.One2many('fleet.insurance.claim', 'incident_id', string='Insurance Claims')
    status = fields.Selection([
        ('reported', 'Reported'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved')
    ], string='Status', default='reported', tracking=True)
    photo_ids = fields.Many2many('ir.attachment', string='Photos/Evidence')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.incident') or 'New'
        return super(FleetIncident, self).create(vals_list)
