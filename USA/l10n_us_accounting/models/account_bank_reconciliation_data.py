# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields
from odoo.tools import float_compare
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.misc import formatLang
from datetime import datetime
from odoo.exceptions import Warning, ValidationError


class BankReconciliationData(models.Model):
    _name = 'account.bank.reconciliation.data'
    _description = 'Bank Reconciliation Data'
    _rec_name = 'statement_ending_date'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    journal_id = fields.Many2one('account.journal', string='Bank Account')
    company_id = fields.Many2one('res.company', related='journal_id.company_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('reconciled', 'Reconciled'),
    ], default='draft', string='State', required=True, copy=False)

    statement_beginning_date = fields.Date('Statement Beginning Date')
    statement_ending_date = fields.Date('Statement Ending Date')
    start_date = fields.Date('Start Date', related='journal_id.show_transactions_from', readonly=False)
    reconcile_on = fields.Date('Reconcile On')
    beginning_balance = fields.Monetary('Beginning Balance')
    ending_balance = fields.Monetary('Ending Balance')

    previous_reconciliation_id = fields.Many2one('account.bank.reconciliation.data')

    # Data for report
    data_line_ids = fields.One2many('account.bank.reconciliation.data.line', 'bank_reconciliation_data_id')
    change_transaction_ids = fields.One2many('account.bank.reconciliation.data.line', 'bank_reconciliation_data_id',
                                             domain=[('is_cleared', '=', True), ('change_status', '!=', 'normal')])
    payments_cleared_ids = fields.One2many('account.bank.reconciliation.data.line', 'bank_reconciliation_data_id',
                                           domain=[('transaction_type', '=', 'payment'), ('is_cleared', '=', True)])
    deposits_cleared_ids = fields.One2many('account.bank.reconciliation.data.line', 'bank_reconciliation_data_id',
                                           domain=[('transaction_type', '=', 'deposit'), ('is_cleared', '=', True)])
    payments_uncleared_ids = fields.One2many('account.bank.reconciliation.data.line', 'bank_reconciliation_data_id',
                                             domain=[('transaction_type', '=', 'payment'), ('is_cleared', '=', False)])
    deposits_uncleared_ids = fields.One2many('account.bank.reconciliation.data.line', 'bank_reconciliation_data_id',
                                             domain=[('transaction_type', '=', 'deposit'), ('is_cleared', '=', False)])
    aml_ids = fields.Many2many('account.move.line', string='Transactions in this Session')

    discrepancy_entry_id = fields.Many2one('account.move', string='Discrepancy Entry')
    difference = fields.Monetary('Adjustment')
    payments_cleared = fields.Monetary('Payments Cleared')
    deposits_cleared = fields.Monetary('Deposits Cleared')
    payments_uncleared = fields.Monetary('Uncleared Payments')  # Negative amount
    deposits_uncleared = fields.Monetary('Uncleared Deposits')
    register_balance = fields.Monetary('Register Balance')
    change_amount = fields.Monetary('Changes', compute='_compute_change_amount')
    payment_count = fields.Integer(string='# of Cleared Payments', compute='_compute_payment_count', store=True)
    deposit_count = fields.Integer(string='# of Cleared Deposits', compute='_compute_deposit_count', store=True)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)

        if defaults.get('journal_id', False):
            journal_id = defaults['journal_id']

            draft_reconciliation = self.search([('journal_id', '=', journal_id), ('state', '=', 'draft')])
            if draft_reconciliation:
                return defaults

            previous_reconciliation = self.search([('journal_id', '=', journal_id), ('state', '=', 'reconciled')],
                                                  order='id desc', limit=1)
            if previous_reconciliation:
                defaults['previous_reconciliation_id'] = previous_reconciliation.id
                defaults['beginning_balance'] = previous_reconciliation.ending_balance
                defaults['statement_beginning_date'] = previous_reconciliation.statement_ending_date

        return defaults

    def get_popup_form_id(self):
        """
        Use by Edit Info button in reconciliation screen
        """
        return self.env.ref('l10n_us_accounting.bank_reconciliation_data_popup_form').id

    def _get_reconciliation_screen(self, data_id):
        """
        Helper function to return action given bank_data_id
        """
        action_obj = self.env.ref('l10n_us_accounting.action_usa_bank_reconciliation')
        action_obj['params'] = {'bank_reconciliation_data_id': data_id}
        action = action_obj.read()[0]
        action['context'] = {'model': 'usa.bank.reconciliation',
                             'bank_reconciliation_data_id': data_id}
        return action

    def _get_transactions(self, old_date=None, new_date=None):
        """
        Get transactions (aml) to show in Reconciliation Screen.
        Used when open the reconciliation screen & reset transaction (edit info)

        CONDITIONS:
        + (outstanding accounts & payment_id & reconciled): reviewed payments, already include batch payments,
        but exclude payment line from BSL
        + OR (outstanding accounts & batch_fund_line_id & reconciled): reviewed adjustment lines, exclude line from BSL
        + OR (statement_line_id and NOT bank accounts): for lines with writeoff/AR/AP account -> REVERSE DR/CR SIDE
        + OR (bank account & not statement_line_id): for manual journal entry that goes directly to Bank  TODO: check journal?
        """
        statement_ending_date = new_date if new_date else self.statement_ending_date
        journal_id = self.journal_id

        bank_account_id = journal_id.default_account_id.id
        exclude_account_ids = [bank_account_id,
                               journal_id.suspense_account_id.id,
                               journal_id.payment_debit_account_id.id,
                               journal_id.payment_credit_account_id.id]
        outstanding_account_ids = [journal_id.payment_debit_account_id.id,
                                   journal_id.payment_credit_account_id.id]

        sql = """
            SELECT aml.id
            FROM account_move_line AS aml
                JOIN account_move AS am ON aml.move_id = am.id
            WHERE aml.date <= %s {date_condition}
                AND aml.bank_reconciled = FALSE
                AND am.state = 'posted'
                AND (
                    (
                        aml.journal_id = %s 
                        AND (
                            (aml.account_id IN %s AND aml.payment_id IS NOT NULL AND aml.reconciled = TRUE) 
                            OR (aml.account_id IN %s AND aml.batch_fund_line_id IS NOT NULL AND aml.reconciled = TRUE)
                            OR (aml.account_id NOT IN %s AND aml.statement_line_id IS NOT NULL)
                        )
                    ) 
                    OR (aml.account_id = %s AND aml.statement_line_id IS NULL)
                )
        """

        date_condition = ""
        if old_date:
            if self.start_date and old_date < self.start_date:
                date_condition = "AND aml.date >= '{}'".format(fields.Date.to_string(self.start_date))
            else:
                date_condition = "AND aml.date > '{}'".format(fields.Date.to_string(old_date))

        sql = sql.format(date_condition=date_condition)

        self.env.cr.execute(sql, [statement_ending_date, journal_id.id, tuple(outstanding_account_ids),
                                  tuple(outstanding_account_ids), tuple(exclude_account_ids), bank_account_id])

        aml_ids = [res[0] for res in self.env.cr.fetchall()]
        return self.env['account.move.line'].browse(aml_ids)

    def _reset_transactions(self, old_date=None, new_date=None):
        """ Reset transactions
        Transactions that are not really reconciled but temporarily.
        Used when reconcile, close without saving & change ending date (edit info)
        Only reset transactions within a time frame (change ending date)
        """
        journal_id = self.journal_id
        outstanding_account_ids = [journal_id.payment_debit_account_id.id,
                                   journal_id.payment_credit_account_id.id]

        if old_date:  # Edit Info
            # This function runs BEFORE get_lines of usa_bank_reconcilation
            # so we have to search for the transactions again
            need_action_amls = self._get_transactions(old_date, new_date)
        else:  # Close Without Saving
            # We already write to aml_ids every time we open a reconciliation screen, no need to search again
            need_action_amls = self.aml_ids

        temporary_true = self.env['account.move.line']
        temporary_false = self.env['account.move.line']
        for line in need_action_amls:
            # Reset outstanding lines
            # if reconciled -> temporary_reconciled: True, and vice versa
            if line.account_id.id in outstanding_account_ids:
                if line.reconciled:
                    temporary_true += line
                else:
                    temporary_false += line
            # Reset write-off lines
            # If BSL's status is confirm -> True, otherwise -> False
            elif line.statement_line_id:
                if line.statement_line_id.status in ['confirm', 'reconciled']:
                    temporary_true += line
                else:
                    temporary_false += line
            else:
                temporary_false += line  # Manual JE contains line bank

        temporary_true.write({'temporary_reconciled': True})
        temporary_false.write({'temporary_reconciled': False})

    def _undo(self):
        """
        Undo last reconciliation
        """
        self.ensure_one()

        # Reset some fields
        prev_id = self.previous_reconciliation_id
        prev_id.with_context(undo_reconciliation=True).write({
            'state': 'draft',
            'ending_balance': self.ending_balance,
            'statement_ending_date': self.statement_ending_date,
            'data_line_ids': [(5,)]
        })

        # Un-mark reconciled, don't change temporary_reconciled so they can still be marked in reconciliation screen
        unreconciled_lines = prev_id.aml_ids.filtered(lambda x: not x.bank_reconciled)
        reconciled_lines = prev_id.aml_ids - unreconciled_lines
        unreconciled_lines.write({'temporary_reconciled': False})
        reconciled_lines.write({'temporary_reconciled': True})
        reconciled_lines.undo_bank_reconciled()

        # Reverse discrepancy entry, if any
        if prev_id.discrepancy_entry_id:
            reverse_move_id = prev_id.discrepancy_entry_id._reverse_moves(cancel=True).ids
            reverse_move = self.env['account.move'].browse(reverse_move_id)
            reverse_move.line_ids.mark_bank_reconciled()

    def _create_report_line(self):
        def get_amount(line):
            if line.credit:
                return {
                    'amount': line.credit,
                    'amount_signed': line.credit,
                    'transaction_type': line.statement_line_id and 'deposit' or 'payment'
                }
            else:
                return {
                    'amount': line.debit,
                    'amount_signed': (-1 * line.debit),
                    'transaction_type': line.statement_line_id and 'payment' or 'deposit'
                }

        self.ensure_one()

        vals_list = []
        for line in self.aml_ids:
            vals = {
                'aml_id': line.id,
                'name': line.move_id.name,
                'date': line.date,
                'memo': line.name,
                'check_number': line.payment_id.check_number if line.payment_id and line.payment_id.check_number else '',
                'payee_id': line.partner_id.id if line.partner_id else False,
                'is_cleared': line.temporary_reconciled,
                'bank_reconciliation_data_id': self.id,
                'batch_payment_id': line.payment_id.batch_payment_id.id or line.batch_fund_line_id.batch_deposit_id.id or False
            }
            vals.update(get_amount(line))
            vals_list.append(vals)
        self.env['account.bank.reconciliation.data.line'].sudo().create(vals_list)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('payments_cleared_ids')
    def _compute_payment_count(self):
        for record in self:
            record.payment_count = len(record.payments_cleared_ids)

    @api.depends('deposits_cleared_ids')
    def _compute_deposit_count(self):
        for record in self:
            record.deposit_count = len(record.deposits_cleared_ids)

    def _compute_change_amount(self):
        for record in self:
            record.change_amount = sum(line.amount_change for line in record.change_transaction_ids)

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    def write(self, vals):
        # This is for Ending Date is updated from Reconciliation Screen's Edit Info
        # if it's from Undo, we want to keep the same state of transactions
        if vals.get('statement_ending_date', False) and not self.env.context.get('undo_reconciliation', False):
            new_date = datetime.strptime(vals.get('statement_ending_date'), DEFAULT_SERVER_DATE_FORMAT).date()
            for record in self:
                old_date = record.statement_ending_date

                if new_date > old_date:
                    record._reset_transactions(old_date, new_date)

        return super().write(vals)

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def action_print_report(self):
        return self.env.ref('l10n_us_accounting.account_bank_reconciliation_data_report').report_action(self)

    def open_reconcile_screen(self):
        """
        Return Reconciliation action. Used in Reconcile button in Dashboard, and Edit Info in Reconciliation screen.
        """
        if self.start_date and self.start_date > self.statement_ending_date:
            raise ValidationError(_('Show transactions from must be less than or equal to Statement Ending Date'))

        if self.env.context.get('edit_info', False):
            return True

        action = self._get_reconciliation_screen(self.id)
        return action

    def undo_last_reconciliation(self):
        if not self.previous_reconciliation_id:
            raise Warning(_('There are no previous reconciliations to undo.'))

        self._undo()

        # Return screen of previous reconciliation
        action = self._get_reconciliation_screen(self.previous_reconciliation_id.id)

        # Delete the newly created record
        self.unlink()
        return action

    def close_without_saving(self):
        self.ensure_one()
        self._reset_transactions()
        self.unlink()
        return self.env.ref('account.open_account_journal_dashboard_kanban').read()[0]

    def check_difference_amount(self, aml_ids, difference, cleared_payments, cleared_deposits):
        self.ensure_one()
        self.write({
            'difference': difference,
            'payments_cleared': cleared_payments,
            'deposits_cleared': cleared_deposits,
            'reconcile_on': datetime.today(),
        })

        if float_compare(difference, 0.0, precision_digits=2) != 0:  # difference != 0
            formatted_value = formatLang(self.env, 0.0, currency_obj=self.env.company.currency_id)
            return {
                'name': "Your difference isn't {} yet".format(formatted_value),
                'type': 'ir.actions.act_window',
                'res_model': 'account.bank.reconciliation.difference',
                'view_type': 'form',
                'view_mode': 'form',
                'views': [[False, 'form']],
                'context': {'default_bank_reconciliation_data_id': self.id},
                'target': 'new',
            }
        return self.do_reconcile()

    def do_reconcile(self):
        self.ensure_one()

        reconciled_items = self.aml_ids.filtered(lambda x: x.temporary_reconciled)
        reconciled_items.mark_bank_reconciled()

        # Create report
        self._create_report_line()
        payments_uncleared = - sum(record.amount for record in self.payments_uncleared_ids)
        deposits_uncleared = sum(record.amount for record in self.deposits_uncleared_ids)
        register_balance = self.ending_balance + payments_uncleared + deposits_uncleared
        self.write({
            'payments_uncleared': payments_uncleared,
            'deposits_uncleared': deposits_uncleared,
            'register_balance': register_balance,
            'state': 'reconciled'
        })

        if self.journal_id.is_credit_card and self.ending_balance < 0:
            action = self.env.ref('l10n_us_accounting.action_record_ending_balance').read()[0]
            action['hide_close_btn'] = True
            action['context'] = {
                'default_ending_balance': self.ending_balance,
                'default_bank_reconciliation_data_id': self.id,
                'default_vendor_id': self.journal_id.partner_id and self.journal_id.partner_id.id or False
            }
            return action

        # Reset temporary_reconciled for next reconciliation
        self._reset_transactions()

        # Redirect to report form, main to clear breadcrumb
        action = self.env.ref('l10n_us_accounting.action_bank_reconciliation_data_report_form').read()[0]
        action['res_id'] = self.id
        return action


