from . import models
from . import controllers

import base64

from odoo.tools import file_open


def _setup_module(env):
    if env.ref('base.main_company', False):
        company = env.ref('base.main_company')
        with file_open('lami_pine_backend_theme/static/src/img/hero_bg.jpg', 'rb') as file:
            company.write({
                'hero_section_bg': base64.b64encode(file.read())
            })


def _uninstall_cleanup(env):
    env['ir.attachment'].search([('url', 'like', '/web/assets/%lami_pine_backend_theme/%')]).unlink()
    env['ir.asset'].search([
        '|', ('path', 'like', '%lami_pine_backend_theme/%'),
        ('target', 'like', 'lami_pine_backend_theme/%'),
    ]).unlink()
    env['ir.config_parameter'].search([('key', 'like', 'lami_pine_backend_theme.%')]).unlink()

    env.registry.clear_cache('assets')
