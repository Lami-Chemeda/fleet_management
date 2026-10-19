/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { SettingsPage } from "@web/webclient/settings_form_view/settings/settings_page";

patch(SettingsPage.prototype, {
    /**
     * Helper to get the icon for the settings tab.
     * Uses theme icons for standard apps if available.
     * @param {Object} module 
     * @returns {string}
     */
    getModuleIcon(module) {
        // Map of module names to theme icon filenames
        const appIconMap = {
            'account': 'account',
            'calendar': 'calendar',
            'contacts': 'contacts',
            'crm': 'crm',
            'hr': 'hr',
            'mail': 'mail',
            'mrp': 'mrp',
            'project': 'project',
            'purchase': 'purchase',
            'sale': 'sale',
            'sale_management': 'sale',
            'stock': 'stock',
            'website': 'website',
            'base': 'settings',
            'base_setup': 'settings',
        };

        const name = module.key;
        const imgurl = module.imgurl || '';

        // Only change icons that are either in the mapping or clearly look like standard app icons
        if (appIconMap[name] || imgurl.includes('icons/apps')) {
            const iconName = appIconMap[name] || name;
            // Check if we have this specific icon in our theme, otherwise fallback to original
            // Note: Since we can't check file existence easily here, we rely on the map
            if (appIconMap[name]) {
                return `/lami_pine_backend_theme/static/src/img/apps/${appIconMap[name]}.png`;
            }
        }
        
        // Handle administration/settings cases
        if (name && (name.includes('administration') || name.includes('management'))) {
             return '/lami_pine_backend_theme/static/src/img/apps/settings.png';
        }

        return imgurl;
    }
});
