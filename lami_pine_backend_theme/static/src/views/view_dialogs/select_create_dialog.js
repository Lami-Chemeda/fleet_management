// Template Theme: customize this file for your theme.
/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { SelectCreateDialog } from '@web/views/view_dialogs/select_create_dialog';

// Patching SelectCreateDialog to support the fullscreen toggle.
patch(SelectCreateDialog.prototype, {
    /**
     * Toggles the dialog size between its initial size and fullscreen ('fs').
     */
    onClickDialogSizeToggle() {
        this.env.dialogData.size = (
            this.env.dialogData.size === 'fs' ? this.env.dialogData.initalSize : 'fs'
        );
    }
});