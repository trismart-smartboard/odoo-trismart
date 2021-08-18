# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class JournalDashboard(models.Model):
    _inherit = 'account.journal'

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    def get_journal_dashboard_datas(self):
        results = super().get_journal_dashboard_datas()

        if self.type in ['bank', 'cash']:
            # Add one more condition: status = open
            self._cr.execute('''
                SELECT COUNT(st_line.id)
                FROM account_bank_statement_line st_line
                JOIN account_move st_line_move ON st_line_move.id = st_line.move_id
                JOIN account_bank_statement st ON st_line.statement_id = st.id
                WHERE st_line_move.journal_id IN %s
                AND st.state = 'posted'
                AND NOT st_line.is_reconciled
                AND st_line.status = 'open'
            ''', [tuple(self.ids)])

            results.update({
                'number_for_reviews': self.env.cr.fetchone()[0],
            })
        return results

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def open_bank_statement_line(self):
        domain = [('journal_id', 'in', self.ids)] if self else []
        context = dict(self._context or {})
        context.update(create=False, edit=False)

        status = context.get('status', False)
        if status:
            domain.append(('status', '=', status))

        names = {
            'excluded':     _('Excluded Items'),
            'confirm':      _('Reviewed Items'),
            'reconciled':   _('Reconciled Items')
        }

        return {
            'name': names.get(status, _('Bank Statement Lines')),
            'res_model': 'account.bank.statement.line',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            # 'search_view_id': self.env.ref('l10n_us_accounting.view_bank_statement_line_search_usa').id,
            'domain': domain,
            'target': 'current',
            'context': context
        }

    def action_usa_reconcile(self):
        """
        Either open a popup to set Ending Balance & Ending date
        or go straight to Reconciliation Screen
        """
        draft_reconciliation = self.env['account.bank.reconciliation.data']. \
            search([('journal_id', '=', self.id), ('state', '=', 'draft')], limit=1)

        # If a draft reconciliation is found, go to that screen
        if draft_reconciliation:
            return draft_reconciliation.open_reconcile_screen()

        # open popup
        action = self.env.ref('l10n_us_accounting.action_bank_reconciliation_data_popup').read()[0]
        action['context'] = {'default_journal_id': self.id}
        return action
