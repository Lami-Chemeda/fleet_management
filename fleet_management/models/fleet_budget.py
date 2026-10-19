from odoo import models, fields, api

class FleetBudget(models.Model):
    _name = 'fleet.budget'
    _description = 'Fleet Budget Control'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Budget Name', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True, tracking=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    
    budgeted_fuel = fields.Monetary(string='Budgeted Fuel', currency_field='currency_id', default=0.0)
    budgeted_maintenance = fields.Monetary(string='Budgeted Maintenance', currency_field='currency_id', default=0.0)
    budgeted_insurance = fields.Monetary(string='Budgeted Insurance', currency_field='currency_id', default=0.0)
    
    actual_fuel = fields.Monetary(string='Actual Fuel', compute='_compute_actuals', currency_field='currency_id')
    actual_maintenance = fields.Monetary(string='Actual Maintenance', compute='_compute_actuals', currency_field='currency_id')
    actual_insurance = fields.Monetary(string='Actual Insurance', compute='_compute_actuals', currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    def _compute_actuals(self):
        for budget in self:
            # Placeholder for actual computation logic
            # This would typically aggregate costs from fleet.fuel.issue, 
            # fleet.maintenance.service, and fleet.vehicle.insurance linked to this department
            budget.actual_fuel = 0.0
            budget.actual_maintenance = 0.0
            budget.actual_insurance = 0.0
