{
    'name': 'Custom Notification',
    'version': '16.0',
    'summary': 'Real-time user notifications in Odoo systray using OWL.',
    'description': '''
        This module provides a systray dropdown with real-time user notifications,
        including unread badges, links to records, and API support.
    ''',
    'category': 'Productivity/Discuss',
    'author': 'Chala Olani',
    'website': 'https://github.com/chalaa/custom_notification',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'bus', 'web'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_notification/static/src/js/notification.js',
            'custom_notification/static/src/xml/notification.xml',
        ],
    },
    'images': ['static/description/notification_preview.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}