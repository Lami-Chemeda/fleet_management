from odoo import models, fields, api


class FleetFinishTripWizard(models.TransientModel):
    _name = 'fleet.finish.trip.wizard'
    _description = 'Finish Trip Confirmation Wizard'

    trip_request_id = fields.Many2one('fleet.trip.request', string='Trip Request', required=True)
    confirm_message = fields.Char(string='Message', default='Are you sure you want to finish this trip?', readonly=True)

    def action_confirm_finish(self):
        self.ensure_one()
        return self.trip_request_id.action_finish_trip()
