# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PaymentDeposit(models.Model):
    _inherit = 'account.payment'

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('partner_id')
    def _onchange_partner_purchase_id(self):
        if self.payment_type == 'outbound':
            return self._onchange_partner_order_id('purchase_deposit_id', ['purchase'])

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def post(self):
        """
        Override
        Check the vendors of deposit and order for the last time before validating
        """
        self._validate_order_id('purchase_deposit_id', 'Purchase Order')
        return super(PaymentDeposit, self).post()
