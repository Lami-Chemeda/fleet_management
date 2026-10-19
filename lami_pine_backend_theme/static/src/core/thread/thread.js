// Template Theme: customize this file for your theme.
/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Thread } from '@mail/core/common/thread';

// Patching the Thread component to support filtering out notification messages.
patch(Thread.prototype, {
    /**
     * Returns the list of messages to display, optionally filtered by type.
     */
    get displayMessages() {
        let messages = (
            this.props.order === 'asc' ?
            this.props.thread.nonEmptyMessages :
            [...this.props.thread.nonEmptyMessages].reverse()
        );
        // Filter out notification messages if showNotificationMessages is false.
        if (!this.props.showNotificationMessages) {
            messages = messages.filter(
                (msg) => !['user_notification', 'notification'].includes(
                    msg.message_type
                )
            );
        }
        return messages;
    },
});

// Add showNotificationMessages to the component's props.
Thread.props = [
    ...Thread.props,
    'showNotificationMessages?',
];
Thread.defaultProps = {
    ...Thread.defaultProps,
    showNotificationMessages: true,
};