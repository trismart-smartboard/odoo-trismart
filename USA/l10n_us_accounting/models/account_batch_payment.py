# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    fund_line_ids = fields.One2many('account.batch.deposit.fund.line', 'batch_deposit_id', string='Adjustment Lines')

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def get_batch_payment_aml(self):
        """
        Get all account.move.line in batch payments, include payments and adjustments.
        """
        aml_ids = self.env['account.move.line']
        for record in self:
            journal_accounts = [record.journal_id.payment_debit_account_id.id,
                                record.journal_id.payment_credit_account_id.id]
            for payment in record.payment_ids.filtered(lambda p: p.state == 'posted'):
                aml_ids |= payment.line_ids.filtered(lambda r: r.account_id.id in journal_accounts and not r.reconciled and not r.bank_reconciled)
            for line in record.fund_line_ids:
                line_id = line.get_aml_adjustments(journal_accounts)
                aml_ids |= line_id

        return aml_ids

    def _get_batch_info_for_review(self):
        """
        Used to get info of this batch payment (except which has been reviewed (temporary_reconciled = True)).
        :return: dictionary of type, amount, amount_journal_currency, amount_payment_currency, journal_id
        """
        def get_amount(rec_amount, currency):
            if currency == journal_currency:
                return rec_amount
            return currency._convert(rec_amount, journal_currency, self.journal_id.company_id, self.date or fields.Date.today())

        self.ensure_one()
        # Copy from account_batch_payment/account_batch_payment.
        company_currency = self.journal_id.company_id.currency_id or self.env.company.currency_id
        journal_currency = self.journal_id.currency_id or company_currency
        filter_amount = self.batch_type == 'outbound' and -self.amount or self.amount

        for payment in self.payment_ids.filtered(lambda p: p.is_matched or p.state == 'draft'):
            payment_currency = payment.currency_id or company_currency
            filter_amount -= get_amount(payment.amount, payment_currency)

        for line in self.fund_line_ids.filtered(lambda f: f.has_been_reviewed or f.account_move_id.state == 'draft'):
            line_currency = line.currency_id or company_currency
            filter_amount -= get_amount(line.line_amount, line_currency)

        return {
            'type': self.batch_type,  # To filter in review screen.
            'filter_amount': filter_amount,
            'journal_id': self.journal_id.id
        }

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('date', 'currency_id', 'payment_ids.amount', 'fund_line_ids.line_amount')
    def _compute_amount(self):
        """
        Call super to calculate the total of all payment lines.
        Then add the total of fund lines.
        """
        super()._compute_amount()

        for batch in self:
            currency = batch.currency_id or batch.journal_id.currency_id or self.env.company.currency_id
            date = batch.date or fields.Date.context_today(self)
            amount = 0
            for fund_line in batch.fund_line_ids:
                liquidity_lines, counterpart_lines, writeoff_lines = fund_line._seek_for_lines()
                for line in liquidity_lines:
                    if line.currency_id == currency:
                        amount += line.amount_currency
                    else:
                        amount += line.company_currency_id._convert(line.balance, currency, line.company_id, date)

            batch.amount += amount

    @api.depends('payment_ids.move_id.is_move_sent', 'payment_ids.is_matched', 'payment_ids.line_ids.bank_reconciled',
                 'fund_line_ids.move_state', 'fund_line_ids.account_move_id.line_ids.bank_reconciled')
    def _compute_state(self):
        super()._compute_state()

        for batch in self:
            outstanding_account_ids = [batch.journal_id.payment_debit_account_id.id,
                                       batch.journal_id.payment_credit_account_id.id]

            move_lines = batch.payment_ids.mapped('line_ids') + batch.fund_line_ids.mapped('account_move_id.line_ids')
            unreconciled_move_lines = move_lines.filtered(lambda l: l.account_id.id in outstanding_account_ids and not l.bank_reconciled)
            if not move_lines:
                batch.state = 'draft'
            elif not unreconciled_move_lines:
                batch.state = 'reconciled'
            elif False not in batch.payment_ids.mapped('is_move_sent') \
                    and (not batch.fund_line_ids
                         or (batch.fund_line_ids and all(line.move_state == 'posted' for line in batch.fund_line_ids))):
                batch.state = 'sent'
            else:
                batch.state = 'draft'

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def validate_adjust_moves(self):
        # Validate all Journal Entries of adjustment lines.
        self.ensure_one()
        self.fund_line_ids.account_move_id._post(soft=False)

    def validate_batch_button(self):
        res = super().validate_batch_button()
        self.validate_adjust_moves()
        return res

    def action_open_journal_entries(self):
        # Open all Journal Entries from adjustment lines of this batch payment.
        self.ensure_one()
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.fund_line_ids.mapped('account_move_id').ids)],
        }


