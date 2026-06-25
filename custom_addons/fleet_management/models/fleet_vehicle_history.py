from odoo import fields, models


class FleetVehicleHistory(models.Model):
    _name = 'fleet.vehicle.history'
    _description = 'Vehicle Lifecycle History'
    _order = 'event_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehicle',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    vehicle_name = fields.Char(
        string='Vehicle Name',
        related='vehicle_id.name',
        store=True,
        readonly=True,
    )
    license_plate = fields.Char(
        string='License Plate',
        related='vehicle_id.license_plate',
        store=True,
        readonly=True,
    )
    model_id = fields.Many2one(
        comodel_name='fleet.vehicle.model',
        string='Model',
        related='vehicle_id.model_id',
        store=True,
        readonly=True,
    )
    chassis_number = fields.Char(
        string='VIN / Chassis Number',
        related='vehicle_id.vin_sn',
        store=True,
        readonly=True,
    )
    engine_number = fields.Char(
        string='Engine Number',
        related='vehicle_id.engine_number',
        store=True,
        readonly=True,
    )
    ownership_type = fields.Selection(
        string='Ownership Type',
        related='vehicle_id.ownership_type',
        store=True,
        readonly=True,
    )
    registration_certificate_number = fields.Char(
        string='Registration Certificate Number',
        related='vehicle_id.registration_certificate_number',
        store=True,
        readonly=True,
    )
    registration_date = fields.Date(
        string='Official Registration Date',
        related='vehicle_id.registration_date',
        store=True,
        readonly=True,
    )
    fleet_status = fields.Selection(
        string='Current Fleet Status',
        related='vehicle_id.fleet_status',
        store=True,
        readonly=True,
    )
    event_type = fields.Selection(
        selection=[
            ('registered', 'Registered'),
            ('assigned', 'Assigned'),
            ('returned', 'Returned'),
            ('maintenance_started', 'Maintenance Started'),
            ('maintenance_completed', 'Maintenance Completed'),
            ('fuel_issued', 'Fuel Issued'),
            ('retired', 'Retired'),
            ('other', 'Other'),
        ],
        string='Event Type',
        required=True,
        tracking=True,
    )
    event_date = fields.Datetime(
        string='Event Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    driver_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Driver',
        tracking=True,
    )
    description = fields.Text(
        string='Description',
    )
    odometer = fields.Float(
        string='Odometer',
    )
