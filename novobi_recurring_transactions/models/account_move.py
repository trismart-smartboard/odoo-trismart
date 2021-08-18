from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    # ==== Business fields ====
    recurring_transaction_id = fields.Many2one('recurring.transaction', string='Recurring Templates')

