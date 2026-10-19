# Template Theme

This module is a starter kit for building a custom Odoo backend theme. It mirrors
the structure and asset wiring used by `lami_pine_backend_theme`, but with neutral
defaults and a generic name so you can copy and customize safely.

Quick customization checklist:
- Update `static/src/scss/colors.scss` and `static/src/scss/variables.scss`.
- Swap images in `static/src/img/` and `static/description/`.
- Adjust webclient UI in `static/src/webclient/` and chatter/dialog in
  `static/src/chatter/` and `static/src/core/`.
- Rename module identifiers in `__manifest__.py` and templates if you clone it.

Settings UI lives in `views/` and system parameters are defined in
`models/res_config_settings.py`.
