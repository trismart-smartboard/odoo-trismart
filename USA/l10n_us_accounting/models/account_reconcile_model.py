# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from collections import defaultdict

class AccountReconcileModelUSA(models.Model):
    _inherit = 'account.reconcile.model'

    # Override
    rule_type = fields.Selection(selection=[
        ('writeoff_button', 'Manually create a write-off on clicked button.'),
        ('writeoff_suggestion', 'Suggest counterpart values.'),
        ('invoice_matching', 'Match existing transactions.')
    ], string='Type', default='writeoff_suggestion', required=True)

    def _apply_conditions(self, query, params, check=False):
        """
        :param query:
        :param params:
        :return: (query, params)
        """
        self.ensure_one()

        if self.rule_type == 'invoice_matching':
            select = """
            AS aml_date_maturity,
            aml.date AS aml_date,
            """

            join_st = """
            ON st_line_move.id = st_line.move_id
            JOIN account_journal journal            ON journal.id = st_line_move.journal_id
            """

            join = """ON payment.move_id = move.id
            LEFT JOIN account_payment_method payment_method ON payment_method.id = payment.payment_method_id
            """

            where = """
            aml.company_id = st_line_move.company_id
            AND aml.journal_id = journal.id
            AND CASE WHEN st_line.amount < 0 THEN payment_method.payment_type = 'outbound' ELSE payment_method.payment_type = 'inbound' END  -- Match payment type
            AND (                                                   -- If Bank line -> must match with bank account of BSL
                account.internal_type = 'liquidity'
                AND aml.account_id IN (journal.payment_debit_account_id, journal.payment_credit_account_id)
                OR account.internal_type != 'liquidity'
            )
            AND aml.bank_reconciled IS NOT TRUE                 -- Has not been reconciled
            AND aml.date <= st_line_move.date           
            """

            query = query.replace('AS aml_date_maturity,', select)
            query = query.replace('ON st_line_move.id = st_line.move_id',join_st)
            query = query.replace('ON payment.move_id = move.id', join)
            query = query.replace('aml.company_id = st_line_move.company_id', where)
            if check:
                query = query.replace('ORDER BY', 'ORDER BY match_check DESC, aml_date DESC,')
            else:
                query = query.replace('ORDER BY', 'ORDER BY aml_date DESC,')

        return query, params

    def _get_invoice_matching_query(self, st_lines_with_partner, excluded_ids):
        query, params = super(AccountReconcileModelUSA, self)._get_invoice_matching_query(st_lines_with_partner,
                                                                                          excluded_ids)
        query, params = self._apply_conditions(query, params)
        return query, params

    def _get_check_matching_query(self, st_lines_with_partner, excluded_ids):
        self.ensure_one()
        query = r'''
                SELECT
                    st_line.id                                  AS id,
                    aml.id                                      AS aml_id,
                    aml.currency_id                             AS aml_currency_id,
                    aml.date_maturity                           AS aml_date_maturity,
                    CASE WHEN st_line.check_number_cal IS NOT NULL AND st_line.check_number_cal = payment.check_number THEN 1 ELSE 0 END AS match_check,
                    TRUE                                        AS payment_reference_flag,
                    aml.amount_residual                         AS aml_amount_residual,
                    aml.amount_residual_currency                AS aml_amount_residual_currency
                FROM account_bank_statement_line st_line
                JOIN account_move st_line_move                  ON st_line_move.id = st_line.move_id    
                JOIN res_company company                        ON company.id = st_line_move.company_id
                , account_move_line aml
                LEFT JOIN account_payment payment               ON payment.id = aml.payment_id
                LEFT JOIN account_payment_method payment_method ON payment_method.id = payment.payment_method_id
                LEFT JOIN account_move move                     ON move.id = aml.move_id AND move.state = 'posted'
                LEFT JOIN account_account account               ON account.id = aml.account_id
                LEFT JOIN res_partner aml_partner               ON aml.partner_id = aml_partner.id
                WHERE
                    aml.company_id = st_line_move.company_id        
                    AND move.state = 'posted'
                    AND account.reconcile IS TRUE
                    AND aml.reconciled IS FALSE
                '''

        # Add conditions to handle each of the statement lines we want to match
        st_lines_queries = []
        for st_line in st_lines_with_partner:
            check_st = r" AND st_line.amount = aml.balance AND st_line.check_number_cal IS NOT NULL AND st_line.check_number_cal = payment.check_number"
            if st_line.amount > 0:
                st_line_subquery = r"aml.balance > 0" + check_st
            else:
                st_line_subquery = r"aml.balance < 0" + check_st

            if self.match_same_currency:
                st_line_subquery += r" AND COALESCE(aml.currency_id, company.currency_id) = %s" % (
                            st_line.foreign_currency_id.id or st_line.move_id.currency_id.id)

            st_lines_queries.append(r"st_line.id = %s AND (%s)" % (st_line.id, st_line_subquery))

        query += r" AND (%s) " % " OR ".join(st_lines_queries)

        params = {}

        if self.past_months_limit:
            date_limit = fields.Date.context_today(self) - relativedelta(months=self.past_months_limit)
            query += "AND aml.date >= %(aml_date_limit)s"
            params['aml_date_limit'] = date_limit

        # Filter out excluded account.move.line.
        if excluded_ids:
            query += 'AND aml.id NOT IN %(excluded_aml_ids)s'
            params['excluded_aml_ids'] = tuple(excluded_ids)

        if self.matching_order == 'new_first':
            query += ' ORDER BY aml_date_maturity DESC, aml_id DESC'
        else:
            query += ' ORDER BY aml_date_maturity ASC, aml_id ASC'
        query, params = self._apply_conditions(query, params, check=True)

        return query, params

    def _get_candidates(self, st_lines_with_partner, excluded_ids):
        self.ensure_one()
        rslt = super(AccountReconcileModelUSA, self)._get_candidates(st_lines_with_partner, excluded_ids)
        # check matching
        if self.rule_type == 'invoice_matching':
            st_check_lines = [st for st, partner in st_lines_with_partner if st.check_number_cal]
            if st_check_lines:
                query, params = self._get_check_matching_query(st_check_lines, excluded_ids)
                self._cr.execute(query, params)

                res = defaultdict(lambda: [])
                for candidate_dict in self._cr.dictfetchall():
                    res[candidate_dict['id']].append(candidate_dict)
                # update rslt
                for key, val in res.items():
                    rslt[key] = val
        return rslt
