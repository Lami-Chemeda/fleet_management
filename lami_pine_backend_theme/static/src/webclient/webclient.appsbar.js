// Template Theme: customize this file for your theme.
/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { WebClient } from '@web/webclient/webclient';
import { AppsBar } from '@lami_pine_backend_theme/webclient/appsbar/appsbar';

// Patching the main WebClient to register the AppsBar component.
// This makes AppsBar available to be used in the WebClient's XML templates.
patch(WebClient, {
    components: {
        ...WebClient.components,
        AppsBar,
    },
});
