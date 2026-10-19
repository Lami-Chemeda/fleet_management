from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    company_stamp = fields.Binary(string='Company Stamp', help='Upload your company stamp image here')
