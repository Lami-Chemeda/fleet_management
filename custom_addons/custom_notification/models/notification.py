from odoo import models, fields, api

class Notification(models.Model):
    _name = 'custom.notification'
    _description = 'User Notifications'

    title = fields.Char(string='Title', required=True)
    message = fields.Text(string='Message', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, 
    ondelete='cascade'
    )
    is_read = fields.Boolean(string='Read', default=False)
    

     # Fields for dynamic action creation
    action_model = fields.Char(string='Model')  # e.g., 'hr.leave'
    action_res_id = fields.Integer(string='Record ID')
    action_view_mode = fields.Char(string='View Mode', default='form')  # e.g., 'form'
    action_id = fields.Integer(string='Action ID', compute="_compute_action_fields", store=True)
    action_company_id = fields.Integer(string='Company ID', compute="_compute_action_fields", store=True)

    @api.constrains('user_id')
    def _check_user_id(self):
        for record in self:
            if not record.user_id:
                raise ValueError("User ID cannot be empty.")

    @api.depends('action_model')
    def _compute_action_fields(self):
        for record in self:
            record.action_company_id = self.env.company.id        
            if record.action_model and not record.action_id:
                # Search for menus that point to actions referencing the action_model
                action = self.env['ir.actions.act_window'].search([
                    ('res_model', '=', record.action_model),
                    ('type', '=', 'ir.actions.act_window'),  # Ensure it’s a window action
                ], limit=1)
                if action:
                    record.action_id = action.id
                else:
                    record.action_id = False
            
