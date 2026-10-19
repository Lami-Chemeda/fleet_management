from odoo import models, fields, api

class FleetVehicleInspection(models.Model):
    _name = 'fleet.vehicle.inspection'
    _description = 'Vehicle Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('fleet.inspection') or 'New')
    inspection_type = fields.Selection([
        ('pre_trip', 'Pre-Trip'),
        ('post_trip', 'Post-Trip'),
        ('periodic', 'Periodic')
    ], string='Inspection Type', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    driver_id = fields.Many2one('hr.employee', string='Driver/Inspector', required=True, default=lambda self: self.env.user.employee_id)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    trip_id = fields.Many2one('fleet.trip.request', string='Related Trip')
    maintenance_id = fields.Many2one('fleet.maintenance.request', string='Related Maintenance')
    line_ids = fields.One2many('fleet.inspection.line', 'inspection_id', string='Checklist')
    overall_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Overall Result', compute='_compute_overall_result', store=True)
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('line_ids.condition')
    def _compute_overall_result(self):
        for record in self:
            if any(line.condition == 'not_ok' for line in record.line_ids):
                record.overall_result = 'fail'
            else:
                record.overall_result = 'pass'


class FleetInspectionLine(models.Model):
    _name = 'fleet.inspection.line'
    _description = 'Inspection Checklist Line'

    inspection_id = fields.Many2one('fleet.vehicle.inspection', string='Inspection', ondelete='cascade')
    item_name = fields.Char(string='Item', required=True)
    condition = fields.Selection([
        ('ok', 'OK'),
        ('not_ok', 'Not OK'),
        ('na', 'N/A')
    ], string='Condition', required=True, default='ok')
    remarks = fields.Char(string='Remarks')
    photo = fields.Binary(string='Photo Evidence')
