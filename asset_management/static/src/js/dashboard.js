/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class AssetDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            kpis: {},
            loading: true,
        });

        onWillStart(async () => {
            await this.loadKpis();
        });
    }

    async loadKpis() {
        const kpis = await this.orm.call("am.dashboard", "get_kpis", [], {});
        this.state.kpis = kpis;
        this.state.loading = false;
    }

    async openAvailableAssets() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "asset.asset",
            name: "Available Assets",
            domain: [["state", "=", "available"]],
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async openAllocatedAssets() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "asset.asset",
            name: "Allocated Assets",
            domain: [["state", "=", "allocated"]],
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async openMaintenance() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "asset.asset",
            name: "Assets in Maintenance",
            domain: [["state", "=", "maintenance"]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async openActiveBookings() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "resource.booking",
            name: "Active Bookings",
            domain: [["state", "in", ["upcoming", "ongoing"]]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async openPendingTransfers() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "asset.transfer",
            name: "Pending Transfers",
            domain: [["state", "=", "requested"]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async openUpcomingReturns() {
        const today = new Date().toISOString().split("T")[0];
        const weekEnd = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "asset.allocation",
            name: "Upcoming Returns",
            domain: [
                ["state", "=", "allocated"],
                ["expected_return_date", ">=", today],
                ["expected_return_date", "<=", weekEnd],
            ],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async openOverdueReturns() {
        const today = new Date().toISOString().split("T")[0];
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "asset.allocation",
            name: "Overdue Returns",
            domain: [
                ["state", "=", "allocated"],
                ["expected_return_date", "<", today],
            ],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async openQuickRegister() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "asset.asset",
            name: "Register Asset",
            views: [[false, "form"]],
            target: "new",
        });
    }

    async openQuickBook() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "resource.booking",
            name: "Book Resource",
            views: [[false, "form"]],
            target: "new",
        });
    }

    async openQuickMaintenance() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "am.maintenance.request",
            name: "Raise Maintenance Request",
            views: [[false, "form"]],
            target: "new",
        });
    }
}

AssetDashboard.template = "asset_management.Dashboard";

registry.category("actions").add("am_dashboard", AssetDashboard);
