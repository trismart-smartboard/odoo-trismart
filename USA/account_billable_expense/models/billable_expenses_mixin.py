from odoo import api, exceptions, fields, models, _

class BillableExpenseMixin(models.AbstractModel):
    _name = 'billable.expenses.mixin'
    _description = 'Billable Expense Mixin'

    def _get_expense_popup(self):
        view_id = self.env.ref('account_billable_expense.assign_expense_form').id
        return {
            'name': 'Assign a customer to any billable expense',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'target': 'new',
            'res_id': self.id,
            'view_id': view_id,
        }
    def _assign_billable_expense(self, type = None):
        self.ensure_one()
        bill_line_ids = self.billable_expenses_ids.mapped('bill_line_id')
        expense_env = self.env['billable.expenses'].sudo()

        for line in self.invoice_line_ids - bill_line_ids:
            expense_env.create({
                'bill_id': self.id,
                'bill_line_id': line.id,
                'description': line.name,
                'amount': line.price_subtotal,
                'bill_date': self.invoice_date
            })

    def open_expense_popup(self):
        self._assign_billable_expense()
        return self._get_expense_popup()

    def assign_customer(self):
        return {'type': 'ir.actions.act_window_close'}
