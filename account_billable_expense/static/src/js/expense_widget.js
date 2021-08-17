odoo.define('account_billable_expense.ExpenseWidget', function (require) {
"use strict";

var core = require('web.core');
var QWeb = core.qweb;

var Widget = require('web.Widget');
var widget_registry = require('web.widget_registry');

var _t = core._t;

var ExpenseWidget = Widget.extend({
    template: 'account_billable_expense.InfoCircle',
    events: _.extend({}, Widget.prototype.events, {
        'click .fa-info-circle': '_onClickButton',
    }),

    init: function (parent, params) {
        this.data = params.data;
        this.fields = params.fields;
        this._super(parent);
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._setPopOver();
        });
    },
    updateState: function (state) {
        this.$el.popover('dispose');
        var candidate = state.data[this.getParent().currentRow];
        if (candidate) {
            this.data = candidate.data;
            this.renderElement();
            this._setPopOver();
        }
    },

    _openInv() {
        this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'account.move',
                view_mode: 'form',
                res_id: this.data.invoiced_to_id.res_id,
                views: [[false, 'form']],
                target: 'current',
            });
    },

    _getContent() {
        const $content = $(QWeb.render('account_billable_expense.InfoPopOver', {
            data: this.data,
        }));
        $content.on('click', '.action_open_inv', this._openInv.bind(this));
        return $content;
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    _setPopOver() {
        const $content = this._getContent();
        if (!$content) {
            return;
        }
        const options = {
            content: $content,
            html: true,
            placement: 'left',
            title: _t('Billable Expense Info'),
            trigger: 'focus',
            delay: {'show': 0, 'hide': 100 },
        };
        this.$el.popover(options);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    _onClickButton: function () {
        this.$el.find('.fa-info-circle').prop('special_click', true);
    },
});

widget_registry.add('billable_expense_widget', ExpenseWidget);

return ExpenseWidget;
});