class BankReconciliationDataLine(models.Model):
    _name = 'account.bank.reconciliation.data.line'
    _description = 'Bank Reconciliation Data Line'

    name = fields.Char('Number')
    date = fields.Date('Date')
    check_number = fields.Char('Checks No')
    memo = fields.Char('Memo')
    payee_id = fields.Many2one('res.partner', 'Payee')
    amount = fields.Monetary('Amount')
    amount_signed = fields.Monetary('Amount Signed')

    bank_reconciliation_data_id = fields.Many2one('account.bank.reconciliation.data', ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='bank_reconciliation_data_id.currency_id')

    transaction_type = fields.Selection([('payment', 'Payment'), ('deposit', 'Deposit')])
    is_cleared = fields.Boolean('Has Been Cleared?')  # Reconciled
    aml_id = fields.Many2one('account.move.line')
    batch_payment_id = fields.Many2one('account.batch.payment')
    # Change Section
    has_been_canceled = fields.Boolean()
    amount_change = fields.Monetary('Amount Change', compute='compute_change_status', store=True)
    current_amount = fields.Monetary('Current Amount', compute='compute_change_status', store=True)
    change_status = fields.Selection([('normal', 'Normal'), ('canceled', 'Canceled'), ('deleted', 'Deleted')],
                                     default='canceled', compute='compute_change_status', store=True)

    @api.depends('aml_id', 'aml_id.move_id.state')
    def compute_change_status(self):
        for record in self:
            current_amount = amount_change = False
            if not record.aml_id:
                change_status = 'deleted'
                current_amount = 0
                amount_change = record.amount_signed
            elif record.aml_id and record.aml_id.move_id.state == 'draft' or record.has_been_canceled:
                change_status = 'canceled'
                current_amount = 0
                amount_change = record.amount_signed
                record.has_been_canceled = True
            else:
                change_status = 'normal'

            record.change_status = change_status
            record.current_amount = current_amount
            record.amount_change = amount_change
