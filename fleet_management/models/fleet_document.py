from odoo import models, fields, api
from datetime import timedelta, date

class FleetVehicleDocument(models.Model):
    _name = 'fleet.vehicle.document'
    _description = 'Vehicle Document and Compliance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Document Name/Number', required=True, tracking=True)
    document_type = fields.Selection([
        ('registration', 'Registration'),
        ('insurance', 'Insurance Certificate'),
        ('road_tax', 'Road Tax'),
        ('emission', 'Emission Certificate'),
        ('permit', 'Operating Permit'),
        ('other', 'Other')
    ], string='Document Type', required=True, tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True)
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', required=True, tracking=True)
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Name')
    status = fields.Selection([
        ('valid', 'Valid'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired')
    ], string='Status', compute='_compute_status', store=True)
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('expiry_date')
    def _compute_status(self):
        today = date.today()
        for doc in self:
            if not doc.expiry_date:
                doc.status = 'valid'
                continue
            
            if doc.expiry_date < today:
                doc.status = 'expired'
            elif doc.expiry_date <= today + timedelta(days=30):
                doc.status = 'expiring_soon'
            else:
                doc.status = 'valid'

    @api.model
    def _cron_check_document_expiry(self):
        """Cron job to check document expiry and create activities."""
        expiring_docs = self.search([
            ('status', 'in', ['expiring_soon', 'expired'])
        ])
        for doc in expiring_docs:
            summary = f"Document {doc.document_type} for {doc.vehicle_id.name} is {doc.status.replace('_', ' ')}"
            doc.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=doc.expiry_date,
                summary=summary,
                user_id=doc.create_uid.id or self.env.uid
            )
