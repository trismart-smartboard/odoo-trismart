# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = "res.company"

    invoice_tax_account_id = fields.Many2one('account.account', string="Default Invoice Tax Account")
    credit_tax_account_id = fields.Many2one('account.account', string="Default Credit Note Tax Account")
