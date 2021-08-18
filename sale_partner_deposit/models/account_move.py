# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountMoveDeposit(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def action_post(self):
        """
        Override
        Apply deposits of SO to invoice automatically
        """
        res = super(AccountMoveDeposit, self).action_post()

        for invoice in self:
            if invoice.move_type == 'out_invoice':
                sale_order_ids = self.env['sale.order']
                for line in invoice.invoice_line_ids:
                    sale_order_ids += line.sale_line_ids.mapped('order_id')
                deposits = sale_order_ids.mapped('deposit_ids')

                self._reconcile_deposit(deposits, invoice)
        return res
