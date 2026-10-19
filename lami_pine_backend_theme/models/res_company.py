from odoo import models, fields


class ResCompany(models.Model):
    
    _inherit = 'res.company'
    
    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------

    hero_section_bg = fields.Image(
        string='Hero Section Background Image',
        attachment=True
    )

    login_page_logo = fields.Image(
        string='Login Page Logo',
        attachment=True
    )

    left_bg_image = fields.Image(
        string='Brand Header Background Image',
        attachment=True
    )

    login_left_panel_bg_image = fields.Image(
        string='Login Left Panel Background Image',
        attachment=True
    )

    motto = fields.Char(
        string='Company Motto',
        default=''
    )
