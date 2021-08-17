from odoo import api, exceptions, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime


class BillableExpenseMixin(models.AbstractModel):
    _inherit = 'billable.expenses.mixin'


    def _assign_billable_expense(self, type = None):
        """
        Get billable expenses from Purchase Order/Bill, or create new ones.
        """
        self.ensure_one()
        expense_env = self.env['billable.expenses'].sudo()
        line_attr = ""
        if type == 'bill':
            line_ids = self.invoice_line_ids
            ids = self.billable_expenses_ids.mapped('bill_line_id')
            line_attr = "purchase_line_id"
            bill_date = self.invoice_date
            updated_attrs = ("bill_id", "bill_line_id")
        elif type == 'purchase':
            line_ids = self.order_line
            ids = self.billable_expenses_ids.mapped('purchase_line_id')
            line_attr = "invoice_lines"
            bill_date = datetime.strptime(fields.Datetime.to_string(self.date_order), DEFAULT_SERVER_DATETIME_FORMAT)
            updated_attrs = ("purchase_id", "purchase_line_id")
        # For all bill lines that have not been set billable expense:
        for line in line_ids - ids:
            # If the purchase order line linked to it has been assigned billable expense -> Link current bill and bill line.
            if line[line_attr] and line[line_attr].billable_expenses_ids:
                line[line_attr].billable_expenses_ids.write({
                    updated_attrs[0]: self.id,
                    updated_attrs[1]: line.id
                })
            # Create new billable expense and link it to current bill/bill line.
            else:
                expense_env.create({
                    updated_attrs[0]: self.id,
                    updated_attrs[1]: line.id,
                    'description': line.name,
                    'amount': line.price_subtotal,
                    'bill_date': bill_date
                })



