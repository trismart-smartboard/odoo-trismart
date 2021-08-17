# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    bad_debt_account_id = fields.Many2one("account.account", string=' Write Off Account for Invoices',
                                          domain=[('deprecated', '=', False)])
    bill_bad_debt_account_id = fields.Many2one("account.account", string=' Write Off Account for Bills',
                                          domain=[('deprecated', '=', False)])
    reconciliation_discrepancies_account_id = fields.Many2one('account.account', 'Reconciliation Discrepancies Account',
                                                              domain=[('deprecated', '=', False)])
