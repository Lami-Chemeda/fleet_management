// Template Theme: customize this file for your theme.
/** @odoo-module **/

import { useState, useRef } from '@odoo/owl';
import { patch } from '@web/core/utils/patch';
import { browser } from "@web/core/browser/browser";
import { FormRenderer } from '@web/views/form/form_renderer';

// Patching the standard FormRenderer to add chatter resizing functionality.
patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        // Initialize chatter state from local storage to remember the user's preferred width.
        this.chatterState = useState({
            width: browser.localStorage.getItem('pine_backend_theme_chatter.width'),
        });
        // Reference to the chatter container element.
        this.chatterContainer = useRef('chatterContainer');
    },

    /**
     * Handles the start of the chatter resizing process.
     * Triggered when the user clicks on the resize handle.
     */
    onStartChatterResize(ev) {
        if (ev.button !== 0) {
            return; // Only handle left-click
        }
        const initialX = ev.pageX;
        const chatterElement = this.chatterContainer.el;
        const initialWidth = chatterElement.offsetWidth;
        const resizeStoppingEvents = [
            'keydown', 'mousedown', 'mouseup'
        ];

        /**
         * Updates the chatter width as the mouse moves.
         */
        const resizePanel = (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            // Calculate new width with constraints (min 50px, max parent width - 250px).
            const newWidth = Math.min(
                Math.max(50, initialWidth - (ev.pageX - initialX)),
                Math.max(chatterElement.parentElement.offsetWidth - 250, 250)
            );
            // Save the new width to local storage and update the state.
            browser.localStorage.setItem('pine_backend_theme_chatter.width', newWidth);
            this.chatterState.width = newWidth;
        };

        /**
         * Stops the resizing process and cleans up event listeners.
         */
        const stopResize = (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            if (ev.type === 'mousedown' && ev.button === 0) {
                return;
            }
            document.removeEventListener('mousemove', resizePanel, true);
            resizeStoppingEvents.forEach((stoppingEvent) => {
                document.removeEventListener(stoppingEvent, stopResize, true);
            });
            document.activeElement.blur();
        };

        // Add listeners for mouse move and stop events.
        document.addEventListener('mousemove', resizePanel, true);
        resizeStoppingEvents.forEach((stoppingEvent) => {
            document.addEventListener(stoppingEvent, stopResize, true);
        });
    },

    /**
     * Resets the chatter width to default on double-click.
     */
    onDoubleClickChatterResize(ev) {
        browser.localStorage.removeItem('pine_backend_theme_chatter.width');
        this.chatterState.width = false;
    },
});
