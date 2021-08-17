odoo.define('l10n_us_accounting.ReconciliationModel', function (require) {
    "use strict";

    let StatementModel = require('account.ReconciliationModel').StatementModel;

    StatementModel.include({

        /**
         * Exclude a bank statement line, similar to validate()
         * @param handle
         */
        exclude: function (handle) {
            let line = this.getLine(handle);
            let handles = [];

            if (handle) {
                handles = [handle];
            } else {
                _.each(this.lines, function (line, handle) {
                    if (!line.reconciled && line.balance && !line.balance.amount && line.reconciliation_proposition.length) {
                        handles.push(handle);
                    }
                });
            }

            line.reconciled = true; // Actually this line is excluded but we can use this attributes as reconciled.
            this.valuemax--;        // Decrease total bank statement lines by 1.

            return this._rpc({
                model: 'account.bank.statement.line',
                method: 'action_exclude',
                args: [line.id],
                context: this.context
            }).then(function () {
                return {
                    handles: handles
                }
            })
        }
    });
});