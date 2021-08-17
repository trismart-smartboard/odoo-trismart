odoo.define('l10n_us_accounting.ManualReconciliationRenderer', function (require) {
    "use strict";
    const field_utils = require('web.field_utils');
    let ManualLineRenderer = require('account.ReconciliationRenderer').ManualLineRenderer;

    ManualLineRenderer.include({
        events: _.extend({}, ManualLineRenderer.prototype.events, {
            'click table.accounting_view td.sort': '_onSortColumn',
        }),
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
    });
});