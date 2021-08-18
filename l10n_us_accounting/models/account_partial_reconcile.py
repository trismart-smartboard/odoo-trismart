# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    debit_payment_id = fields.Many2one('account.payment', string='Debit payment',
                                       related='debit_move_id.payment_id', store=True)
    credit_payment_id = fields.Many2one('account.payment', string='Credit payment',
                                        related='credit_move_id.payment_id', store=True)
