{
    'name': 'Advanced fleet,vehicle and feul management',

    'version': '18.0.2.0.1',
    'summary': 'Advanced Fleet & Fuel Management: Control fuel quotas, vehicle maintenance, trip requests, and driver GPS tracking.',
    'description': """
<h1>Ultimate Fleet & Fuel Management Pro (Odoo 18)</h1>
<p>The ultimate <b>Fleet Management</b> and Fuel Operations system for Odoo. If you are looking for a complete <b>fleet management</b> and fuel tracking solution, this module provides strict fuel quotas, trip approvals, vehicle lifecycle tracking, and automated budget deductions.</p>
<br/>
<h3>Key Features:</h3>
<ul>
    <li><b>Advanced Fuel Management:</b> Track every drop of fuel. Driver fuel requests, multi-level approvals, fuel quotas per vehicle, and pump station receipt logging.</li>
    <li><b>Vehicle & GPS Tracking:</b> Full vehicle lifecycle management with integrated GPS tracking logs (Latitude, Longitude, Speed).</li>
    <li><b>Trip & Dispatch Management:</b> Multi-level approval workflows for trip dispatching.</li>
    <li><b>Maintenance & Repairs:</b> Automated maintenance alerts, external garage vendor linking, and invoice tracking.</li>
    <li><b>Driver Scorecards:</b> Gamify driver performance based on fuel efficiency and incident reports.</li>
    <li><b>Incident & Insurance:</b> Log accidents, manage claims, and track document renewals (insurance, licenses).</li>
</ul>
<p>Transform your logistics and eliminate fuel theft today with <b>Ultimate Fleet & Fuel Management Pro</b>!</p>
    """,
    'category': 'Operations/Fleet',
    'author': '@lamitech and @alexastu',
    'depends': [
        'base',
        'mail',
        'hr',
        'contacts',
        'fleet',
        'lami_custom_notification',
        'lami_custom_report',
        'custom_email_notifier',
        'lami_pine_backend_theme',
        'web',  # Added this line for login template inheritance
        'calendar',
        'account',
        'portal',
        'uom',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/fleet_cron_data.xml',
        'views/fleet_reject_reason_wizard_views.xml',
        'views/fleet_finish_trip_wizard_views.xml',
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
        'views/fleet_document_views.xml',
        'views/fleet_insurance_views.xml',
        'views/fleet_inspection_views.xml',
        'views/fleet_incident_views.xml',
        'views/fleet_contract_tyre_views.xml',
        'views/fleet_budget_views.xml',
        'views/fleet_driver_score_views.xml',
        'views/fleet_kpi_dashboard_views.xml',
        'views/fleet_gps_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/fleet_portal_templates.xml',
        'views/fleet_backend_dashboard_views.xml',
        'views/fleet_menu_views.xml',
        'report/trip_assignment_template.xml',
        'views/login_branding_views.xml',
        'views/fleet_dashboard_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fleet_management/static/src/css/hide_chatter_buttons.css',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'OPL-1',
    'price': 137.99,
    'currency': 'USD',
    'images': ['static/description/icon.png', 'static/description/icon.png'],
}