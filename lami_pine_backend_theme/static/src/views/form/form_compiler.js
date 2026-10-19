// Template Theme: customize this file for your theme.
/** @odoo-module **/

import { session } from '@web/session';
import { patch } from '@web/core/utils/patch';
import { append, createElement, setAttributes } from '@web/core/utils/xml';
import { FormCompiler } from '@web/views/form/form_compiler';

// Patching FormCompiler to inject custom XML/attributes into the form view at compilation time.
patch(FormCompiler.prototype, {
    compileHeader(node, params) {
        const res = super.compileHeader(node, params);
        const statusBarButtons = res.querySelector("StatusBarButtons");
        if (statusBarButtons) {
            statusBarButtons.setAttribute("t-if", "true");
        }
        return res;
    },
    compile(node, params) {
        const res = super.compile(node, params);

        // Find the chatter container in the compiled XML.
        const chatterContainerHookXml = res.querySelector(
            '.o_form_renderer > .o-mail-Form-chatter'
        );
        if (!chatterContainerHookXml) {
            return res;
        }

        // Add a t-ref so we can access the chatter element in the renderer.
        setAttributes(chatterContainerHookXml, {
            't-ref': 'chatterContainer',
        });

        // Handle chatter positioning based on user session settings.
        if (session.chatter_position === 'bottom') {
            // If chatter is at the bottom, move it inside the form sheet background.
            const formSheetBgXml = res.querySelector('.o_form_sheet_bg');
            if (!chatterContainerHookXml || !formSheetBgXml?.parentNode) {
                return res;
            }
            const webClientViewAttachmentViewHookXml = res.querySelector(
                '.o_attachment_preview'
            );
            const chatterContainerXml = chatterContainerHookXml.querySelector(
                "t[t-component='__comp__.mailComponents.Chatter']"
            );

            // Clone the chatter container to place it in the new location.
            const sheetBgChatterContainerHookXml = chatterContainerHookXml.cloneNode(true);
            const sheetBgChatterContainerXml = sheetBgChatterContainerHookXml.querySelector(
                "t[t-component='__comp__.mailComponents.Chatter']"
            );

            sheetBgChatterContainerHookXml.classList.add('o-isInFormSheetBg', 'w-auto');
            append(formSheetBgXml, sheetBgChatterContainerHookXml);

            // Update attributes for the new chatter location.
            setAttributes(sheetBgChatterContainerXml, {
                isInFormSheetBg: 'true',
                isChatterAside: 'false',
            });
            setAttributes(chatterContainerXml, {
                isInFormSheetBg: 'true',
                isChatterAside: 'false',
            });

            // Hide the original chatter container.
            setAttributes(chatterContainerHookXml, {
                't-if': 'false',
            });

            if (webClientViewAttachmentViewHookXml) {
                setAttributes(webClientViewAttachmentViewHookXml, {
                    't-if': 'false',
                });
            }
        } else {
            // If chatter is on the side, add the resizing handle.
            setAttributes(chatterContainerHookXml, {
                't-att-style': '__comp__.chatterState.width ? `width: ${__comp__.chatterState.width}px;` : ""',
            });

            // Create the resize handle element.
            const chatterContainerResizeHookXml = createElement('span');
            chatterContainerResizeHookXml.classList.add('tt_chatter_resize');
            setAttributes(chatterContainerResizeHookXml, {
                't-on-mousedown.stop.prevent': '__comp__.onStartChatterResize.bind(__comp__)',
                't-on-dblclick.stop.prevent': '__comp__.onDoubleClickChatterResize.bind(__comp__)',
            });

            // Append the resize handle to the chatter container.
            append(chatterContainerHookXml, chatterContainerResizeHookXml);
        }
        return res;
    },
});
