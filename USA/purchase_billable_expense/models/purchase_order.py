# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseOrderUSA(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'billable.expenses.mixin']
    billable_expenses_ids = fields.One2many('billable.expenses', 'purchase_id')  # correspond with each purchase line

    def _get_expense_popup(self):
        purchase_view_id = self.env.ref('purchase_billable_expense.purchase_assign_expense_popup_form').id
        expense_popup = super(PurchaseOrderUSA, self)._get_expense_popup()
        expense_popup['view_id'] = purchase_view_id
        return expense_popup

    def _assign_billable_expense(self, type=None):
        return super(PurchaseOrderUSA, self)._assign_billable_expense(type="purchase")

    def button_cancel(self):
        """
        Remove Expense if Purchase is canceled/deleted.
        """
        res = super(PurchaseOrderUSA, self).button_cancel()
        for record in self:
            record.billable_expenses_ids.sudo().unlink()  # delete expense for PO

        return res


class PurchaseOrderLineUSA(models.Model):
    _inherit = 'purchase.order.line'

    billable_expenses_ids = fields.One2many('billable.expenses', 'purchase_line_id')  # only one record, for PO
    invoiced_to_id = fields.Many2one('account.move', compute='_compute_invoiced_to_id', store=True)
    billable_expense_customer_id = fields.Many2one('res.partner', 'Assigned Customer', store=True,
                                                   related='billable_expenses_ids.customer_id')

    @api.depends('billable_expenses_ids', 'billable_expenses_ids.customer_id',
                 'billable_expenses_ids.is_outstanding', 'state')
    def _compute_invoiced_to_id(self):
        for record in self:
            invoiced_to_id = False
            if record.state in ['purchase', 'done']:
                if record.billable_expenses_ids and record.billable_expenses_ids[0].customer_id:
                    expense = record.billable_expenses_ids[0]
                    if not expense.is_outstanding:  # already invoiced
                        invoiced_to_id = expense.invoice_line_id.move_id
            record.invoiced_to_id = invoiced_to_id


