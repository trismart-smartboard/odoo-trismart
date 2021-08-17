from odoo import fields, models, api
from odoo.tools import float_compare


class AccountPaymentToDraftPopup(models.TransientModel):
    _name = 'button.draft.message'
    _description = 'Confirmed message when setting Payment/JE to draft'

    payment_id = fields.Many2one('account.payment', string='Payment')
    move_id = fields.Many2one('account.move', string='Journal Entry')
    message = fields.Html('Confirmed message', sanitize_attributes=False)

    @api.model
    def default_get(self, fields):
        res = super(AccountPaymentToDraftPopup, self).default_get(fields)
        context = self.env.context
        if context.get('default_payment_id', False):
            payment_id = self.env['account.payment'].browse(context['default_payment_id'])
            res['message'] = self._get_confirmed_message_payment(payment_id)
        elif context.get('default_move_id', False):
            move_id = self.env['account.move'].browse(context['default_move_id'])
            res['message'] = self._get_confirmed_message_move(move_id)

        return res

    def _get_confirmed_message_payment(self, payment):
        """
        Get confirmed message when clicking 'Reset to draft' on payment form.
        :param payment: record of model account.payment
        :return: message
        """
        message = False
        if payment and payment.state != 'draft':
            # Check if this payment has been applied for any invoice/bill or reconciled yet
            if float_compare(payment.applied_amount, 0, precision_rounding=payment.currency_id.rounding) > 0:
                message = "This payment has been applied{}. Resetting it to draft will remove it from all related transactions"
                
            line_ids = payment.move_id.line_ids.filtered(
                lambda line: line.account_id.id in [line.journal_id.payment_debit_account_id.id,
                                                    line.journal_id.payment_credit_account_id.id])
            if line_ids.filtered('bank_reconciled'):
                if message:
                    message = message.format(" and reconciled") + " and affect your reconciliation data."
                else:
                    message = "This payment has been reconciled. Resetting it to draft will affect your reconciliation data."
            elif payment.is_matched:
                if message:
                    message = message.format(" and matched with a bank statement line") + "."
                else:
                    message = "This payment has been matched with a bank statement line. Resetting it to draft will affect your reconciliation data."
            elif message:
                message = message.format("") + "."

            if not message:
                message = "Are you sure you want to set this payment to draft?"
        return message

    def _get_confirmed_message_move(self, move):
        """
        Get confirmed message when clicking 'Reset to draft' on move (Invoice/Bill/.../JE) form.
        :param move: record of model account.move
        :return: message
        """
        message = False
        if move and move.state != 'draft':
            line_ids = move.line_ids.filtered(lambda line: line.account_id.id in [line.journal_id.payment_debit_account_id.id,
                                                                            line.journal_id.payment_credit_account_id.id])
            if move.has_reconciled_entries:
                message = "This transaction has been applied{}. Resetting it to draft will remove it from all related transactions"

            if move.move_type == 'entry':
                if line_ids.filtered('bank_reconciled'):
                    if message:
                        message = message.format(" and reconciled") + " and affect your reconciliation data."
                    else:
                        message = "This transaction has been reconciled. Resetting it to draft will affect your reconciliation data."
                elif line_ids.filtered('reconciled'):
                    if message:
                        message = message.format(" and reviewed for bank reconciliation") + "."
                    else:
                        message = "This transaction has been reviewed for bank reconciliation. Resetting it to draft will affect your reconciliation data."
                elif message:
                    message = message.format("") + "."
            elif message:
                message = message.format("") + "."

            if not message:
                message = "Are you sure you want to set this transaction to draft?"
        return message

    def button_set_to_draft(self):
        def reset_reconcile_state(line_ids):
            line_ids.write({
                'temporary_reconciled': False,
                'bank_reconciled': False
            })

        self.ensure_one()

        if self.payment_id:
            self.payment_id.action_draft()
            journal_id = self.payment_id.journal_id
            outstanding_account_ids = [journal_id.payment_debit_account_id.id,
                                       journal_id.payment_credit_account_id.id]
            reset_reconcile_state(self.payment_id.line_ids.filtered(lambda l: l.account_id.id in outstanding_account_ids))
        elif self.move_id:
            self.move_id.button_draft()
            journal_id = self.move_id.journal_id
            if journal_id.type in ['bank', 'cash']:
                outstanding_account_ids = [journal_id.payment_debit_account_id.id,
                                           journal_id.payment_credit_account_id.id]
                reset_reconcile_state(self.move_id.line_ids.filtered(lambda l: l.account_id.id in outstanding_account_ids))
            else:
                # Miscellaneous entries contain Bank/Cash line
                reset_reconcile_state(self.move_id.line_ids.filtered(lambda l: l.account_id.user_type_id.id == self.env.ref('account.data_account_type_liquidity').id))
