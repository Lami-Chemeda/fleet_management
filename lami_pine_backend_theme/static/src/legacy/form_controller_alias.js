// Template Theme: customize this file for your theme.
/** @odoo-module **/

// This file provides a legacy alias for the FormController.
// It ensures compatibility with older modules that might still use odoo.define for FormController.
odoo.define("web.FormController", ["@web/views/form/form_controller"], function (formController) {
    "use strict";

    return formController.FormController;
});
