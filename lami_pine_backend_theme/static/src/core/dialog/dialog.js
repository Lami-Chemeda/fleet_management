// Template Theme: customize this file for your theme.
/** @odoo-module **/

import { session } from '@web/session';
import { patch } from '@web/core/utils/patch';
import { Dialog } from '@web/core/dialog/dialog';

// Patching the Dialog component to add a fullscreen toggle.
patch(Dialog.prototype, {
  setup() {
    super.setup();
    // Set the initial dialog size based on session settings or props.
    this.data.size = (
        session.dialog_size !== 'maximize' ? this.props.size : 'fs'
    );
    this.data.initalSize = this.props?.size || 'lg';
  },

  /**
   * Toggles the dialog size between its initial size and fullscreen ('fs').
   */
  onClickDialogSizeToggle() {
      this.data.size = this.data.size === 'fs' ? this.data.initalSize : 'fs';
  }
});
