# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountJournalUSA(models.Model):
    _inherit = 'account.journal'

    is_credit_card = fields.Boolean(string='Is Credit Card?')
    partner_id = fields.Many2one('res.partner', string='Vendor',
                                 help='This contact will be used to record vendor bill and payment '
                                      'for credit card balance.',
                                 copy=False)
    show_transactions_from = fields.Date(string='Show transaction from',
                                         help='Save the last start_date value in bank reconciliation screen')

    def _fill_missing_values(self, vals):
        journal_type = vals.get('type')
        has_payment_accounts = vals.get('payment_debit_account_id') or vals.get('payment_credit_account_id')
        super(AccountJournalUSA, self)._fill_missing_values(vals)
        if journal_type and journal_type in ('bank', 'cash') and not has_payment_accounts:
            account = self.env['account.account']
            account.browse(vals['payment_debit_account_id']).write({
                'name': _("%s Outstanding Receipts") % vals['name'],
            })
            account.browse(vals['payment_credit_account_id']).write({
                'name': _("%s Outstanding Payments") % vals['name'],
            })
            