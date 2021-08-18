# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    invoice_tax_account_id = fields.Many2one('account.account',
                                             related='company_id.invoice_tax_account_id', readonly=False, required=False)
    credit_tax_account_id = fields.Many2one('account.account',
                                            related='company_id.credit_tax_account_id', readonly=False, required=False)
