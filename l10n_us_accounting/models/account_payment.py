# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_is_zero, float_compare


class AccountPaymentUSA(models.Model):
    _inherit = 'account.payment'

    # == Business fields ==
    ar_in_charge = fields.Many2one(string='AR In Charge', comodel_name='res.users', domain=[('share', '=', False)])
    is_payment_receipt = fields.Boolean(string='Is Payment Receipt?', default=False)
    expense_account = fields.Many2one('account.account', string='Expense Account',
                                      domain=lambda self: [('user_type_id', 'in', [self.env.ref('account.data_account_type_expenses').id,
                                                                                   self.env.ref('account.data_account_type_direct_costs').id])])
    income_account = fields.Many2one('account.account', string='Income Account',
                                     domain=lambda self: [('user_type_id', 'in', [self.env.ref('account.data_account_type_revenue').id,
                                                                                  self.env.ref('account.data_account_type_other_income').id])])

    # Reconcile with invoices/entries
    available_move_line_ids = fields.Many2many('account.move.line', compute='_compute_available_move_line',
                                               string='Available Move Lines')
    payment_line_ids = fields.One2many('account.payment.line', 'payment_id', string='Payment Lines')
    debit_partial_reconcile_ids = fields.One2many('account.partial.reconcile', 'debit_payment_id',
                                                  string='Debit reconciled transactions')
    credit_partial_reconcile_ids = fields.One2many('account.partial.reconcile', 'credit_payment_id',
                                                   string='Credit reconciled transactions')

    to_apply_amount = fields.Monetary('Amount to Apply', compute='_compute_to_apply_amount', store=True)
    applied_amount = fields.Monetary('Applied Amount', compute='_compute_applied_amount', store=True)
    outstanding_payment = fields.Monetary('Outstanding Amount', compute='_compute_entries_amount', store=True)
    writeoff_amount = fields.Monetary('Write-off Amount', compute='_compute_entries_amount', store=True)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    def _check_build_page_info(self, i, p):
        res = super()._check_build_page_info(i, p)

        if self.partner_id.print_check_as and self.partner_id.check_name:
            res['partner_name'] = self.partner_id.check_name

        return res

    def _get_invoice_balance_due_and_credit_amount(self, inv):
        """
        Used to print payment receipt PDF
        :param inv:
        :return: array contains balance due and credit amount of invoice/bill
        """
        other_payment_amount = credit_amount = 0
        for partial, amount, counterpart_line in inv._get_reconciled_invoices_partials():
            account_payment_id = counterpart_line.payment_id.id
            move_type = counterpart_line.move_id.move_type
            # Deposit reconciled info: move type is entry and there is no link to deposit payment
            if account_payment_id != self.id and \
                    (account_payment_id or (move_type == 'entry' and not account_payment_id)):
                other_payment_amount += amount
            elif move_type in ['out_refund', 'in_refund']:
                credit_amount += amount

        return {
            'balance_due': inv.amount_total - other_payment_amount,
            'credit': credit_amount
        }

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('partner_id', 'partner_id.unreconciled_aml_ids', 'partner_id.unreconciled_payable_aml_ids',
                 'payment_type', 'partner_type', 'state', 'currency_id', 'payment_line_ids')
    def _compute_available_move_line(self):
        """
        Get available open transactions so users can select in account.payment.line model.
        But only in draft state, when it's posted, we don't care.

        Note: we don't store this field cause we don't want to re-compute it for all the payments whenever
        unreconciled_aml_ids change.
        """
        for record in self:
            if record.state != 'draft':
                record.available_move_line_ids = False
            else:
                partner_id = record.partner_id
                if not partner_id:
                    record.available_move_line_ids = False
                else:
                    side_field = 'debit' if record.payment_type == 'inbound' else 'credit'
                    unreconcile_ids = partner_id.unreconciled_aml_ids if record.partner_type == 'customer' \
                        else partner_id.unreconciled_payable_aml_ids

                    added_ids = record.payment_line_ids.mapped('account_move_line_id')  # aml already added
                    available_ids = (unreconcile_ids - added_ids)  # aml that users can select

                    available_move_line_ids = available_ids.filtered(lambda x: x.currency_id == record.currency_id
                                                                               and x[side_field] > 0)

                    record.available_move_line_ids = available_move_line_ids

    @api.depends('payment_line_ids', 'payment_line_ids.payment')
    def _compute_to_apply_amount(self):
        """
        Compute "To Apply amount" in Draft state. Based in our new model.
        :return:
        """
        for record in self:
            record.to_apply_amount = sum(record.payment_line_ids.mapped('payment'))

    @api.depends('debit_partial_reconcile_ids', 'debit_partial_reconcile_ids.amount',
                 'credit_partial_reconcile_ids', 'credit_partial_reconcile_ids.amount')
    def _compute_applied_amount(self):
        """
        Compute "Applied amount" in Posted state. Based in account.partial.reconcile.
        :return:
        """
        for record in self:
            if record.payment_type == 'inbound':
                amt_side_field = 'credit_amount_currency'
                reconcile_field = 'credit_partial_reconcile_ids'
            else:
                amt_side_field = 'debit_amount_currency'
                reconcile_field = 'debit_partial_reconcile_ids'

            applied_amount = sum(record[reconcile_field].mapped(amt_side_field))

            record.applied_amount = applied_amount

    @api.depends('move_id', 'move_id.line_ids', 'move_id.line_ids.amount_residual_currency',
                 'move_id.line_ids.amount_currency')
    def _compute_entries_amount(self):
        for record in self:
            _, counterpart_lines, writeoff_lines = record._seek_for_lines()
            record.outstanding_payment = abs(sum((counterpart_lines.mapped('amount_residual_currency')))) if counterpart_lines else 0
            record.writeoff_amount = abs(sum((writeoff_lines.mapped('amount_currency')))) if writeoff_lines else 0

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('partner_id')
    def _onchange_select_customer(self):
        self.ar_in_charge = self.partner_id.ar_in_charge

    @api.onchange('partner_id', 'payment_type', 'partner_type', 'currency_id')
    def _onchange_update_payment_line(self):
        self.payment_line_ids = False

    @api.onchange('payment_type', 'partner_type')
    def _onchange_payment_and_partner_type(self):
        if (self.payment_type == 'outbound' and self.partner_type == 'customer') \
                or (self.payment_type == 'inbound' and self.partner_type == 'supplier'):
            self.is_payment_receipt = False
            self.expense_account = False
            self.income_account = False

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    @api.model
    def create(self, values):
        """
        Override to add deposit/check move line like a write-off move line
        """
        if values.get('is_payment_receipt', False):
            account_id = values.get('expense_account') or values.get('income_account')
            values['write_off_line_vals'] = {
                'account_id': account_id,
                'amount': -values.get('amount', 0.0)
            }

        return super(AccountPaymentUSA, self).create(values)

    def _synchronize_to_moves(self, changed_fields):
        """
        Override to update move lines of payment receipt when changing fields on the payment form
        """
        if self._context.get('skip_account_move_synchronization'):
            return

        payment_receipts = self.with_context(skip_account_move_synchronization=True).filtered(lambda x: x.is_payment_receipt)
        if 'is_payment_receipt' in changed_fields and not payment_receipts:
            # When change from payment receipt to normal payment, we need to remove write-off move line
            for payment in self.with_context(skip_account_move_synchronization=True):
                liquidity_lines, counterpart_lines, other_lines = payment._seek_for_lines()
                line_vals_list = payment._prepare_move_line_default_vals(write_off_line_vals={})
                line_ids_commands = [
                    (1, liquidity_lines.id, line_vals_list[0]),
                    (1, counterpart_lines.id, line_vals_list[1]),
                    (2, other_lines[0].id, 0),
                ]
                payment.move_id.write({
                    'line_ids': line_ids_commands
                })
            super(AccountPaymentUSA, self)._synchronize_to_moves(changed_fields)
        elif any(field in changed_fields for field in ['partner_id', 'partner_bank_id', 'date', 'payment_reference', 'amount', 'currency_id', 'expense_account', 'income_account', 'is_payment_receipt']):
            for payment in payment_receipts:
                liquidity_lines, counterpart_lines, other_lines = payment._seek_for_lines()
                # When change from normal payment to payment receipt, we need to create write-off move line
                if other_lines:
                    other_line_vals = {
                        'name': other_lines[0].name,
                        'amount': -payment.amount,
                        'account_id': payment.is_payment_receipt and (payment.expense_account.id or payment.income_account.id) or other_lines[0].account_id.id
                    }
                else:
                    other_line_vals = {
                        'amount': -payment.amount,
                        'account_id': payment.expense_account.id or payment.income_account.id
                    }
                line_vals_list = payment._prepare_move_line_default_vals(write_off_line_vals=other_line_vals)
                if other_lines:
                    # Just update write-off move line
                    line_ids_commands = [
                        (1, liquidity_lines.id, line_vals_list[0]),
                        (1, counterpart_lines.id, line_vals_list[1]),
                        (1, other_lines[0].id, line_vals_list[2]),
                    ]
                else:
                    # Need to set debit and credit of counter part move line to 0
                    # Create write-off move line
                    line_vals_list[1].update(debit=0, credit=0)
                    line_ids_commands = [
                        (1, liquidity_lines.id, line_vals_list[0]),
                        (1, counterpart_lines.id, line_vals_list[1]),
                        (0, 0, line_vals_list[2]),
                    ]
                payment.move_id.write({
                    'partner_id': payment.partner_id.id,
                    'currency_id': payment.currency_id.id,
                    'partner_bank_id': payment.partner_bank_id.id,
                    'line_ids': line_ids_commands
                })
            super(AccountPaymentUSA, self - payment_receipts)._synchronize_to_moves(changed_fields)
        else:
            super(AccountPaymentUSA, self)._synchronize_to_moves(changed_fields)

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def action_post(self):
        res = super().action_post()

        for payment in self:
            # Amount Validation
            if float_compare(payment.amount, payment.to_apply_amount,
                             precision_rounding=payment.currency_id.rounding) < 0:
                raise ValidationError('Payment amount cannot be smaller than Amount to apply')

            # Reconcile open transactions
            _, counterpart_lines, _ = payment._seek_for_lines()
            for open_tran in payment.payment_line_ids:
                tran_aml = open_tran.account_move_line_id
                if tran_aml.reconciled:
                    continue

                # Most of the times there will be only one counterpart line.
                for counterpart in counterpart_lines:
                    if counterpart.reconciled:
                        continue

                    tran_aml.move_id.with_context(partial_amount=open_tran.payment).js_assign_outstanding_line(counterpart.id)

        self.payment_line_ids = False  # We don't need it in posted state
        return res

    def button_draft_usa(self):
        self.ensure_one()
        action = self.env.ref('l10n_us_accounting.action_view_button_set_to_draft_message').read()[0]
        action['context'] = isinstance(action.get('context', {}), dict) or {}
        action['context']['default_payment_id'] = self.id
        return action

