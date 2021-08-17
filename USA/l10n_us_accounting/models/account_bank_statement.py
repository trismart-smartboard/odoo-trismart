# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def button_reopen(self):
        """
        Override.
        Set all statement lines status to open (already done in button_undo_reconciliation)
        :return:
        """
        if any(line.status == 'reconciled' for line in self.line_ids):
            raise UserError(_("There are some reconciled statement lines. Please undo a reconciliation session instead."))

        super().button_reopen()

    @api.depends('line_ids.status')
    def _compute_all_lines_reconciled(self):
        """
        Override
        Change reconciled condition of Bank statement
        """
        for statement in self:
            statement.all_lines_reconciled = all(st_line.status == 'reconciled' for st_line in statement.line_ids)
