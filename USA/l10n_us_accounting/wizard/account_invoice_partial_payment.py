# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning


class PartialPayment(models.TransientModel):
    _name = 'account.invoice.partial.payment'
    _description = 'Partial Payment'

    currency_id = fields.Many2one('res.currency', readonly=True)
    amount = fields.Monetary('Amount')
    invoice_id = fields.Many2one('account.move')
    move_line_id = fields.Many2one('account.move.line')
    have_same_currency = fields.Boolean(compute='_get_have_same_currency')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('invoice_id', 'move_line_id')
    def _get_have_same_currency(self):
        for record in self:
            have_same_currency = False
            if record.invoice_id and record.move_line_id:
                move_line_currency = record.move_line_id.currency_id or self.env.company.currency_id
                if record.invoice_id.currency_id.id == move_line_currency.id:
                    have_same_currency = True
            record.have_same_currency = have_same_currency

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    @api.model
    def default_get(self, fields):
        res = super(PartialPayment, self).default_get(fields)

        invoice_id = self.env['account.move'].browse(self.env.context.get('invoice_id'))
        move_line_id = self.env['account.move.line'].browse(self.env.context.get('credit_aml_id'))

        res.update({
            'invoice_id': self.env.context.get('invoice_id'),
            'move_line_id': self.env.context.get('credit_aml_id'),
            'currency_id': invoice_id.currency_id.id
        })

        amount_due = invoice_id.amount_residual

        if move_line_id.currency_id and move_line_id.currency_id == invoice_id.currency_id:
            payment_amount = abs(move_line_id.amount_residual_currency)
        else:
            currency = move_line_id.company_id.currency_id
            payment_amount = currency._convert(abs(move_line_id.amount_residual), invoice_id.currency_id,
                                               invoice_id.company_id, move_line_id.date or fields.Date.today())

        res['amount'] = amount_due < payment_amount and amount_due or payment_amount
        return res

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def apply(self):
        if not self.have_same_currency:  # we don't need to validate the amount if they have different currency
            self.invoice_id.js_assign_outstanding_line(self.move_line_id.id)
        else:
            if self.amount <= 0:
                raise Warning(_('You entered an invalid value. Please make sure you enter a value is greater than 0.'))
            elif self.amount > abs(self.move_line_id.amount_residual_currency) or self.amount > self.invoice_id.amount_residual:
                raise Warning(_('You entered a value that exceeds the amount due/outstanding amount of the transactions'))
            self.invoice_id.with_context(partial_amount=self.amount).js_assign_outstanding_line(self.move_line_id.id)

        return True
