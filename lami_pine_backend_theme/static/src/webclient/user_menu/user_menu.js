// Template Theme: customize this file for your theme.
/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { UserMenu } from "@web/webclient/user_menu/user_menu";

// Patching the UserMenu to add a user role display.
patch(UserMenu.prototype, {
    setup() {
        super.setup();
        // Determine the user's role based on their permissions.
        this.userRole = user.isAdmin ? "Administrator" : user.isSystem ? "System" : "User";
    },
});
