odoo.define('l10n_us_accounting.ReconciliationRenderer', function (require) {
    "use strict";
    var session = require("web.session");
    const field_utils = require('web.field_utils');
    let LineRenderer = require('account.ReconciliationRenderer').LineRenderer;
    const mappingFormatTable = {
        '%d': 'dd',
        '%m': 'mm',
        '%Y': 'yy'
    }
    LineRenderer.include({
        events: _.extend({}, LineRenderer.prototype.events, {
            'click .accounting_view caption .o_exclude_button button': '_onExclude',
            'click table.accounting_view td.sort': '_onSortColumn',
        }),
        start: function () {
            let state = this._initialState;
            let model = _.find(state.reconcileModels, function (item) {
                return item.id === state.model_id;
            });
            let $modelName = this.$el.find('div.reconciliation_model_name');
            if (model && state.reconciliation_proposition.length > 0) {
                $modelName.css('display', 'inline-block');
                $modelName.find('span').text(model.name);
            }
            let self = this;

            return this._super.apply(this, arguments).then(function () {
                let numOfLines = self.$el.find('table.accounting_view tbody tr.mv_line').length;
                if (numOfLines === 0) {
                    self._hideReconciliationModelName();
                }
            });
        },

        /**
         * @override
         * Handle when users click on each bank statement line, change partner, update transaction lines...
         * @param {Object} state
         */
        update: function (state) {
            // Remove Bank rule name
            let numOfLines = this.$el.find('table.accounting_view tbody tr.mv_line').length;
            this.filterBatchPayment(state);
            this._super.apply(this, arguments);
            let numOfLinesAfter = this.$el.find('table.accounting_view tbody tr.mv_line').length;
            if (numOfLinesAfter !== numOfLines) {
                this._hideReconciliationModelName();
            }
        },

        /**
         * Odoo calls 'get_batch_payments_data' to get all un-reconciled batch payments and apply them for all BSL.
         * We need to filter them in the suggested list of each based BSL:
         *      Journal must be the same as journal of BSL
         *      Amount of batch payment <= amount of BSL
         *      If st_line.amount_currency < 0, choose OUT batch payment, else IN batch payment.
         * @param {Object} state
         */
        filterBatchPayment: function (state) {
            let relevant_payments = state.relevant_payments;

            if (relevant_payments.length > 0 && state.st_line) {
                let bsl_amount = state.st_line.amount_currency;
                let journal_id = state.st_line.journal_id;

                state.relevant_payments = relevant_payments.filter(batch =>
                    (batch.journal_id === journal_id) &&
                    (bsl_amount < 0 ? batch.type === 'outbound' && batch.filter_amount <= -bsl_amount
                        : batch.type === 'inbound' && batch.filter_amount <= bsl_amount)
                )
            }
        },

        /**
         * @override
         * Handle if users change fields, such as partner.
         * @param {event} event
         * @private
         */
        _onFieldChanged: function (event) {
            let fieldName = event.target.name;
            if (fieldName === 'partner_id') {
                this._hideReconciliationModelName();
            }
            this._super.apply(this, arguments);
        },

        /**
         * Exclude bank statement line.
         * @private
         */
        _onExclude: function () {
            this.trigger_up('exclude');
        },

        /**
         * @override
         * Hide reconciliation model name when removing proposition line
         * @param {event} event
         * @private
         */
        _onSelectProposition: function (event) {
            // this._onClickRemovePayee(event);
            this._hideReconciliationModelName();
            this._super.apply(this, arguments);
        },

        /**
         * @override
         * Hide reconciliation model name when adding line
         * @param {event} event
         * @private
         */
        _onSelectMoveLine: function (event) {
            this._super.apply(this, arguments);
            this._hideReconciliationModelName();
        },


        /**
         * Get current active currencies of current user
         * @param
         */
        getCurrentCurrency() {
            const currentCurrencies = this._rpc({
                model: "res.currency",
                method: "search_read",
                fields: ["symbol"],
                domain: [["active", "=", true]],
            }).then(function (result) {
                return result.map(record => record.symbol).join('');
            });
            return currentCurrencies;
        },
        /**
         * Get float number format for current language of current user.
         * @param
         */
        getLanguageFormat() {
            const currentFormat = this._rpc({
                model: "res.lang",
                method: "search_read",
                fields: ["date_format"],
                domain: [["code", "=", session.user_context.lang]],
            }).then(function (result) {
                let pythonDateFormat = result[0].date_format;
                let dateSeparator = pythonDateFormat[2]
                let pythonDateFormatList = pythonDateFormat.split(dateSeparator);
                let jsDateFormat = pythonDateFormatList.map(record => mappingFormatTable[record])
                return jsDateFormat.join(dateSeparator);
            });
            return currentFormat;
        },
        /**
         * Sort suggested matching list when users click on header of table.
         * @param {event} event
         * @private
         */
        _onSortColumn: async function (event) {
            // Convert string to other values
            var date_format = await this.getLanguageFormat();
            let currencies = await this.getCurrentCurrency();
            let strDateToDate = (str) => $.datepicker.parseDate(date_format, str);
            let strCurrencyToNum = (str) => {
                const currencySymbolRegex = RegExp(`[${currencies}]`, 'g');
                return field_utils.parse.float(str.replace(currencySymbolRegex, "").trim()).toFixed(2);
            }
            let strNumToNum = str => Number(str.replace(/\u200B/g, ''));

            // Get string value from a cell.
            let getCellValue = (row, index) => $(row).children('td').eq(index).text().trim();

            // Get function to sort (ASC)
            let comparer = (index, sort_type) => (a, b) => {
                let valA = getCellValue(a, index);
                let valB = getCellValue(b, index);
                switch (sort_type) {
                    case 'number':
                        return strNumToNum(valA) - strNumToNum(valB);
                    case 'currency':
                        return strCurrencyToNum(valA) - strCurrencyToNum(valB);
                    case 'date':
                        return strDateToDate(valA) - strDateToDate(valB);
                    case 'text':
                        return valA.localeCompare(valB);
                }
            };

            let tables = this.$el.find('table.table_sort');
            // Suggested matching list has been displayed or not.
            let display = window.getComputedStyle(this.$el.find('.o_notebook')[0]).getPropertyValue('display');

            if (tables.length > 0 && display !== 'none') {
                let index = event.target.cellIndex;
                let sort_type = event.target.getAttribute('sort_type');
                let sort_mode = event.target.getAttribute('sort_mode') || 'asc';

                // Remove sort icon and sort mode for all headers
                let cols = this.$el.find('tr.header td.sort');
                _.each(cols, col => {
                    col.setAttribute('sort_mode', '');
                    let icon = $(col).find('span.sort_icon')[0];
                    if (icon) {
                        icon.innerHTML = '';
                    }
                });

                // Update sort icon: up arrow (ASC) or down arrow (DESC)
                let sort_icon = $(event.target).find('span.sort_icon')[0];
                if (sort_icon) {
                    sort_icon.innerHTML = sort_mode === 'desc' ? '&uarr;' : '&darr;';
                }

                // Update sort mode: 'asc' or 'desc'
                event.target.setAttribute('sort_mode', sort_mode === 'desc' ? 'asc' : 'desc');

                _.each(tables, table => {
                    // Get rows after sorting in ASC order.
                    let rows = $(table).find('tr').toArray().sort(comparer(index, sort_type));
                    // Revert rows if sorting in DESC order.
                    rows = sort_mode === 'asc' ? rows.reverse() : rows;
                    _.each(rows, row => $(table).append(row));
                })
            }
        },
        /**
         * @override
         * Hide reconciliation model name when modifying input amount
         * @param {event} event
         * @private
         */
        _editAmount: function (event) {
            this._super.apply(this, arguments);
            this._hideReconciliationModelName();
        },
        _hideReconciliationModelName: function () {
            this.$el.find('div.reconciliation_model_name').hide();
        },

        /**
         * @override
         * Disable edit partial amount feature -> call onSelect to remove the line
         */
        _onEditAmount: function (event) {
            this._onSelectProposition(event);
        },
    });
});