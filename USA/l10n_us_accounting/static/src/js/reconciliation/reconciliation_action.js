odoo.define('l10n_us_accounting.ReconciliationClientAction', function (require) {
    "use strict";

    let StatementAction = require('account.ReconciliationClientAction').StatementAction;

    StatementAction.include({
        custom_events: _.extend({}, StatementAction.prototype.custom_events, {
            exclude: '_onExclude',
        }),

        /**
         * Exclude a bank statement line, similar to _onValidate(event)
         * @param {event} event
         * @private
         */
        _onExclude: function (event) {
            var self = this;
            var handle = event.target.handle;

            this.model.exclude(handle).then(function (result) {
                self.renderer.update({
                    'valuenow': self.model.valuenow,
                    'valuemax': self.model.valuemax,
                    'title': self.title,
                    'time': Date.now()-self.time,
                    'notifications': result.notifications,
                    'context': self.model.getContext(),
                });
                self._forceUpdate();
                _.each(result.handles, function (handle) {
                    var widget = self._getWidget(handle);
                    if (widget) {
                        widget.destroy();
                        var index = _.findIndex(self.widgets, function (widget) {return widget.handle===handle;});
                        self.widgets.splice(index, 1);
                    }
                });
                self._openFirstLine(handle);
            });
        },

    });
});