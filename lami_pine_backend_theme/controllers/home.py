# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class HomeController(http.Controller):
    @http.route('/home', type='http', auth='user')
    def home(self, **kwargs):
        context = request.env['ir.http'].webclient_rendering_context()
        response = request.render('web.webclient_bootstrap', qcontext=context)
        response.headers['X-Frame-Options'] = 'DENY'
        return response