class AccountBatchPaymentLine(models.Model):
    _name = 'account.batch.deposit.fund.line'
    _inherits = {'account.move': 'account_move_id'}
    _check_company_auto = True
    _description = 'Batch Payment Fund Line'

    ####################################################################################################################
    # Refactor for v14: generate draft entry and sync with adjustment line, by inherits 'account.move'
    # Based on code of account.bank.statement.line
    ####################################################################################################################
    # == Business fields ==
    account_move_id = fields.Many2one('account.move', string='Journal Entry', ondelete='cascade', check_company=True, required=True)
    batch_deposit_id = fields.Many2one('account.batch.payment', ondelete='cascade')
    batch_type = fields.Selection(related='batch_deposit_id.batch_type', string='Batch Payment Type')
    move_state = fields.Selection(related='account_move_id.state', string='Journal Entry State')

    # == Synchronized fields with the account.move.lines ==
    line_partner_id = fields.Many2one('res.partner', 'Customer/Vendor')
    line_account_id = fields.Many2one('account.account', 'Account')
    line_communication = fields.Char('Description')
    line_payment_date = fields.Date('Date')
    line_currency_id = fields.Many2one('res.currency', string='Currency',
                                  related='batch_deposit_id.currency_id', store=True)
    line_amount = fields.Monetary('Amount', currency_field='line_currency_id')

    # == Technical fields ==
    has_been_reviewed = fields.Boolean(string='Have been reviewed?', compute='_compute_bank_reconciled', store=True, copy=False)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_liquid_account_id(self, journal_id, batch_type):
        if batch_type == 'inbound':
            return journal_id.payment_debit_account_id
        else:
            return journal_id.payment_credit_account_id

    @api.model
    def _prepare_liquidity_move_line_vals(self):
        self.ensure_one()
        ref = self.line_communication or self.batch_deposit_id.display_name + ' Adjustment'
        amount = self.line_amount
        to_debit = bool(
            self.batch_type == 'inbound' and amount >= 0 or self.batch_type == 'outbound' and amount <= 0)
        liquid_account_id = self._get_liquid_account_id(self.journal_id, self.batch_type)

        return {
            'name': ref,
            'move_id': self.account_move_id.id,
            'partner_id': self.line_partner_id.id,
            'date': self.line_payment_date,
            'currency_id': self.line_currency_id.id,
            'account_id': liquid_account_id.id,
            'debit': to_debit and abs(amount) or 0.0,
            'credit': not to_debit and abs(amount) or 0.0,
        }

    @api.model
    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        self.ensure_one()

        if not counterpart_account_id:
            counterpart_account_id = self.line_account_id.id

        liquidity_line_vals = self._prepare_liquidity_move_line_vals()
        counterpart_line_vals = liquidity_line_vals.copy()
        counterpart_line_vals.update({
            'account_id': counterpart_account_id,
            'debit': liquidity_line_vals['credit'],
            'credit': liquidity_line_vals['debit']
        })

        return liquidity_line_vals, counterpart_line_vals

    def _seek_for_lines(self):
        """ Helper used to dispatch the journal items between:
        - The lines using the liquidity account.
        - The lines using the transfer account.
        - The lines being not in one of the two previous categories.
        :return: (liquidity_lines, suspense_lines, other_lines)
        """
        liquidity_lines = self.env['account.move.line']
        counterpart_lines = self.env['account.move.line']
        other_lines = self.env['account.move.line']

        liquid_account_id = self._get_liquid_account_id(self.journal_id, self.batch_type)
        counterpart_account = self.line_account_id

        for line in self.account_move_id.line_ids:
            if line.account_id == liquid_account_id:
                liquidity_lines += line
            elif line.account_id == counterpart_account:
                counterpart_lines += line
            else:
                other_lines += line
        return liquidity_lines, counterpart_lines, other_lines

    def _get_init_sync_values(self, line_ids=[]):
        self.ensure_one()
        vals = {
            'batch_fund_line_id': self.id,
            'partner_id': self.line_partner_id.id,
            'currency_id': self.line_currency_id.id,
            'date': self.line_payment_date
        }
        if line_ids:
            vals['line_ids'] = line_ids
        return vals

    def get_aml_adjustments(self, journal_accounts=None):
        """
        Get account.move.line record posted by Adjustments, which is used in Reviewed screen and Reconciliation screen
        Only get lines that have not been reviewed or reconciled
        :param journal_accounts:
        """
        self.ensure_one()
        journal_accounts = journal_accounts or [self.batch_deposit_id.journal_id.payment_debit_account_id.id,
                                                self.batch_deposit_id.journal_id.payment_credit_account_id.id]
        sign = 1 if self.batch_deposit_id.batch_type == 'inbound' else -1
        if self.account_move_id.state == 'posted':
            return self.account_move_id.line_ids.filtered(lambda r: r.account_id.id in journal_accounts and
                                                                (0 < sign*self.line_amount == r.debit or 0 < -sign*self.line_amount == r.credit) and
                                                                (not r.reconciled and not r.bank_reconciled))
        else:
            return self.env['account.move.line']
    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('account_move_id', 'account_move_id.line_ids.reconciled')
    def _compute_bank_reconciled(self):
        for record in self:
            aml_ids = record.get_aml_adjustments()
            record.has_been_reviewed = True if record.move_state == 'posted' and not aml_ids else False

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        # Add Bank Journal to newly created entries
        for vals in vals_list:
            batch_id = self.env['account.batch.payment'].browse(vals['batch_deposit_id'])

            journal = batch_id.journal_id
            vals.update({
                'move_type': 'entry',
                'journal_id': journal.id,
                'currency_id': (journal.currency_id or journal.company_id.currency_id).id,
            })
            if 'date' not in vals and 'line_payment_date' in vals:
                vals['date'] = vals['line_payment_date']

        res = super().create(vals_list)

        for index, line_id in enumerate(res):
            counterpart_account_id = vals_list[index].get('line_account_id', False)
            to_write = line_id._get_init_sync_values()
            if 'line_ids' not in vals_list[index]:
                to_write['line_ids'] = [(0, 0, line_vals) for line_vals in line_id._prepare_move_line_default_vals(
                    counterpart_account_id=counterpart_account_id)]

            line_id.account_move_id.write(to_write)

        return res

    def write(self, vals):
        res = super().write(vals)
        self._synchronize_to_moves(set(vals.keys()))
        return res

    # -------------------------------------------------------------------------
    # SYNCHRONIZATION account.batch.payment.fund.line <-> account.move
    # -------------------------------------------------------------------------

    def _synchronize_to_moves(self, changed_fields):
        """
        Update the account.move regarding the modified account.batch.deposit.fund.line.
        :param changed_fields: A list containing all modified fields on account.bank.statement.line.
        :return:
        """
        if self._context.get('skip_account_move_synchronization'):
            return

        # Cannot sync Journal
        if not any(field_name in changed_fields for field_name in (
            'line_communication', 'line_amount', 'line_currency_id', 'line_partner_id',
            'batch_type', 'line_payment_date', 'line_account_id'
        )):
            return

        for line_id in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, counterpart_lines, other_lines = line_id._seek_for_lines()

            line_vals_list = self._prepare_move_line_default_vals()
            line_ids_commands = [(1, liquidity_lines.id, line_vals_list[0])]

            if counterpart_lines:
                line_ids_commands.append((1, counterpart_lines.id, line_vals_list[1]))
            else:
                line_ids_commands.append((0, 0, line_vals_list[1]))

            for line in other_lines:
                line_ids_commands.append((2, line.id))

            line_id.account_move_id.write(line_id._get_init_sync_values(line_ids=line_ids_commands))

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def action_open_journal_entry(self):
        self.ensure_one()
        return {
            'name': _('Journal Entry'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.account_move_id.id,
            'type': 'ir.actions.act_window',
        }
