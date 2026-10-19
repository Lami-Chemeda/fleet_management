{
    'name': 'Custom Email Notifier',
    'version': '18.0.1.0.1',
    'summary': 'Universal Email Notification Utility',
    'description': """
        This module provides a universal background email sender utilizing email.json.
        Other modules can import the send_custom_email function to easily dispatch
        system notifications via external SMTP servers asynchronously.
    """,
    'category': 'Hidden/Tools',
    'author': 'lami chemeda',
    'depends': ['base', 'mail'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
