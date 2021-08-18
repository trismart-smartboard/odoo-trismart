odoo.define('l10n_us_accounting.dialog', function (require) {
    'use strict';

    let Dialog = require('web.Dialog');

    let USADialog = Dialog.include({
        init: function (parent, options) {
            this._super(parent, options);
            if (parent) {
                let found_action = _.find(parent.actions, function (act) {
                    return act.xml_id === 'l10n_us_accounting.action_record_ending_balance';
                });
                this.hide_close_btn = found_action && found_action.hide_close_btn || false;
            }
        },

        willStart: function () {
            return this._super.apply(this, arguments).then(function () {
                if (this.hide_close_btn) {
                    this.$modal.find('button[data-dismiss="modal"]').css('visibility', 'hidden');
                }
            }.bind(this));
        },
    });
});
