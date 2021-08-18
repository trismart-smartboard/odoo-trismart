# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    account_eligible_1099 = fields.Boolean(string='Eligible for 1099?', default=False)

    @api.onchange('reconcile')
    def _onchange_reconcile_usa(self):
        if self.reconcile:
            self.account_eligible_1099 = False
