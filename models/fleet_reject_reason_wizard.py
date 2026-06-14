from odoo import fields, models


class FleetRejectReasonWizard(models.TransientModel):
    _name = 'fleet.reject.reason.wizard'
    _description = 'Fleet Request Rejection Reason'

    request_model = fields.Char(string='Request Model', required=True)
    request_id = fields.Integer(string='Request', required=True)
    reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        record = self.env[self.request_model].browse(self.request_id)
        record.write({'rejection_reason': self.reason})
        record.action_reject()
        return {'type': 'ir.actions.act_window_close'}
