{
    'name': 'Fleet Management',
    'version': '18.0.1.0.0',
    'summary': 'Vehicle, driver, trip, fuel, and maintenance management',
    'description': """
Fleet Management module for managing vehicles, drivers, trip requests,
fuel requests, maintenance requests, external garages, and fleet reports.
    """,
    'category': 'Operations/Fleet',
    'author': 'Pcalami',
    'depends': [
        'base',
        'mail',
        'hr',
        'contacts',
        'fleet',
        'custom_notification',
        'custom_report',
        'web',  # Added this line for login template inheritance
        'uom',  # Added for uom.uom used in fuel requests
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/fleet_reject_reason_wizard_views.xml',
        'views/fleet_finish_trip_wizard_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/hr_employee_views.xml',
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
        'views/fleet_vehicle_history_views.xml',
        'views/fleet_trip_request_views.xml',
        'views/fleet_vehicle_assignment_views.xml',
        'views/fleet_fuel_request_views.xml',
        'views/fleet_fuel_issue_views.xml',
        'views/fleet_maintenance_request_views.xml',
        'views/fleet_maintenance_service_views.xml',
        'views/fleet_fuel_quota_views.xml',
        'views/fleet_fuel_type_views.xml',
        'views/fleet_report_views.xml',
        'views/fleet_menu_views.xml',
        'report/trip_assignment_template.xml',
        'report/trip_assignment_report.xml',
        'views/login_branding_views.xml',
        
    ],
    'assets': {
        'web.assets_backend': [
            'fleet_management/static/src/css/hide_chatter_buttons.css',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}