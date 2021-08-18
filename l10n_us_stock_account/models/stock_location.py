from odoo import fields, models


class StockLocation(models.Model):
    _name = "stock.location"
    _inherit = ["stock.location", "mail.thread", "mail.activity.mixin"]

    valuation_in_account_id = fields.Many2one(tracking=True)
    valuation_out_account_id = fields.Many2one(tracking=True)
