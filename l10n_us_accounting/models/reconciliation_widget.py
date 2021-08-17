from odoo import fields, models, api


class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    # -------------------------------------------------------------------------
    # BANK STATEMENT
    # -------------------------------------------------------------------------
    @api.model
    def get_bank_statement_data(self, bank_statement_line_ids, srch_domain=[]):
        """
        Override.
        Called when load reviewed form.
        Add status = open to `domain` in order to remove excluded/reconciled bank statement lines.
        :param bank_statement_line_ids:
        :param srch_domain:
        :return:
        """
        srch_domain.append(('status', '=', 'open'))
        return super().get_bank_statement_data(bank_statement_line_ids, srch_domain)

    @api.model
    def process_bank_statement_line(self, st_line_ids, data):
        """
        Override.
        Called when clicking on button `Apply` on `bank_statement_reconciliation_view` (review screen)

        :param st_line_ids
        :param list of dicts data: must contains the keys
            'counterpart_aml_dicts', 'payment_aml_ids' and 'new_aml_dicts',
            whose value is the same as described in process_reconciliation
            except that ids are used instead of recordsets.
        :returns dict: used as a hook to add additional keys.
        """
        result = super().process_bank_statement_line(st_line_ids, data)

        statement_lines = self.env['account.bank.statement.line'].browse(st_line_ids)

        # Mark BSL as reviewed
        statement_lines.write({'status': 'confirm'})

        # Mark all the lines that are not Bank or Bank Suspense Account temporary_reconcile
        statement_lines.get_reconciliation_lines().write({'temporary_reconciled': True})

        return result

    # -------------------------------------------------------------------------
    # BATCH PAYMENT
    # -------------------------------------------------------------------------
    @api.model
    def get_move_lines_by_batch_payment(self, st_line_id, batch_payment_id):
        """
        Override
        Also get move lines for adjustments of batch payment.
        """
        res = super(AccountReconciliation, self).get_move_lines_by_batch_payment(st_line_id, batch_payment_id)
        st_line = self.env['account.bank.statement.line'].browse(st_line_id)
        batch_id = self.env['account.batch.payment'].browse(batch_payment_id)
        aml_ids = self.env['account.move.line']
        journal_accounts = [batch_id.journal_id.payment_debit_account_id.id, batch_id.journal_id.payment_credit_account_id.id]
        for line in batch_id.fund_line_ids:
            line_id = line.get_aml_adjustments(journal_accounts)
            aml_ids |= line_id
        aml_list = [self._prepare_js_reconciliation_widget_move_line(st_line, line) for line in aml_ids]

        return res + aml_list

    @api.model
    def get_batch_payments_data(self, bank_statement_ids):
        """
        Override
        Filter batch payments in BSL review screen following conditions:
        - Batch payments must have same Journal as BSL
        - Batch payments type (IN/OUT) must have Same Transaction Type as BSL
        - Unreconciled amount of batch payment <= amount of BSL
        """
        batch_payments = super(AccountReconciliation, self).get_batch_payments_data(bank_statement_ids)
        length = len(batch_payments)
        index = 0

        while index < length:
            batch = batch_payments[index]
            batch_id = self.env['account.batch.payment'].browse(batch['id'])
            move_lines = batch_id.get_batch_payment_aml()
            if move_lines:
                batch.update(batch_id._get_batch_info_for_review())
                index += 1
            else:
                del batch_payments[index]
                length -= 1

        return batch_payments

    # -------------------------------------------------------------------------
    # MATCHING CONDITION
    # -------------------------------------------------------------------------
    @api.model
    def _get_query_reconciliation_widget_customer_vendor_matching_lines(self, statement_line, domain=[]):
        """
        Override
        Add more conditions to filter account move lines of Customer/Vendor Matching tab in BSL review screen
        - Transaction Date <= BSL date
        - Based on transaction type (Deposit/Payment)
        - Transactions' amount <= BSLs' amount
        - Same Payee (OOTB)
        """
        domain = domain + [
            ('date', '<=', statement_line.date),
            '|',
                '&', ('debit', '=', 0), ('credit', '<=', -statement_line.amount),
                '&', ('credit', '=', 0), ('debit', '<=', statement_line.amount),
        ]
        return super(AccountReconciliation, self)._get_query_reconciliation_widget_customer_vendor_matching_lines(statement_line, domain)

    @api.model
    def _get_query_reconciliation_widget_miscellaneous_matching_lines(self, statement_line, domain=[]):
        """
        Override
        Add more conditions to filter account move lines of Miscellaneous Matching tab in BSL review screen
        - Transaction Date <= BSL date
        - Based on transaction type (Deposit/Payment)
        - Transactions' amount <= BSLs' amount
        - Same Payee (OOTB)
        """
        liquidity_journals = self.env['account.journal'].search([('id', '!=', statement_line.journal_id.id),
                                                                 ('type', 'in', ['bank', 'cash'])])
        liquidity_account_ids = liquidity_journals.mapped('payment_credit_account_id.id') +\
                                liquidity_journals.mapped('payment_debit_account_id.id')
        domain = domain + [
            ('account_id.id', 'not in', liquidity_account_ids),
            ('date', '<=', statement_line.date),
            '|',
                '&', ('debit', '=', 0), ('credit', '<=', -statement_line.amount),
                '&', ('credit', '=', 0), ('debit', '<=', statement_line.amount),
        ]
        return super(AccountReconciliation, self)._get_query_reconciliation_widget_miscellaneous_matching_lines(statement_line, domain)
