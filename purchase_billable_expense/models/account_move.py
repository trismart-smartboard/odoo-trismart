from odoo import models, fields


class AccountMoveUSA(models.Model):
    _name = "account.move"
    _inherit = ['account.move','billable.expenses.mixin']

    def _assign_billable_expense(self, type = None):
        return super(AccountMoveUSA,self)._assign_billable_expense(type = "bill")

    def action_post(self):
        """
        Inherit to automatically assign billable expenses to current bill (User does not have to click on button Assign)
        """
        super(AccountMoveUSA, self).action_post()
        for record in self.filtered(lambda r: r.move_type == 'in_invoice'):
            record._assign_billable_expense()

