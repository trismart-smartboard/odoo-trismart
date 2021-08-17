# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_is_zero
from odoo.addons.l10n_custom_dashboard.utils.graph_setting import format_currency
from odoo.tools.misc import formatLang, format_date
# -------------------------------------------------------------------------
# LOG STATE + MESSAGE
# -------------------------------------------------------------------------
LOG_CREATE = 1
LOG_UPDATE = 2
LOG_DELETE = 3

LOG_MSG_CREATE = "Journal Item has been created."
LOG_MSG_UPDATE = "Journal Item has been updated."
LOG_MSG_DELETE = "Journal Item has been deleted."


class AccountMoveLineUSA(models.Model):
    _inherit = 'account.move.line'

    eligible_for_1099 = fields.Boolean(string='Eligible for 1099?', default=True)

    batch_fund_line_id = fields.Many2one('account.batch.deposit.fund.line',
                                         related='move_id.batch_fund_line_id', store=True)

    # BANK RECONCILIATION FIELDS
    # This field is marked after reviewed, and to be checked by default when go to Reconciliation Screen.
    temporary_reconciled = fields.Boolean(string='Have been Reviewed?', default=False, copy=False)
    # Reconciled. Will be set after reconciled and reset after undo a Reconciliation session.
    bank_reconciled = fields.Boolean(string='Have been Reconciled?', default=False, copy=False)

    reconciled_line_id = fields.Many2one('account.move.line', string='Reconciled Move Line',
                                         help='Payment Line reconciled with this Statement Move Line',
                                         compute='_compute_reconciled_line_id', store=True)
    reconciled_payment_id = fields.Many2one('account.payment', string='Reconciled Payment',
                                            help='Payment reconciled with this Statement Move Line',
                                            related='reconciled_line_id.payment_id')
    reconciled_statement_line_ids = fields.One2many('account.move.line', 'reconciled_line_id',
                                                    string='Reconciled Statement Line',
                                                    help='Statement Line reconciled with this Move Line, '
                                                         'counterpart of Reconciled Move Line')

    # -------------------------------------------------------------------------
    # RECONCILIATION
    # -------------------------------------------------------------------------
    def _prepare_reconciliation_partials(self):
        """
        Override
        Allow to apply partial payment
        Only handle the case that invoice and payment have the same currency
        """
        res = super(AccountMoveLineUSA, self)._prepare_reconciliation_partials()
        partial_amount_currency = self._context.get('partial_amount', False)
        company_currency = self.env.company.currency_id
        partial_vals = res and res[0] or False
        if not float_is_zero(partial_amount_currency, precision_digits=company_currency.rounding) and partial_vals:
            debit_line = self.env['account.move.line'].browse(partial_vals['debit_move_id'])
            credit_line = self.env['account.move.line'].browse(partial_vals['credit_move_id'])

            if debit_line.currency_id != credit_line.currency_id:
                return res

            if partial_amount_currency >= partial_vals['amount']:
                return res

            partial_vals.update({
                'amount': partial_amount_currency,
                'debit_amount_currency': partial_amount_currency,
                'credit_amount_currency': partial_amount_currency,
            })
        return res

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def name_get(self):
        if self.env.context.get("default_payment_name_get"):
            result = []
            env = self.env
            for line in self:
                date_due = line.date_maturity or line.move_id.invoice_date_due or line.move_id.date
                amount = abs(line.amount_currency)
                name = (line.move_id.name or '') + " - %s - %s" % (
                format_date(env, date_due), formatLang(env, amount, currency_obj=line.currency_id))
                result.append((line.id, name))
            return result
        else:
            return super().name_get()

    def _log_values(self, state, values):

        if state == LOG_CREATE and isinstance(values, list):
            string = LOG_MSG_CREATE
        elif state == LOG_UPDATE and any(c in values for c in ['account_id', 'partner_id', 'debit', 'credit']) and len(values) > 1:
            string = LOG_MSG_UPDATE
        elif state == LOG_DELETE and not len(values):
            string = LOG_MSG_DELETE
        else:
            return
        moves = self.mapped('move_id')
        for move in moves:
            move_lines = self.filtered(lambda x: x.move_id == move)
            msg = "<b>" + _(string) + "</b><ul>"
            for line in move_lines:
                if 'account_id' in values:

                    account_name = self.env['account.account'].browse(values['account_id']).name
                    new_account_name = "<i>None</i>" if not account_name else account_name
                    old_account_name = "<i>None</i>" if not line.account_id.name else line.account_id.name

                    msg += (_("Account: ") + "%s -> %s <br/>" % (old_account_name, new_account_name))
                else:
                    msg += (_("Account: ") + "%s<br/>" % line.account_id.name) if line.account_id.name else _("Account: <i>None</i><br/>")
                if 'partner_id' in values and values['partner_id']:
                    partner_id = values['partner_id'] if isinstance(values['partner_id'], int) else values['partner_id'].id
                    partner_name = self.env['res.partner'].browse(partner_id).name
                    new_partner_name = "<i>None</i>" if not partner_name else partner_name
                    old_partner_name = "<i>None</i>" if not line.partner_id.name else line.partner_id.name

                    msg += _("Partner: <i>None</i><br/>") if new_partner_name == "<i>None</i>"\
                        else (_("Partner: ") + "%s -> %s <br/>" % (old_partner_name, new_partner_name))

                else:
                    msg += (_("Partner: ") + "%s<br/>" % line.partner_id.name) if (line.partner_id.name) else _("Partner: <i>None</i><br/>")
                if 'debit' in values or 'credit' in values:
                    deb = values['debit'] if 'debit' in values else line.debit
                    cred = values['credit'] if 'credit' in values else line.credit
                    old_balance = format_currency(self,line.balance)
                    new_balance = format_currency(self,deb - cred)
                    msg += (_("Balance: ") + "%s -> %s <br/>" % (
                        old_balance, new_balance))
                else:
                    msg += (_("Balance: ") + "%s<br/>" % (format_currency(self, line.balance)))
                msg += (_("Label: ") + "%s<br/>" % line.name) if line.name else ""
                msg += "<br/>"
            msg += "</ul>"

            move.message_post(body=msg)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('statement_line_id', 'matched_debit_ids', 'matched_credit_ids')
    def _compute_reconciled_line_id(self):
        """
        This is for Statement Line's items only.
        If it's reviewed, Suspense Account -> Outstanding Receipts/Payment.
        Safe to say there'll only be 1 line in match_debit or credit.
        """
        for record in self:
            journal_account_ids = [record.journal_id.payment_debit_account_id.id,
                                   record.journal_id.payment_credit_account_id.id]
            reconciled_line_id = False

            if record.statement_line_id and record.account_id.id in journal_account_ids:
                if record.matched_debit_ids:
                    reconciled_line_id = record.matched_debit_ids[0].debit_move_id
                elif record.matched_credit_ids:
                    reconciled_line_id = record.matched_credit_ids[0].credit_move_id

            record.reconciled_line_id = reconciled_line_id

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    def unlink(self):
        self._log_values(LOG_DELETE, {})
        result = super(AccountMoveLineUSA, self).unlink()
        return result

    def write(self, values):
        self._log_values(LOG_UPDATE, values)
        result = super(AccountMoveLineUSA, self).write(values)
        return result

    def create(self, values):
        result = super(AccountMoveLineUSA, self).create(values)
        result._log_values(LOG_CREATE, values)
        return result

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def update_temporary_reconciled(self, ids, checked):
        # Click on checkbox or select/deselect all on Reconciliation Screen.
        return self.browse(ids).write({'temporary_reconciled': checked})

    def mark_bank_reconciled(self):
        """
        Apply reconcile on Reconciliation Screen.
        - Set bank_reconciled = True for this account_move_line.
        - Check BSL. If all Journal Items in this BSL have been reconciled, mark it reconciled.
        """
        self.write({'bank_reconciled': True})

        statement_line_ids = self.mapped('statement_line_id') + \
                             self.mapped('reconciled_statement_line_ids.statement_line_id')

        for line in statement_line_ids:
            if False not in line.get_reconciled_states():
                line.status = 'reconciled'

    def undo_bank_reconciled(self):
        """
        Undo last reconciliation.
        - Set bank_reconciled = False for this account_move_line.
        - Set status of BSL to 'confirm'.
        """
        self.write({'bank_reconciled': False})

        statement_line_ids = self.mapped('statement_line_id') + \
                             self.mapped('reconciled_statement_line_ids.statement_line_id')
        statement_line_ids.filtered(lambda x: x.status == 'reconciled').write({'status': 'confirm'})
