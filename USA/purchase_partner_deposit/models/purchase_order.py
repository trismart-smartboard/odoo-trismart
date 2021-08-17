# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class DepositPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    deposit_ids = fields.One2many('account.payment', 'purchase_deposit_id', string='Deposits', domain=[('state', '!=', 'draft')])
    deposit_count = fields.Integer('Deposit Count', compute='_get_deposit_total', store=True)
    deposit_total = fields.Monetary(string='Total Deposit', compute='_get_deposit_total', store=True)
    remaining_total = fields.Monetary(string='Net Total', compute='_get_deposit_total', store=True)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('amount_total', 'deposit_ids', 'deposit_ids.state')
    def _get_deposit_total(self):
        for order in self:
            deposit_total_signed = sum(order.deposit_ids.mapped('amount_total_signed'))
            # Convert total deposit to currency of SO using currency date is purchase order date
            deposit_total = order.company_id.currency_id._convert(
                deposit_total_signed,
                order.currency_id,
                order.company_id,
                order.date_order or fields.Date.today()
            )
            order.update({
                'deposit_total': deposit_total,
                'deposit_count': len(order.deposit_ids),
                'remaining_total': order.amount_total - deposit_total,
            })

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def action_view_deposit(self):
        action = self.sudo().env.ref('account_partner_deposit.action_account_payment_supplier_deposit').read()[0]
        action['domain'] = [('id', 'in', self.deposit_ids.ids)]
        return action

    def button_cancel(self):
        """
        Override
        Unlink deposits when canceling POs
        """
        res = super(DepositPurchaseOrder, self).button_cancel()
        for order in self.sudo().filtered(lambda x: x.state == 'cancel'):
            order.deposit_ids = [(5, 0, 0)]
        return res
