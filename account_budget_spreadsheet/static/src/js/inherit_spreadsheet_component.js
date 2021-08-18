// topBarMenuRegistry is where action is implemented for example: Save as template, New, Make a copy, ...
// If we want to add a new action to topBarMenuRegistry, we need to add a child to this class define: Name, Action ((env)=>{some function}),...
odoo.define("account_budget_spreadsheet.InheritSpreadsheetComponent", function (require) {
    "use strict";

    const core = require("web.core");
    var framework = require('web.framework');
    var session = require('web.session');
    const _t = core._t;
    const extended_spreadsheet = require("documents_spreadsheet.spreadsheet_extended");

    // This funtion is used to calculated the actual row of spreadsheet
    const calculateNumRows = (cells) => {
        let numRows = 0;
        let list_keys = Object.keys(cells);
        list_keys.forEach(function (value, index) {
            if (value[0] === 'A' && !isNaN(parseInt(value[1]))) {
                numRows += 1;
            }
        })
        return numRows;

    }
    const topBarMenuRegistry = extended_spreadsheet.registries.topbarMenuRegistry;
     // We add child to the top Bar to add another action in File menu
    topBarMenuRegistry.addChild("export_to_xlsx", ["file"], {
        name: _t("Export to Excel"),
        sequence: 50,
        action: (env) => {
            const sheet = env.getters.getSheets()[0];
            let cells = sheet.cells;
            let rows = sheet.rows;
            const numRows = calculateNumRows(cells);

            let options = {};
            let data = []
            let self = this;
            for (let r = 0; r < numRows; r++) {
                let row = rows[r].cells;
                let opt = {};
                if (row && Object.keys(row).length === 0) {
                    opt['data'] = [];
                } else {
                    let numCols = Object.keys(row);
                    let cols = [];
                    let list_keys = Object.keys(numCols);
                    list_keys.forEach(function (value, index) {
                        let col = row[value].value;
                        cols.push(col);
                    })
                    opt['data'] = cols;
                }
                data.push(opt);
            }
            options.data = data;
            var action_data = {
                financial_id: null,
                model: 'usa.budget.entry',
                output_format: "xlsx",
                options: JSON.stringify(options),
            };
            // Export File
            framework.blockUI();
            var def = $.Deferred();
            session.get_file({
                url: '/account_reports',
                data: action_data,
                success: def.resolve.bind(def),
                error: function (error) {
                    self.call('crash_manager', 'rpc_error', error);
                    def.reject();
                },
                complete: framework.unblockUI,
            });
        },
    });
    extended_spreadsheet.registries.topbarMenuRegistry = topBarMenuRegistry;
});
