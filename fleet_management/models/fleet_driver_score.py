from odoo import models, fields, api

class FleetDriverScore(models.Model):
    _name = 'fleet.driver.score'
    _description = 'Driver Scorecard'
    _inherit = ['mail.thread']

    driver_id = fields.Many2one('hr.employee', string='Driver', required=True, tracking=True)
    period = fields.Date(string='Period (Month/Year)', required=True)
    trips_completed = fields.Integer(string='Trips Completed', default=0)
    incidents_count = fields.Integer(string='Incidents Count', default=0)
    harsh_braking_events = fields.Integer(string='Harsh Braking Events', default=0)
    fuel_efficiency = fields.Float(string='Fuel Efficiency (L/100km)')
    punctuality = fields.Float(string='Punctuality (%)', default=100.0)
    score = fields.Float(string='Overall Score', compute='_compute_score', store=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('trips_completed', 'incidents_count', 'harsh_braking_events', 'punctuality')
    def _compute_score(self):
        for record in self:
            # Basic scoring algorithm: start with 100
            # Deduct for incidents and harsh braking, reward for trips.
            base = 100.0
            base -= record.incidents_count * 20
            base -= record.harsh_braking_events * 5
            base -= (100.0 - record.punctuality) * 0.5
            base += min(record.trips_completed * 2, 20)  # Max 20 bonus points
            record.score = max(min(base, 100.0), 0.0)  # Clamp between 0 and 100
