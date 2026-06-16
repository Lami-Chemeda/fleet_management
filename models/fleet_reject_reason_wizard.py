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
        
        # Determine who is rejecting based on their role and request state
        is_department_manager = self.env.user.has_group('fleet_management.group_department_manager')
        is_fleet_manager = self.env.user.has_group('fleet_management.group_fleet_manager')
        
        rejection_role = False
        if is_department_manager and record.state == 'submitted':
            rejection_role = 'department_manager'
        elif is_fleet_manager:
            rejection_role = 'fleet_manager'
        
        # Write rejection reason and who rejected
        record.write({
            'rejection_reason': self.reason,
            'rejected_by': self.env.user.name,
            'rejected_by_role': rejection_role,
        })

        # action_reject will now just handle the state change and extra validation
        record.action_reject()
        return {'type': 'ir.actions.act_window_close'}