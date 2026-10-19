from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_garage_vendor = fields.Boolean(
        string='Garage / Service Provider',
    )
    garage_approval_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('suspended', 'Suspended'),
        ],
        string='Garage Approval Status',
        default='draft',
    )
    garage_service_type = fields.Selection(
        selection=[
            ('mechanical', 'Mechanical'),
            ('electrical', 'Electrical'),
            ('body_work', 'Body Work'),
            ('tire', 'Tire Service'),
            ('general', 'General Service'),
            ('other', 'Other'),
        ],
        string='Service Type',
    )
    garage_contact_person = fields.Char(
        string='Garage Contact Person',
    )
    garage_notes = fields.Text(
        string='Garage Notes',
    )
