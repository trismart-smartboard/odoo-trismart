odoo.define("documents_spreadsheet.BudgetListView", function (require) {
    "use strict";

    const ListController = require("web.ListController");
    const ListView = require("web.ListView");
    const DocumentsListView = require('documents.DocumentsListView');
    const viewRegistry = require("web.view_registry");

    const BudgetController = ListController.extend({
        _onButtonClicked(ev) {
            this._super(...arguments);
            const {attrs, record} = ev.data;
            if (attrs.name === "open_budget") {
                this._openSpreadsheet(record);
            }
        },
        /**
         * Open a document
         *
         * @param {record}
         */
        _openSpreadsheet(record) {
            this.do_action({
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    active_id: record.data.id,
                },
            });

        },
    });

    const BudgetListView = ListView.extend({
        config: Object.assign({}, DocumentsListView.prototype.config, {
            Controller: BudgetController,
        }),
    });

    viewRegistry.add("budget_spreadsheet_list", BudgetListView);
    return BudgetListView;
});
