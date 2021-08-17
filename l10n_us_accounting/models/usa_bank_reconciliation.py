# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields
from datetime import datetime
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang


class USABankReconciliation(models.AbstractModel):
    _inherit = 'account.report'
    _name = 'usa.bank.reconciliation'
    _description = 'Bank Reconciliation Session'

    ####################################################
    # OPTIONS: TEMPLATES
    ####################################################
    def _get_templates(self):
        templates = super(USABankReconciliation, self)._get_templates()
        templates['line_template'] = 'l10n_us_accounting.line_template_usa_bank_reconciliation'
        templates['main_template'] = 'l10n_us_accounting.template_usa_bank_reconciliation'
        return templates

    def _get_columns_name(self, options):
        # Payment is Credit (Send Money). Deposit is Debit (Receive Money).
        return [
            {},
            {'name': _('Date'), 'class': 'date'},
            {'name': _('Payee')},
            {'name': _('Batch Payment')},
            {'name': _('Memo')},
            {'name': _('Check Number')},
            {'name': _('Payment'), 'class': 'number'},
            {'name': _('Deposit'), 'class': 'number'},
            {'name': _('Reconcile')},
        ]

    def _get_report_name(self):
        bank_reconciliation_data_id = self._get_bank_reconciliation_data_id()

        return bank_reconciliation_data_id.journal_id.name

    def _get_reports_buttons(self):
        return []

    ####################################################
    # OPTIONS: HELPERS
    ####################################################
    def _format_date(self, date):
        return datetime.strftime(date, '%m/%d/%Y')

    def get_html(self, options, line_id=None, additional_context=None):
        bank_reconciliation_data_id = self._get_bank_reconciliation_data_id()

        if additional_context == None:
            additional_context = {}

        beginning_balance = bank_reconciliation_data_id.beginning_balance
        ending_balance = bank_reconciliation_data_id.ending_balance

        additional_context.update({
            'today': self._format_date(bank_reconciliation_data_id.statement_ending_date),
            'beginning_balance': beginning_balance,
            'ending_balance': ending_balance,
            'formatted_beginning': self.format_value(beginning_balance),
            'formatted_ending': self.format_value(ending_balance),
            'bank_reconciliation_data_id': bank_reconciliation_data_id.id
        })

        options['currency_id'] = bank_reconciliation_data_id.currency_id.id
        options['multi_company'] = None

        return super(USABankReconciliation, self).get_html(options, line_id=line_id,
                                                           additional_context=additional_context)

    def _get_bank_reconciliation_data_id(self):
        bank_reconciliation_data_id = None
        bank_id = self.env.context.get('bank_reconciliation_data_id', False)

        params = self.env.context.get('params', False)

        if not bank_id and params and params.get('action', False):
            action_obj = self.env['ir.actions.client'].browse(params['action'])
            bank_id = action_obj.params.get('bank_reconciliation_data_id', False)

        if bank_id:
            bank_reconciliation_data_id = self.env['account.bank.reconciliation.data'].browse(bank_id)

        if not bank_reconciliation_data_id:
            raise UserError(_('Cannot get Bank\'s information.'))

        if bank_reconciliation_data_id.state == 'reconciled':
            raise UserError(_('You can not access this screen anymore because it is already reconciled.'))

        return bank_reconciliation_data_id

    def open_batch_deposit_document(self, options, params=None):
        """
        Called when pressing caret option of batch adjustment line
        """
        if not params:
            params = {}
        ctx = self.env.context.copy()
        ctx.pop('id', '')
        move_line_id = self.env['account.move.line'].browse( params.get('id', False))
        batch_id = move_line_id.batch_fund_line_id or move_line_id.payment_id.batch_payment_id or False
        if batch_id:
            view_id = self.env.ref('account_batch_payment.view_batch_payment_form').id
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'tree',
                'view_mode': 'form',
                'views': [(view_id, 'form')],
                'res_model': 'account.batch.payment',
                'view_id': view_id,
                'res_id': batch_id.id,
                'context': ctx,
            }

    ####################################################
    # OPTIONS: CORE
    ####################################################
    @api.model
    def _get_lines(self, options, line_id=None):
        def get_batch_payment_info(batch_id):
            batch_amount = formatLang(self.env, batch_id.amount, currency_obj=batch_id.currency_id)
            return'{} {}'.format(batch_id.name, batch_amount)

        lines = []
        bank_reconciliation_data_id = self._get_bank_reconciliation_data_id()

        aml_ids = bank_reconciliation_data_id._get_transactions()
        bank_reconciliation_data_id.write({'aml_ids': [(6, 0, aml_ids.ids)]})

        # Filter by Start Date:
        if bank_reconciliation_data_id.start_date:
            hidden_transactions = aml_ids.filtered(lambda x: x.date < bank_reconciliation_data_id.start_date)
            hidden_transactions.write({'temporary_reconciled': False})
            aml_ids = aml_ids - hidden_transactions

        for line in aml_ids:
            """
            Date
            Payee
            Batch Payment (Name + amount)
            Memo
            Check Number
            Payment (Credit/Send Money)
            Deposit (Debit/Receive Money)
            Reconcile
            """

            check_number = line.payment_id.check_number if line.payment_id and line.payment_id.check_number else ''
            credit = line.credit
            debit = line.debit
            # For writeoff/AR/AP in BSL's journal entry, reverse the debit/credit side
            if line.statement_line_id:
                credit = line.debit
                debit = line.credit

            batch_payment_info = ''
            if line.batch_fund_line_id:
                # Get batch payment info of batch adjustment line
                batch_payment_info = get_batch_payment_info(line.batch_fund_line_id.batch_deposit_id)
            if line.payment_id and line.payment_id.batch_payment_id:
                # Get batch payment info of payment's line
                batch_payment_info = get_batch_payment_info(line.payment_id.batch_payment_id)

            columns = [self._format_date(line.date),
                       line.partner_id.name if line.partner_id else '',
                       batch_payment_info,
                       line.name,
                       check_number,
                       self.format_value(credit) if credit > 0 else '',
                       self.format_value(debit) if debit > 0 else '',
                       {'name': False, 'blocked': line.temporary_reconciled,
                        'debit': debit,
                        'credit': credit}]

            caret_type = 'account.move'
            caret_batch_payment = False
            if line.payment_id:
                caret_type = 'account.payment'
            if line.batch_fund_line_id or line.payment_id.batch_payment_id:
                caret_batch_payment = True

            lines.append({
                'id': line.id,
                'name': line.move_id.name,
                'caret_options': caret_type,
                'caret_batch_payment': caret_batch_payment,
                'model': 'account.move.line',
                'columns': [type(v) == dict and v or {'name': v} for v in columns],
                'level': 1,
            })

        if not lines:
            lines.append({
                'id': 'base',
                'model': 'base',
                'level': 0,
                'class': 'o_account_reports_domain_total',
                'columns': [{'name': v} for v in ['', '', '', '', '', '', '']],
            })
        return lines
