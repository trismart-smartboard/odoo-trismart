from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountInvoiceUSA(models.Model):

    _name = 'account.move'
    _inherit = ['account.move','billable.expenses.mixin']

    billable_expenses_ids = fields.One2many('billable.expenses', 'bill_id')  # correspond with each invoice line
    expense_btn_name = fields.Char(compute='_get_expense_btn_name')

    is_billable = fields.Boolean('Billable expense', compute="_get_is_billable", store=True)

    @api.depends('invoice_line_ids', 'invoice_line_ids.is_billable')
    def _get_is_billable(self):
        for record in self:
            record.is_billable = any(line.is_billable for line in record.invoice_line_ids)

    @api.depends('partner_id')
    def _get_expense_btn_name(self):
        """
        Compute name for button assign expenses to invoice.
        Billable expense is shared between main and sub contacts.
        """
        for record in self:
            expenses = record.partner_id.get_outstanding_expenses({}, record.company_id.ids, subcontact=True)
            if expenses:
                added_expenses = expenses.filtered(lambda ex: ex.invoice_line_id)
                record.expense_btn_name = \
                    '{} of {} billable expense(s) added'.format(len(added_expenses),
                                                                len(expenses)) if added_expenses else \
                        '{} billable expense(s) can be added'.format(len(expenses))
            else:
                record.expense_btn_name = False

    @api.onchange('partner_id')
    def _update_expense_btn_name(self):
        self.ensure_one()
        if self.move_type == 'out_invoice':
            if self.invoice_line_ids.filtered(lambda x: x.is_billable):
                raise UserError(_('Please remove added billable expenses before changing customer.'))
            else:
                self._get_expense_btn_name()

    def get_customer_billable_expenses(self):
        self.ensure_one()
        billable_expense = self.partner_id.get_outstanding_expenses({}, self.company_id.ids, subcontact=True)
        billable_expense.write({'invoice_currency_id': self.currency_id.id})
        return billable_expense.ids

    def button_draft(self):
        res = super(AccountInvoiceUSA, self).button_draft()
        for record in self:
            # Context unlink_bill=True is used in purchase_billable_expense
            record.billable_expenses_ids.sudo().with_context(unlink_bill=True).unlink()  # delete expense for bill

        return res

    def from_expense_to_invoice(self, values, mode):
        def create_invoice_line(account_id, name, price_unit, source_document, billable_expense_ids):
            # Create new invoice line from billable expense and add to this Invoice.
            aml_value = {
                'account_id': account_id,
                'name': name,
                'price_unit': price_unit,
                'quantity': 1,
                'invoice_billable_expenses_ids': billable_expense_ids
            }
            self.write({'invoice_line_ids': [(0, 0, aml_value)]})

        def update_billable_expense(expenses):
            invoice_id = self.invoice_line_ids.filtered(lambda r: r.invoice_billable_expenses_ids == expenses)
            expenses.sudo().write({'invoice_line_id': invoice_id.id})

        self.ensure_one()
        expense_ids = self.env['billable.expenses'].browse(values)
        account_id = expense_ids.get_expense_account()

        # Add multiple expenses to 1 line
        if mode == 'one':
            description = '\n'.join(expense.description for expense in expense_ids)
            amount = sum(expense.amount_currency for expense in expense_ids)
            source_list = expense_ids.mapped('source_document')
            source = ', '.join(source_list) if source_list else ''
            create_invoice_line(account_id, description, amount, source, [(6, 0, values)])
            update_billable_expense(expense_ids)

        elif mode == 'item':
            for expense in expense_ids:
                account_id = expense.get_expense_account() or account_id
                create_invoice_line(account_id, expense.description, expense.amount_currency, expense.source_document,
                                    [(4, expense.id)])

            # Cannot put update_billable_expense() after create_invoice_line() in the same loop.
            for expense in expense_ids:
                update_billable_expense(expense)

        return True


class AccountInvoiceLineUSA(models.Model):
    _inherit = 'account.move.line'

    move_type = fields.Selection(related='move_id.move_type')
    billable_expenses_ids = fields.One2many('billable.expenses', 'bill_line_id')  # only one record, for bill

    # maybe more than one record, multi expenses added as one line
    invoice_billable_expenses_ids = fields.Many2many('billable.expenses')
    invoiced_to_id = fields.Many2one('account.move', compute='_compute_invoice_to_id', store=True)
    is_billable = fields.Boolean('Billable expense', compute='_get_is_billable', store=True)
    billable_expense_customer_id = fields.Many2one('res.partner', 'Assigned Customer', store=True,
                                                   related='billable_expenses_ids.customer_id')

    @api.depends('billable_expenses_ids', 'billable_expenses_ids.customer_id',
                 'billable_expenses_ids.is_outstanding', 'move_id.state')
    def _compute_invoice_to_id(self):
        for record in self:
            invoiced_to_id = False
            if record.move_id.state == 'posted':
                if record.billable_expenses_ids and record.billable_expenses_ids[0].customer_id:
                    expense = record.billable_expenses_ids[0]
                    if not expense.is_outstanding:  # already invoiced
                        invoiced_to_id = expense.invoice_line_id.move_id
            record.invoiced_to_id = invoiced_to_id


    @api.depends('invoice_billable_expenses_ids')
    def _get_is_billable(self):
        for record in self:
            record.is_billable = True if record.invoice_billable_expenses_ids else False


    def open_invoice_expense(self):
        view_id = self.env.ref('account.view_move_form').id
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'target': 'current',
            'res_id': self.invoiced_to_id.id,
            'view_id': view_id,
        }
