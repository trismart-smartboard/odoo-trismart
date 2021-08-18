from odoo import models, fields, _


class AccountFinancialReportLine(models.Model):
    _inherit = "account.financial.html.report.line"

    hide_in_budget = fields.Boolean('Hide in Budget Spreadsheet?', default=False)