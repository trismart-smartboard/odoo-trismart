// We will define our own convertFormulas function to override PARSE function
// of Odoo OOTB.
// Some functions need to be redefined to use convertFormulas:
// convertPivotsFormulas, _removeInvalidPivotRows, getDataFromTemplate

odoo.define('account_budget_spreadsheet.BudgetSpreadsheetWidget', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var widget_registry = require('web.widget_registry');
    const {relativeToAbsolute, fetchCache, getCells} = require("documents_spreadsheet.pivot_utils");
    const spreadsheet_utils = require("account_budget_spreadsheet.o_spreadsheet_utils");
    const {_parse} = spreadsheet_utils
    const {astToFormula} = require("documents_spreadsheet.spreadsheet")
    const {Model} = require("documents_spreadsheet.spreadsheet");
    const core = require('web.core');
    var _t = core._t;

    var BudgetSpreadsheetWidget = Widget.extend({
            template: 'account_budget_spreadsheet.budget_spreadsheet_button',
            events: _.extend({}, Widget.prototype.events, {
                '.create_new_spreadsheet': '_createSpreadsheet'
            }),
            convertFormulas: function convertFormulas(cells, convertFunction, ...args) {

                cells.forEach((cell) => {
                    const ast = convertFunction(_parse(cell.content), ...args);
                    cell.content = ast ? `=${astToFormula(ast)}` : "";
                });
            },
            convertPivotFormulas: async function convertPivotFormulas(rpc, cells, convertFunction, pivots, ...args) {
                const self = this;
                if (!pivots || pivots.length === 0) return;
                await Promise.all(Object.values(pivots).map((pivot) => fetchCache(pivot, rpc)));
                self.convertFormulas(cells, convertFunction, pivots, ...args);
                Object.values(pivots).forEach((pivot) => {
                    pivot.cache = undefined;
                    pivot.lastUpdate = undefined;
                    pivot.isLoaded = false;
                })
            },
            _removeInvalidPivotRows: function _removeInvalidPivotRows(rpc, data) {
                const self = this;
                const model = new Model(data, {
                    mode: "headless",
                    evalContext: {
                        env: {
                            services: {rpc},
                        },
                    },
                });
                for (let sheet of model.getters.getSheets()) {
                    const invalidRows = [];
                    for (let rowIndex = 0; rowIndex < model.getters.getNumberRows(sheet.id); rowIndex++) {
                        const {cells} = model.getters.getRow(sheet.id, rowIndex);
                        const [valid, invalid] = Object.values(cells)
                            .filter((cell) => /^\s*=.*PIVOT/.test(cell.content))
                            .reduce(
                                ([valid, invalid], cell) => {
                                    const isInvalid = /^\s*=.*PIVOT(\.HEADER)?.*#IDNOTFOUND/.test(cell.content);
                                    return [isInvalid ? valid : valid + 1, isInvalid ? invalid + 1 : invalid];
                                },
                                [0, 0]
                            );
                        if (invalid > 0 && valid === 0) {
                            invalidRows.push(rowIndex);
                        }
                    }
                    model.dispatch("REMOVE_ROWS", {rows: invalidRows, sheet: sheet.id});
                }
                data = model.exportData();
                self.convertFormulas(
                    getCells(data, /^\s*=.*PIVOT.*#IDNOTFOUND/),
                    () => null,
                );
                return data;
            },
            getDataFromTemplate: async function getDataFromTemplate(rpc, templateId) {
                const self = this;
                let [{data}] = await rpc({
                    method: "read",
                    model: "spreadsheet.template",
                    args: [templateId, ["data"]],
                });
                data = JSON.parse(atob(data));
                const {pivots} = data;
                await self.convertPivotFormulas(rpc, getCells(data, /^\s*=.*PIVOT/), relativeToAbsolute, pivots);
                return self._removeInvalidPivotRows(rpc, data);
            }
            ,

            init: function (parent, params) {
                this.data = params.data;
                this.fields = params.fields;
                this._super(parent);
            }
            ,

            start: function () {
                const self = this;
                this.$el.bind('click', function () {
                    const data = self.data;
                    return self._createSpreadsheet(data);
                });
            }
            ,
            updateState: function (state) {
                this.data = state.data;
            }
            ,
            _createSpreadsheet(data) {
                const {name, report_type, period_type, year, analytic_account_id, create_budget_from_last_year} = data;
                if (name === false){
                    return this.do_warn(_t("Warning"), 'Name must be required');
                }
                let analytic_account = false;
                if (data['analytic_account_id']) {
                    analytic_account = analytic_account_id['data']['id'];
                }

                let self = this;
                this._rpc({
                    model: 'documents.document',
                    method: 'create_spreadsheet_from_report',
                    args: [[], period_type, report_type, name, year, analytic_account, create_budget_from_last_year]
                }).then(async function (data) {
                    let spreadsheetId = data['spreadsheet_id']
                    const processed_data = await self.getDataFromTemplate(self._rpc.bind(self), spreadsheetId);
                    const spreadsheet_id = await self._rpc({
                        model: "documents.document",
                        method: "create",
                        args: [
                            {
                                name: data['spreadsheet_name'],
                                mimetype: "application/o-spreadsheet",
                                handler: "spreadsheet",
                                raw: JSON.stringify(processed_data),
                                is_budget_spreadsheet: true,
                                folder_id: data['folder_id'],
                                report_type: report_type,
                                period_type: period_type,
                                analytic_account_id: data['analytic_account_id'],
                                year: year
                            },
                        ],
                    });
                    self.do_action({
                        type: "ir.actions.client",
                        tag: "action_open_spreadsheet",
                        params: {
                            active_id: spreadsheet_id,
                        },
                    });
                });
            }
            ,

        })
    ;

    widget_registry.add('budget_spreadsheet_widget', BudgetSpreadsheetWidget);

    return BudgetSpreadsheetWidget;
});
