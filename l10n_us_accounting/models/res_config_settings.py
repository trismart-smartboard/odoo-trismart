# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettingsUSA(models.TransientModel):
    _inherit = 'res.config.settings'

    bad_debt_account_id = fields.Many2one("account.account", string='Write Off Account for Invoices',
                                          related='company_id.bad_debt_account_id', readonly=False,
                                          domain=[('deprecated', '=', False)])

    bill_bad_debt_account_id = fields.Many2one("account.account", string='Write Off Account for Bills',
                                          related='company_id.bill_bad_debt_account_id', readonly=False,
                                          domain=[('deprecated', '=', False)])