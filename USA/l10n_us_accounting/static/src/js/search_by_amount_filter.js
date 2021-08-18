odoo.define('l10n_us_accounting.SearchByAmountFilter', function (require) {
    const Domain = require('web.Domain');
    const DropdownMenuItem = require('web.DropdownMenuItem');
    const patchMixin = require('web.patchMixin');
    const { useModel } = require('web/static/src/js/model.js');
    const FilterMenu = require('web.FilterMenu');
    const { hooks } = owl;
    const { useRef, useState } = hooks;
    const Dialog = require('web.Dialog');

    class SearchByAmountFilter extends DropdownMenuItem {
        constructor() {
            super(...arguments);
            this.model = useModel('searchModel');
            this.modelContext = this.model.config && this.model.config.context || {};
            this.searchByAmountRef = useRef('search_by_amount_filter');
            this.minValRef = useRef('min_val');
            this.maxValRef = useRef('max_val');
            this.state = useState({open: true});
        }

        /*
        * @Override
        * Show Search By Amount in filter
        * */
        mounted() {
            super.mounted(...arguments);
            if (this.modelContext.searchByAmountFilter) {
                this.searchByAmountRef.el.classList.toggle('d-none');
            }
        }

        validateValue(value, name) {
            if (!$.isNumeric(value)) {
                this._showErrorMessage(name + ' value must be a valid number');
                return false;
            }
            if (this.isNegativeChecking && value < 0) {
                this._showErrorMessage(name + ' value must not be less than 0.0');
                return false;
            }
            return true;
        }

        _showErrorMessage(message) {
            new Dialog(this, {
                title: 'Validation error!',
                size: 'medium',
                $content: $('<div>').html('<p>' + message + '<p/>')
            }).open();
        }

        _onApplyAmountFilter() {
            let minVal = parseFloat(this.minValRef.el.value);
            if (!this.validateValue(minVal, 'Min')) {
                return false;
            }
            let maxVal = parseFloat(this.maxValRef.el.value);
            if (!this.validateValue(maxVal, 'Max')) {
                return false;
            }
            if (maxVal < minVal) {
                this._showErrorMessage('Max value must be greater than or equal to Min value');
                return false;
            }
            let filter = [{
                description: 'Amount from "' + minVal.toString() + '" to "' + maxVal.toString() + '"',
                domain: Domain.prototype.arrayToString([
                    [this.modelContext.compareField, '<=', maxVal],
                    [this.modelContext.compareField, '>=', minVal]
                ])
            }];
            // Create new filter
            this.model.dispatch('createNewFilters', filter);
        }
    }

    SearchByAmountFilter.props = {
        fields: Object,
    };
    SearchByAmountFilter.template = 'l10n_us_accounting.SearchByAmountFilter';

    FilterMenu.components = Object.assign({}, FilterMenu.components, {
        SearchByAmountFilter,
    });

    return patchMixin(SearchByAmountFilter);
});