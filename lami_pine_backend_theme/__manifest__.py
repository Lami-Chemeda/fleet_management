{
    'name': 'Pine Backend Theme Suite',
    'summary': 'A clean, modern backend theme with flexible customization.',
    'description': '''
        Pine Backend Theme is a polished, modern theme for Odoo that delivers
        a clean UI, responsive layout, and configurable styling. It provides
        ready-to-use assets, settings, and example views to speed up branding
        and customization work.
    ''',
    'version': '18.0.1.0.0',
    'category': 'Themes/Backend',
    'license': 'LGPL-3',
    'author': 'Daniel Geremew',
    'website': 'danielgeremew93@gmail.com',
    'depends': [
        'base_setup',
        'mail',
        'web',
        'web_editor',
        'auth_signup',
    ],
    'data': [
        'templates/web_layout.xml',
        'templates/webclient_colors.xml',
        'templates/webclient_appsbar.xml',
        'views/login.xml',
        'views/reset_pwd.xml',
        'views/home.xml',
        'views/res_config_settings.xml',
        'views/res_users_appsbar.xml',
        'views/res_users_chatter.xml',
        'views/res_users_dialog.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'lami_pine_backend_theme/static/src/scss/colors.scss'),
            (
                'before',
                'lami_pine_backend_theme/static/src/scss/colors.scss',
                'lami_pine_backend_theme/static/src/scss/colors_light.scss',
            ),
            'lami_pine_backend_theme/static/src/scss/appsbar.variables.scss',
            (
                'after',
                'web/static/src/scss/primary_variables.scss',
                'lami_pine_backend_theme/static/src/scss/variables.scss',
            ),
        ],
        'web._assets_backend_helpers': [
            'lami_pine_backend_theme/static/src/scss/appsbar.mixins.scss',
        ],
        'web.assets_web_dark': [
            (
                'after',
                'lami_pine_backend_theme/static/src/scss/appsbar.variables.scss',
                'lami_pine_backend_theme/static/src/scss/appsbar.variables.dark.scss',
            ),
            (
                'after',
                'lami_pine_backend_theme/static/src/scss/colors.scss',
                'lami_pine_backend_theme/static/src/scss/colors_dark.scss',
            ),
        ],
        'web.assets_frontend': [
            'lami_pine_backend_theme/static/src/webclient/login/login.scss',
            'lami_pine_backend_theme/static/src/webclient/login/reset_pwd.scss',
        ],
        'web.assets_backend': [
            'lami_pine_backend_theme/static/src/webclient/**/*.xml',
            'lami_pine_backend_theme/static/src/webclient/**/*.scss',
            'lami_pine_backend_theme/static/src/webclient/**/*.js',
            'lami_pine_backend_theme/static/src/core/**/*.xml',
            'lami_pine_backend_theme/static/src/core/**/*.scss',
            'lami_pine_backend_theme/static/src/core/**/*.js',
            'lami_pine_backend_theme/static/src/chatter/**/*.xml',
            'lami_pine_backend_theme/static/src/chatter/**/*.scss',
            'lami_pine_backend_theme/static/src/chatter/**/*.js',
            'lami_pine_backend_theme/static/src/views/**/*.scss',
            'lami_pine_backend_theme/static/src/views/**/*.js',
        ],
    },
    'images': [
        'static/description/icon.png',
        'static/description/banner.png',
    ],
    'post_init_hook': '_setup_module',
    'uninstall_hook': '_uninstall_cleanup',
}
