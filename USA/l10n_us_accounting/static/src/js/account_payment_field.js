odoo.define('l10n_us_accounting.account_payment', function (require) {
    let ShowPaymentLineWidget = require('account.payment').ShowPaymentLineWidget;

    ShowPaymentLineWidget.include({
        /**
         * @override
         * Open popup to edit applied amount when users click on Outstanding payment.
         * @param {Object} event
         * @private
         */
        _onOutstandingCreditAssign: function (event) {
            event.stopPropagation();
            event.preventDefault();
            let self = this;
            let id = $(event.target).data('id') || false;

            return self.do_action({
                name: 'Amount to Apply',
                type: 'ir.actions.act_window',
                res_model: 'account.invoice.partial.payment',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    invoice_id: JSON.parse(this.value).move_id,
                    credit_aml_id: id
                }
            }, {
                on_close: function () {
                    self.trigger_up('reload');
                }
            });
        },
    });

    return ShowPaymentLineWidget;
});