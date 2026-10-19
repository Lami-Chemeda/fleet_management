// Template Theme: customize this file for your theme.
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { computeAppsAndMenuItems, reorderApps } from "@web/webclient/menus/menu_helpers";

const THEME_APP_ICON_BASE = "/lami_pine_backend_theme/static/src/img/apps/";
const THEME_APP_ICON_MAP = {
	account: `${THEME_APP_ICON_BASE}account.png`,
	home: `${THEME_APP_ICON_BASE}home.png`,
	base: `${THEME_APP_ICON_BASE}settings.png`,
	calendar: `${THEME_APP_ICON_BASE}calendar.png`,
	contacts: `${THEME_APP_ICON_BASE}contacts.png`,
	crm: `${THEME_APP_ICON_BASE}crm.png`,
	hr: `${THEME_APP_ICON_BASE}hr.png`,
	mail: `${THEME_APP_ICON_BASE}mail.png`,
	mrp: `${THEME_APP_ICON_BASE}mrp.png`,
	project: `${THEME_APP_ICON_BASE}project.png`,
	project_todo: `${THEME_APP_ICON_BASE}project_todo.png`,
	purchase: `${THEME_APP_ICON_BASE}purchase.png`,
	sale: `${THEME_APP_ICON_BASE}sale.png`,
	stock: `${THEME_APP_ICON_BASE}stock.png`,
	website: `${THEME_APP_ICON_BASE}website.png`,
    apps: `${THEME_APP_ICON_BASE}Apps.png`,
	lami_pine_backend_theme: `${THEME_APP_ICON_BASE}home.png`,
};

const THEME_APP_ICON_ALIASES = {
	sale_management: "sale",
};

/**
 * app_menu service
 * This service provides helper methods for managing and retrieving app menus.
 */
export const appMenuService = {
    dependencies: ["menu"],
    async start(env, { menu }) {
        return {
            /**
             * Returns the currently active app.
             */
        	getCurrentApp () {
        		return menu.getCurrentApp();
        	},

            /**
             * Returns the list of apps, reordered according to user settings if available.
             */
			getAppsMenuItems() {
				const menuItems = computeAppsAndMenuItems(
					menu.getMenuAsTree('root')
				)
				const apps = menuItems.apps;
				const menuConfig = JSON.parse(
					user.settings?.homemenu_config || 'null'
				);
				if (menuConfig) {
                    reorderApps(apps, menuConfig);
				}

				for (const app of apps) {
					if (!app.xmlid) continue;
					let moduleName = app.xmlid.split('.')[0];
					moduleName = THEME_APP_ICON_ALIASES[moduleName] || moduleName;
                    
                    // Special case for the "Apps" menu
                    if (app.xmlid === 'base.menu_management') {
                        moduleName = 'apps';
                    }

					const iconUrl = THEME_APP_ICON_MAP[moduleName];
					if (iconUrl) {
						app.webIconData = iconUrl;
					}
				}
        		return apps;
			},

            /**
             * Selects/activates a specific app.
             * @param {Object} app - The app to select.
             */
			selectApp(app) {
				menu.selectMenu(app);
			}
        };
    },
};

// Register the service in the 'services' category.
registry.category("services").add("app_menu", appMenuService, { force: true });
