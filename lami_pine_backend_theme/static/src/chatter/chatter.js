// Template Theme: customize this file for your theme.
/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";
import { Chatter } from "@mail/chatter/web_portal/chatter";

// Patching the Chatter component to add a toggle for notification messages.
patch(Chatter.prototype, {
    setup() {
        super.setup();
        // Load the notification toggle state from local storage.
        const showNotificationMessages = browser.localStorage.getItem(
            'pine_backend_theme_chatter.notifications'
        );
        this.state.showNotificationMessages = (
            showNotificationMessages != null ? 
            JSON.parse(showNotificationMessages) : true
        );
    },

    /**
     * Toggles the visibility of notification messages in the chatter.
     */
    onClickNotificationsToggle() {
        const showNotificationMessages = !this.state.showNotificationMessages;
        // Save the new state to local storage.
        browser.localStorage.setItem(
            'pine_backend_theme_chatter.notifications', showNotificationMessages
        );
        this.state.showNotificationMessages = showNotificationMessages;
    },
});


