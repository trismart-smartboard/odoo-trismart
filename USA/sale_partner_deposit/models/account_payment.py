# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PaymentDeposit(models.Model):
    _inherit = 'account.payment'

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('partner_id')
    def _onchange_partner_sale_id(self):
        if self.payment_type == 'inbound':
            return self._onchange_partner_order_id('sale_deposit_id', ['sale'])

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def post(self):
        """
        Override
        Check the customers of deposit and order for the last time before validating
        """
        self._validate_order_id('sale_deposit_id', 'Sales Order')
        return super(PaymentDeposit, self).post()
