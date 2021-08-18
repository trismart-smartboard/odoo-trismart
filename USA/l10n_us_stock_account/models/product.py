from odoo import api, fields, models, tools, _


class ProductCategory(models.Model):
    _name = "product.category"
    _inherit = ["product.category", "mail.thread", "mail.activity.mixin"]

    property_cost_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('fifo', 'First In First Out (FIFO)'),
        ('average', 'Average Cost (AVCO)')], tracking=True)
    property_valuation = fields.Selection([
        ('manual_periodic', 'Manual'),
        ('real_time', 'Automated')], tracking=True)
    property_account_income_categ_id = fields.Many2one(tracking=True)
    property_account_expense_categ_id = fields.Many2one(tracking=True)
    property_account_creditor_price_difference_categ = fields.Many2one(tracking=True)
    property_stock_account_input_categ_id = fields.Many2one(tracking=True)
    property_stock_account_output_categ_id = fields.Many2one(tracking=True)
    property_stock_journal = fields.Many2one(tracking=True)
    property_stock_valuation_account_id = fields.Many2one(tracking=True)
