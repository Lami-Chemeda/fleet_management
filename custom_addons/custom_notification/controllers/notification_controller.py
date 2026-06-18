from odoo import http
from odoo.http import request

class NotificationController(http.Controller):
    @http.route('/custom_notification/fetch', type='json', auth='user')
    def fetch_notifications(self):
        user = request.env.user
        notifications = request.env['custom.notification'].sudo().search([
            ('user_id', '=', user.id),
            ('is_read', '=', False)
        ])

        print("Notifications:====================>", notifications)
        return [{'id': n.id, 'title': n.title, 'message': n.message} for n in notifications]

    @http.route('/custom_notification/mark_as_read', type='json', auth='user')
    def mark_as_read(self, notification_id):
        notification = request.env['custom.notification'].sudo().browse(notification_id)
        if notification.user_id.id == request.env.user.id:
            notification.is_read = True
        return {'success': True}
