# -*- coding: utf-8 -*-
import json
from odoo import api, fields, models, _
from odoo.tools import float_is_zero
from odoo.exceptions import ValidationError


class AccountMoveDeposit(models.Model):
    _inherit = 'account.move'

    is_deposit = fields.Boolean('Is a Deposit?')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    def _compute_payments_widget_to_reconcile_info(self):
        """
        Override to add deposit payments to payment widget on invoice/bill
        """
        super(AccountMoveDeposit, self)._compute_payments_widget_to_reconcile_info()

        for move in self:
            info = json.loads(move.invoice_outstanding_credits_debits_widget)

            if move.state != 'posted' or move.payment_state not in ('not_paid', 'partial')  \
                    or move.move_type not in ['out_invoice', 'in_invoice']:
                continue

            payment_type = move.move_type == 'out_invoice' and 'inbound' or 'outbound'
            domain = [('account_id.reconcile', '=', True),
                      ('payment_id.is_deposit', '=', True),
                      ('payment_id.payment_type', '=', payment_type),
                      ('move_id.state', '=', 'posted'),
                      ('partner_id', '=', move.commercial_partner_id.id),
                      ('reconciled', '=', False),
                      '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0)]

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                type_payment = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                type_payment = _('Outstanding debits')

            if not info:
                info = {'title': type_payment, 'outstanding': True, 'content': [], 'move_id': move.id}
            lines = self.env['account.move.line'].search(domain)

            if len(lines) != 0:
                for line in lines:
                    if line.currency_id == move.currency_id:
                        # Same foreign currency.
                        amount = abs(line.amount_residual_currency)
                    else:
                        # Different foreign currencies.
                        amount = move.company_currency_id._convert(
                            abs(line.amount_residual),
                            move.currency_id,
                            move.company_id,
                            line.date,
                        )

                    if move.currency_id.is_zero(amount):
                        continue

                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount,
                        'currency': move.currency_id.symbol,
                        'id': line.id,
                        'position': move.currency_id.position,
                        'payment_id': line.payment_id.id,
                        'digits': [69, move.currency_id.decimal_places],
                        'payment_date': fields.Date.to_string(line.date),
                    })
                move.invoice_outstanding_credits_debits_widget = json.dumps(info)
                move.invoice_has_outstanding = True

    @api.depends('batch_fund_line_id', 'is_deposit')
    def _compute_is_line_readonly(self):
        super()._compute_is_line_readonly()

        for record in self.filtered('is_deposit'):
            record.is_line_readonly = True

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def button_draft(self):
        """
        When we set an invoice/bill to draft, we want to delete all the linked Deposit JE
        so next time it will display the Deposit Payment
        """
        non_entry_ids = self.filtered(lambda x: x.move_type != 'entry')

        for move in non_entry_ids:
            line_ids = move.mapped('line_ids')
            sql = """
                SELECT am.id
                    FROM account_partial_reconcile as apr
                    JOIN account_move_line as aml ON (apr.debit_move_id = aml.id OR apr.credit_move_id = aml.id) AND 
                                                        (apr.debit_move_id IN {} OR apr.credit_move_id IN {})
                    JOIN account_move as am ON am.id = aml.move_id
                WHERE am.is_deposit = TRUE AND am.state = 'posted';
            """.format(tuple(line_ids.ids), tuple(line_ids.ids))
            self.env.cr.execute(sql)
            deposit_move_ids = [res[0] for res in self.env.cr.fetchall()]
            deposit_move_ids = self.env['account.move'].browse(deposit_move_ids)

            super(AccountMoveDeposit, move).button_draft()

            deposit_move_ids.button_draft()
            deposit_move_ids.with_context(force_delete=True).unlink()

        super(AccountMoveDeposit, self - non_entry_ids).button_draft()

    def js_assign_outstanding_line(self, credit_aml_id):
        """Override to reconcile invoice/bill and deposits"""
        self.ensure_one()
        credit_aml = self.env['account.move.line'].browse(credit_aml_id)
        if credit_aml.payment_id and credit_aml.payment_id.is_deposit:
            line_to_reconcile = self.line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
            register_payment_line = self._create_deposit_payment_entry(credit_aml, line_to_reconcile)
            if register_payment_line and line_to_reconcile:
                (register_payment_line + line_to_reconcile).reconcile()
        else:
            return super(AccountMoveDeposit, self).js_assign_outstanding_line(credit_aml_id)

    def js_remove_outstanding_partial(self, partial_id):
        """
        Override to remove deposit entry when removing deposit payment from invoice/bill
        """
        self.ensure_one()
        partial = self.env['account.partial.reconcile'].browse(partial_id)
        deposit_move_id = self.env['account.move'].browse()
        if partial.credit_move_id.move_id.is_deposit:
            deposit_move_id = partial.credit_move_id.move_id
        elif partial.debit_move_id.move_id.is_deposit:
            deposit_move_id = partial.debit_move_id.move_id

        res = super(AccountMoveDeposit, self).js_remove_outstanding_partial(partial_id)

        if deposit_move_id:
            deposit_move_id.button_draft()
            deposit_move_id.with_context(force_delete=True).unlink()

        return res

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    def _create_deposit_payment_entry(self, payment_line, invoice_line):
        """
        Create intermediate journal entry
        :return: payable/receivable move lines of new entry
        """
        total_invoice_amount = abs(sum(invoice_line.mapped('amount_residual')))
        amount = min(total_invoice_amount, abs(payment_line.amount_residual))

        if self.env.context.get('partial_amount', False):
            amount = self.env.context.get('partial_amount')

        if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
            return False

        company_id = payment_line.company_id
        if payment_line.debit > 0:
            journal_id = company_id.vendor_deposit_journal_id
        elif payment_line.credit > 0:
            journal_id = company_id.customer_deposit_journal_id
        else:
            journal_id = self.env['account.journal'].search([('type', '=', 'general')], limit=1)

        debit_account, credit_account = self._get_account_side(payment_line, invoice_line)
        reference = 'Deposit to Payment'
        payment_id = payment_line.payment_id
        date = self.invoice_date or fields.Date.today()

        new_account_move = self.env['account.move'].create({
            'journal_id': journal_id.id,
            'date': date,
            'ref': reference,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'is_deposit': True,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'partner_id': payment_line.partner_id.id,
                    'account_id': debit_account.id,
                    'debit': amount,
                    'credit': 0,
                    'date': date,
                    'name': reference,
                }),
                (0, 0, {
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'account_id': credit_account.id,
                    'debit': 0,
                    'credit': amount,
                    'date': date,
                    'name': reference,
                })
            ],
        })
        new_account_move.post()

        (payment_line + new_account_move.line_ids.filtered(lambda l: l.account_id == payment_line.account_id)).reconcile()
        payment_id.write({'deposit_ids': [(4, new_account_move.id)]})

        return new_account_move.line_ids.filtered(lambda l: l.account_id.internal_type in ('payable', 'receivable'))

    def _get_account_side(self, payment_line, invoice_line):
        debit_account = payment_line.credit > 0 and payment_line.account_id or invoice_line.account_id
        credit_account = payment_line.debit > 0 and payment_line.account_id or invoice_line.account_id

        return debit_account, credit_account

    def _reconcile_deposit(self, deposits, invoice):
        """
        Helper method: reconcile deposit automatically when confirming Invoice/Bill
        """
        for deposit in deposits.filtered(lambda r: r.state == 'posted'):
            move_type = invoice.move_type
            move_lines = deposit.line_ids.filtered(lambda line: line.account_id.reconcile and line.account_id.internal_type != 'liquidity' and not line.reconciled)
            if move_type == 'out_invoice':
                move_line = move_lines.filtered(lambda line: line.credit > 0)
            else:
                move_line = move_lines.filtered(lambda line: line.debit > 0)
            if move_line:
                invoice.js_assign_outstanding_line(move_line.id)

    def _get_reconciled_info_JSON_values(self):
        """
        Override
        Add label of applied transactions to dict values to show in payment widget on invoice form
        """
        reconciled_vals = super(AccountMoveDeposit, self)._get_reconciled_info_JSON_values()

        for val in reconciled_vals:
            move_id = self.browse(val.get('move_id'))
            if move_id.is_deposit:
                val['trans_label'] = 'Deposit'

        return reconciled_vals
