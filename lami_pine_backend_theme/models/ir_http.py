from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):

    _inherit = "ir.http"

    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------
    
    def session_info(self):
        result = super(IrHttp, self).session_info()
        result['chatter_position'] = self.env.user.chatter_position
        result['dialog_size'] = self.env.user.dialog_size
        if request.env.user._is_internal():
            for company in request.env.user.company_ids.with_context(bin_size=True):
                result['user_companies']['allowed_companies'][company.id].update({
                    'has_logo': bool(company.logo),
                    'has_left_bg_image': bool(company.left_bg_image),
                    'has_hero_section_bg': bool(company.hero_section_bg),
                    'motto': company.motto,
                })
        return result
