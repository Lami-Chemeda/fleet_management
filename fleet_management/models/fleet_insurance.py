from odoo import models, fields, api

class FleetVehicleInsurance(models.Model):
    _name = 'fleet.vehicle.insurance'
    _description = 'Vehicle Insurance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Policy Number', required=True, tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True)
    insurer_id = fields.Many2one('res.partner', string='Insurer', required=True, tracking=True)
    coverage_type = fields.Selection([
        ('comprehensive', 'Comprehensive'),
        ('third_party', 'Third Party'),
        ('other', 'Other')
    ], string='Coverage Type', required=True)
    premium_amount = fields.Monetary(string='Premium Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    claim_ids = fields.One2many('fleet.insurance.claim', 'insurance_id', string='Claims')
    notes = fields.Text(string='Policy Details')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

class FleetInsuranceClaim(models.Model):
    _name = 'fleet.insurance.claim'
    _description = 'Insurance Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Claim Reference', required=True, tracking=True)
    insurance_id = fields.Many2one('fleet.vehicle.insurance', string='Insurance Policy', required=True)
    incident_id = fields.Many2one('fleet.incident', string='Related Incident')
    claim_date = fields.Date(string='Date of Claim', default=fields.Date.context_today)
    claim_amount = fields.Monetary(string='Claim Amount', currency_field='currency_id')
    currency_id = fields.Many2one(related='insurance_id.currency_id')
    status = fields.Selection([
        ('filed', 'Filed'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid')
    ], string='Status', default='filed', tracking=True)
    description = fields.Text(string='Description')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
