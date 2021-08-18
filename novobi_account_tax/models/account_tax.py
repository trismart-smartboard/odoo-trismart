# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import models, fields, api, _


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.model
    def default_get(self, vals):
        # company_id is added so that we are sure to fetch a default value from it to use in repartition lines, below
        rslt = super().default_get(vals + ['company_id'])

        company_id = rslt.get('company_id')
        company = self.env['res.company'].browse(company_id)

        if 'invoice_repartition_line_ids' in rslt:
            rslt['invoice_repartition_line_ids'][1][2]['account_id'] = company.invoice_tax_account_id.id

        if 'refund_repartition_line_ids' in rslt:
            rslt['refund_repartition_line_ids'][1][2]['account_id'] = company.credit_tax_account_id.id

        return rslt


class AccountTaxRepartitionLine(models.Model):
    _inherit = "account.tax.repartition.line"

    def _default_account_id(self):
        company = self.company_id if self.company_id else self.env.company
        if self.env.context.get('default_invoice_tax', False):
            return company.invoice_tax_account_id.id
        else:
            return company.credit_tax_account_id.id

    # Override
    account_id = fields.Many2one(default=_default_account_id)
