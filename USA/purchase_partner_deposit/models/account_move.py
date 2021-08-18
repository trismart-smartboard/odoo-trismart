# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def action_post(self):
        """
        Override
        Apply deposits of PO to bill automatically
        """
        res = super(AccountMove, self).action_post()
        for invoice in self:
            if invoice.move_type == 'in_invoice':
                purchase_order_ids = invoice.invoice_line_ids.mapped('purchase_line_id.order_id')
                deposits = purchase_order_ids.mapped('deposit_ids')
                self._reconcile_deposit(deposits, invoice)
        return res
