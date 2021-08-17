# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_is_zero, float_compare


class AccountPaymentLine(models.Model):
    _name = 'account.payment.line'
    _description = 'Payment Lines'
    _rec_name = 'account_move_line_id'

    # == Business fields ==
    payment_id = fields.Many2one('account.payment', ondelete='cascade')
    account_move_line_id = fields.Many2one('account.move.line', ondelete='cascade')
    payment = fields.Monetary('Payment Amount')

    # == Related/Computed fields ==
    currency_id = fields.Many2one(related='payment_id.currency_id', store=True)
    partner_id = fields.Many2one('res.partner', related='payment_id.partner_id', store=True)
    move_id = fields.Many2one('account.move', related='account_move_line_id.move_id', store=True)

    # == Computed fields ==
    date_invoice = fields.Date('Transaction Date', compute='_get_amount_residual', store=True)
    date_due = fields.Date('Due Date', compute='_get_amount_residual', store=True)
    amount_total = fields.Monetary('Total', compute='_get_amount_residual', store=True)
    residual = fields.Monetary('Amount Due', compute='_get_amount_residual', store=True)

    # == Display purpose fields ==

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('account_move_line_id', 'account_move_line_id.balance',
                 'account_move_line_id.amount_residual', 'account_move_line_id.date_maturity',
                 'move_id', 'move_id.date', 'move_id.invoice_date', 'move_id.invoice_date_due')
    def _get_amount_residual(self):
        for record in self:
            date_invoice = date_due = amount_total = residual = False
            move_id = record.move_id
            aml_id = record.account_move_line_id

            if aml_id:
                # Journal entry (invoice_id.type = 'entry') won't have value of `invoice_date` and `invoice_date_due`
                # So get value of `date` for `date_invoice` and `date_due` instead.
                date_invoice = move_id and (move_id.invoice_date or move_id.date)
                date_due = aml_id.date_maturity or move_id and move_id.invoice_date_due or move_id.date

                if aml_id.currency_id:
                    amount_total = abs(aml_id.amount_currency)
                    residual = abs(aml_id.amount_residual_currency)
                else:
                    amount_total = abs(aml_id.balance)
                    residual = abs(aml_id.amount_residual)

            record.date_invoice = date_invoice
            record.date_due = date_due
            record.amount_total = amount_total
            record.residual = residual

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('partner_id')
    def _onchange_partner(self):
        """
        Run when add new open invoice to payment.
        :return: domain for available invoices to add.
        """
        if self.partner_id:
            return {
                'domain': {'account_move_line_id': [('id', 'in', self.payment_id.available_move_line_ids.ids)]},
            }

    @api.onchange('account_move_line_id')
    def _onchange_account_move(self):
        if self.account_move_line_id:
            self.payment = self.residual

    @api.onchange('payment')
    def _onchange_payment_amount(self):
        if self.payment <= 0 and self.account_move_line_id:
            raise ValidationError(_('Please enter an amount greater than 0'))

        rounding = self.currency_id.rounding
        if float_compare(self.payment, self.residual, precision_rounding=rounding) == 1:
            self.payment = self.residual

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------
    @api.constrains('residual')
    def _check_residual_amount(self):
        """
        This is for when the transaction gets applied in some other places.
        => we either change the payment amount or remove the line (full reconciled)
        :return:
        """
        for record in self:
            rounding = record.currency_id.rounding
            if float_is_zero(record.residual, precision_rounding=rounding) and record.id:
                record.unlink()
            elif float_compare(record.payment, record.residual, precision_rounding=rounding) == 1:
                record.write({'payment': record.residual})

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    @api.constrains('payment')
    def _check_payment_amount(self):
        for record in self:
            if record.payment <= 0:
                raise ValidationError(_('Payment Amount must be greater than 0'))

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
