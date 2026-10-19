// Template Theme: customize this file for your theme.
/** @odoo-module **/

import { Component, onWillStart, useState, useRef, useExternalListener } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

class TemplateThemeHome extends Component {
    static template = "lami_pine_backend_theme.Home";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.appMenuService = useService("app_menu");
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.companyService = useService("company");
        this.dropdownRef = useRef("focusDropdown");

        useExternalListener(window, "click", (ev) => {
            if (this.state.showFocusDropdown && 
                this.dropdownRef.el && 
                !this.dropdownRef.el.contains(ev.target)) {
                this.state.showFocusDropdown = false;
            }
        });

        this.countCache = new Map();
        this.state = useState({
            loading: true,
            metrics: [],
            moduleCards: [],
            focusItems: [],
            focusFilter: "7",
            showFocusDropdown: false,
            summary: {
                activityCount: 0,
                salesCount: 0,
                hasSales: false,
            },
            userName: user.name || "User",
        });

        onWillStart(() => {
            this.loadHome();
        });
    }

    getAvailableAppXmlIds() {
        const apps = this.appMenuService.getAppsMenuItems() || [];
        return new Set(apps.map((app) => app.xmlid).filter(Boolean));
    }

    getAppByXmlId() {
        const apps = this.appMenuService.getAppsMenuItems() || [];
        return new Map(
            apps
                .filter((app) => app.xmlid)
                .map((app) => [app.xmlid, app])
        );
    }

    getHeroBackgroundUrl() {
        if (this.companyService.currentCompany && this.companyService.currentCompany.has_hero_section_bg) {
            return `url(/web/image?model=res.company&field=hero_section_bg&id=${this.companyService.currentCompany.id})`;
        }
        return 'url(/lami_pine_backend_theme/static/src/img/hero_bg.jpg)';
    }

    async loadHome() {
        const formatter = new Intl.NumberFormat();
        const formatCount = (value) => formatter.format(value || 0);
        const today = new Date().toISOString().slice(0, 10);
        const availableAppXmlIds = this.getAvailableAppXmlIds();
        const appByXmlId = this.getAppByXmlId();
        const hasApp = (def) => !def.app_xmlid || availableAppXmlIds.has(def.app_xmlid);

        this.countCache.clear();
        const getCount = (model, domain) => this._getCount(model, domain);

        const metricDefs = [
            {
                key: "activities",
                label: "My Activities",
                model: "mail.activity",
                domain: [["user_id", "=", user.userId]],
                iconClass: "fa fa-check-circle",
                accentClass: "tt_stat_primary",
                iconClassName: "tt_stat_icon_blue",
                subtext: "Assigned to you",
                keywords: ["discuss", "activity", "mail"],
                action: "mail.action_view_activity",
                app_xmlid: "mail.menu_root_discuss",
            },
            {
                key: "sales",
                label: "Sales Orders",
                model: "sale.order",
                domain: [["state", "=", "sale"]],
                iconClass: "fa fa-line-chart",
                accentClass: "tt_stat_accent",
                iconClassName: "tt_stat_icon_green",
                subtext: "Confirmed orders",
                keywords: ["sale", "crm", "quotation", "sales"],
                action: "sale.action_orders",
                app_xmlid: "sale.sale_menu_root",
            },
            {
                key: "invoices",
                label: "Invoices Due",
                model: "account.move",
                domain: [
                    ["move_type", "=", "out_invoice"],
                    ["state", "=", "posted"],
                    ["payment_state", "in", ["not_paid", "partial"]],
                ],
                iconClass: "fa fa-file-text-o",
                accentClass: "tt_stat_warning",
                iconClassName: "tt_stat_icon_orange",
                subtext: "Awaiting payment",
                keywords: ["account", "invoice", "invoic", "accounting"],
                action: "account.action_move_out_invoice_type",
                app_xmlid: "account.menu_finance",
            },
            {
                key: "transfers",
                label: "Stock Transfers",
                model: "stock.picking",
                domain: [["state", "in", ["confirmed", "assigned", "waiting"]]],
                iconClass: "fa fa-truck",
                accentClass: "tt_stat_purple",
                iconClassName: "tt_stat_icon_purple",
                subtext: "Ready to process",
                keywords: ["inventory", "stock", "warehouse"],
                action: "stock.action_picking_tree_all",
                app_xmlid: "stock.menu_stock_root",
            },
            {
                key: "leads",
                label: "My Pipeline",
                model: "crm.lead",
                domain: [["user_id", "=", user.userId], ["type", "=", "opportunity"]],
                iconClass: "fa fa-star",
                accentClass: "tt_stat_primary",
                iconClassName: "tt_stat_icon_blue",
                subtext: "Active opportunities",
                keywords: ["crm", "pipeline", "lead"],
                action: "crm.crm_lead_action_pipeline",
                app_xmlid: "crm.crm_menu_root",
            },
        ];

        const metricsPromise = Promise.all(
            metricDefs.map(async (def) => {
                if (!hasApp(def)) {
                    return null;
                }
                const count = await getCount(def.model, def.domain);
                if (count === null) {
                    return null;
                }
                return {
                    ...def,
                    value: formatCount(count),
                    rawValue: count,
                };
            })
        ).then((items) => items.filter((m) => m));

        const cardDefs = [
            {
                key: "accounting",
                title: "Accounting",
                description: "Track customer invoices and vendor bills.",
                model: "account.move",
                domain: [["state", "=", "draft"], ["move_type", "=", "out_invoice"]],
                metricLabel: "Draft Invoices",
                headerClass: "tt_bg_blue",
                iconClass: "fa fa-file-text-o",
                watermarkClass: "fa fa-calculator",
                badge: "Review",
                badgeClass: "tt_badge_blue",
                keywords: ["account", "invoice", "invoic", "accounting"],
                action: "account.action_move_out_invoice_type",
                app_xmlid: "account.menu_finance",
                additionalInfo: [
                   { label: "Unpaid Invoices", model: "account.move", domain: [["move_type", "=", "out_invoice"], ["state", "=", "posted"], ["payment_state", "in", ["not_paid", "partial"]]] },
                   { label: "Unpaid Bills", model: "account.move", domain: [["move_type", "=", "in_invoice"], ["state", "=", "posted"], ["payment_state", "in", ["not_paid", "partial"]]] },
                ],
            },
            {
                key: "sales",
                title: "Sales",
                description: "Quotes, orders, and customer commitments.",
                model: "sale.order",
                domain: [["state", "in", ["draft", "sent"]]],
                metricLabel: "Quotes Pending",
                headerClass: "tt_bg_orange",
                iconClass: "fa fa-line-chart",
                watermarkClass: "fa fa-handshake-o",
                badge: "Active",
                badgeClass: "tt_badge_orange",
                keywords: ["sale", "crm", "quotation", "sales"],
                action: "sale.action_quotations_with_onboarding",
                app_xmlid: "sale.sale_menu_root",
                additionalInfo: [
                    { label: "Orders to Invoice", model: "sale.order", domain: [["invoice_status", "=", "to invoice"]] }
                ]
            },
            {
                key: "crm",
                title: "CRM",
                description: "Manage leads, opportunities, and pipeline.",
                model: "crm.lead",
                domain: [["type", "=", "opportunity"]],
                metricLabel: "Opportunities",
                headerClass: "tt_bg_purple",
                iconClass: "fa fa-star",
                watermarkClass: "fa fa-handshake-o",
                badge: "Pipeline",
                badgeClass: "tt_badge_purple",
                keywords: ["crm", "pipeline", "lead"],
                action: "crm.crm_lead_action_pipeline",
                app_xmlid: "crm.crm_menu_root",
                additionalInfo: [
                    { label: "New Leads", model: "crm.lead", domain: [["type", "=", "lead"]] }
                ]
            },
            {
                key: "project",
                title: "Project",
                description: "Tasks, deadlines, and project progress.",
                model: "project.task",
                domain: [["user_ids", "in", [user.userId]], ["state", "not in", ["1_done", "1_canceled"]]], 
                metricLabel: "My Tasks",
                headerClass: "tt_bg_blue",
                iconClass: "fa fa-tasks",
                watermarkClass: "fa fa-check-square-o",
                badge: "In Progress",
                badgeClass: "tt_badge_blue",
                keywords: ["project", "task", "agile"],
                action: "project.action_view_task",
                app_xmlid: "project.menu_main_pm",
                additionalInfo: []
            },
            {
                key: "purchases",
                title: "Purchases",
                description: "Requests, approvals, and vendor orders.",
                model: "purchase.order",
                domain: [["state", "in", ["draft", "sent", "to approve"]]],
                metricLabel: "RFQs",
                headerClass: "tt_bg_green",
                iconClass: "fa fa-shopping-cart",
                watermarkClass: "fa fa-truck",
                badge: "Queued",
                badgeClass: "tt_badge_green",
                keywords: ["purchase", "vendor", "buy"],
                action: "purchase.purchase_rfq",
                app_xmlid: "purchase.menu_purchase_root",
                additionalInfo: [
                     { label: "Orders to Approve", model: "purchase.order", domain: [["state", "=", "to approve"]] }
                ]
            },
            {
                key: "inventory",
                title: "Inventory",
                description: "Transfers, replenishment, and stock health.",
                model: "stock.picking",
                domain: [["state", "in", ["confirmed", "assigned", "waiting"]]],
                metricLabel: "To Process",
                headerClass: "tt_bg_purple",
                iconClass: "fa fa-dropbox",
                watermarkClass: "fa fa-cubes",
                badge: "In Progress",
                badgeClass: "tt_badge_gray",
                keywords: ["inventory", "stock", "warehouse"],
                action: "stock.action_picking_tree_all",
                app_xmlid: "stock.menu_stock_root",
                additionalInfo: [
                    { label: "Receipts", model: "stock.picking", domain: [["picking_type_id.code", "=", "incoming"], ["state", "not in", ["done", "cancel"]]] },
                    { label: "Deliveries", model: "stock.picking", domain: [["picking_type_id.code", "=", "outgoing"], ["state", "not in", ["done", "cancel"]]] }
                ]
            },
            {
                key: "employees",
                title: "Employees",
                description: "Directory, structure, and presence.",
                model: "hr.employee",
                domain: [],
                metricLabel: "Active Employees",
                headerClass: "tt_bg_green",
                iconClass: "fa fa-users",
                watermarkClass: "fa fa-id-card-o",
                badge: "Directory",
                badgeClass: "tt_badge_green",
                keywords: ["employee", "hr", "human resources"],
                action: "hr.open_view_employee_list_my",
                app_xmlid: "hr.menu_hr_root",
                additionalInfo: []
            },
            {
                key: "contacts",
                title: "Contacts",
                description: "Customer and vendor directory snapshots.",
                model: "res.partner",
                domain: [["active", "=", true]],
                metricLabel: "Total Contacts",
                headerClass: "tt_bg_blue",
                iconClass: "fa fa-address-book",
                watermarkClass: "fa fa-users",
                badge: "Active",
                badgeClass: "tt_badge_blue",
                keywords: ["contacts", "partner", "crm", "sales"],
                action: "contacts.action_contacts",
                app_xmlid: "contacts.menu_contacts",
                additionalInfo: [
                    { label: "Companies", model: "res.partner", domain: [["is_company", "=", true]] },
                    { label: "Individuals", model: "res.partner", domain: [["is_company", "=", false]] }
                ]
            },
        ];

        const cardPromises = cardDefs.map(async (def) => {
            if (!hasApp(def)) {
                return null;
            }
            const count = await getCount(def.model, def.domain);
            if (count === null) {
                return null;
            }
            const app = def.app_xmlid ? appByXmlId.get(def.app_xmlid) : null;
            return {
                ...def,
                title: app?.label || app?.name || def.title,
                metric: `${formatCount(count)} ${def.metricLabel}`,
                infoItems: [],
            };
        });

        const [metrics, moduleCards] = await Promise.all([
            metricsPromise,
            Promise.all(cardPromises).then((cards) => cards.filter((c) => c)),
        ]);

        const salesMetric = metrics.find((metric) => metric.key === "sales");
        const activityMetric = metrics.find((metric) => metric.key === "activities");
        this.state.summary.activityCount = activityMetric ? activityMetric.rawValue : 0;
        this.state.summary.salesCount = salesMetric ? salesMetric.rawValue : 0;
        this.state.summary.hasSales = Boolean(salesMetric);

        this.state.metrics = metrics;
        this.state.moduleCards = moduleCards;
        this.state.focusItems = [];
        this.state.loading = false;

        this.loadSecondaryData({ hasApp, cardDefs, formatCount, today });
    }

    async _getCount(model, domain) {
        const cacheKey = `${model}:${JSON.stringify(domain)}`;
        if (this.countCache.has(cacheKey)) {
            return this.countCache.get(cacheKey);
        }
        try {
            const value = await this.orm.searchCount(model, domain);
            this.countCache.set(cacheKey, value);
            return value;
        } catch (error) {
            return null;
        }
    }

    async _loadFocusItems(hasApp, today) {
        if (!hasApp({ app_xmlid: "mail.menu_root_discuss" })) {
            return [];
        }
        try {
            const domain = [["user_id", "=", user.userId]];
            const filter = this.state.focusFilter;
            
            if (filter === "overdue") {
                domain.push(["date_deadline", "<", today]);
            } else if (filter === "today") {
                domain.push(["date_deadline", "=", today]);
            } else if (filter !== "all") {
                // Upcoming X days
                const targetDate = new Date();
                targetDate.setDate(targetDate.getDate() + parseInt(filter));
                const dateStr = targetDate.toISOString().slice(0, 10);
                domain.push(["date_deadline", "<=", dateStr]);
                // Optionally filter out past if we want only 'Next' X days
                // domain.push(["date_deadline", ">=", today]); 
            }

            const activities = await this.orm.searchRead(
                "mail.activity",
                domain,
                ["summary", "res_name", "date_deadline", "activity_type_id", "res_model", "res_id"],
                { order: "date_deadline asc", limit: filter === "all" ? 20 : 10 }
            );
            return activities.map((activity, index) => {
                const title = activity.summary || activity.activity_type_id?.[1] || "Activity";
                const record = activity.res_name || "";
                const date = activity.date_deadline || "";
                return {
                    id: activity.id || index,
                    title,
                    record,
                    type: activity.activity_type_id?.[1] || "Task",
                    date,
                    isOverdue: Boolean(date && date < today),
                    app_xmlid: "mail.menu_root_discuss",
                    res_model: activity.res_model,
                    res_id: activity.res_id,
                };
            });
        } catch (error) {
            return [];
        }
    }

    async loadSecondaryData({ hasApp, cardDefs, formatCount, today }) {
        const defByKey = new Map(cardDefs.map((def) => [def.key, def]));
        const infoPromises = this.state.moduleCards.map(async (card) => {
            const def = defByKey.get(card.key);
            if (!def || !def.additionalInfo || !def.additionalInfo.length) {
                return card;
            }
            const infoItems = (await Promise.all(
                def.additionalInfo.map(async (info) => {
                    const infoCount = await this._getCount(info.model, info.domain);
                    if (infoCount !== null) {
                        return { ...info, value: formatCount(infoCount), app_xmlid: def.app_xmlid };
                    }
                    return null;
                })
            )).filter((i) => i);
            return { ...card, infoItems };
        });

        const [updatedCards, focusItems] = await Promise.all([
            Promise.all(infoPromises),
            this._loadFocusItems(hasApp, today),
        ]);

        this.state.moduleCards = updatedCards;
        this.state.focusItems = focusItems;
    }

    _updateMenu(appXmlId) {
        if (!appXmlId) return;
        const app = this.menuService.getApps().find((app) => app.xmlid === appXmlId);
        if (app) {
            this.menuService.setCurrentMenu(app);
        }
    }

    onCardClick(item) {
        if (item.action) {
            this._updateMenu(item.app_xmlid);
            this.actionService.doAction(item.action);
        }
    }

    onInfoItemClick(info, ev) {
        ev.stopPropagation();
        this._updateMenu(info.app_xmlid);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: info.label,
            res_model: info.model,
            domain: info.domain,
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    onFocusItemClick(item) {
        if (item.res_model && item.res_id) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: item.res_model,
                res_id: item.res_id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    get currentFocusLabel() {
        const labels = {
            "7": "Next 7 days",
            "today": "Today",
            "overdue": "Overdue",
            "14": "Next 14 days",
            "30": "Next 30 days",
            "all": "All",
        };
        return labels[this.state.focusFilter] || "Filter";
    }

    toggleFocusDropdown() {
        this.state.showFocusDropdown = !this.state.showFocusDropdown;
    }

    async onFocusFilterChange(val) {
        this.state.focusFilter = val;
        this.state.showFocusDropdown = false;
        const today = new Date().toISOString().slice(0, 10);
        const availableAppXmlIds = this.getAvailableAppXmlIds();
        const hasApp = (def) => !def.app_xmlid || availableAppXmlIds.has(def.app_xmlid);
        this.state.focusItems = await this._loadFocusItems(hasApp, today);
    }
}

registry.category("actions").add("lami_pine_backend_theme.home", TemplateThemeHome);
