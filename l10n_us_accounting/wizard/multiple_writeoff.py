from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.tools import float_compare
from ..utils.writeoff_utils import write_off
import logging

_logger = logging.getLogger(__name__)


class MultipleWriteOffWizard(models.TransientModel):
    _name = "multiple.writeoff.wizard"
    _description = "Create Write-off for multiple invoices/bills"

    def _default_move_type(self):
        return self._context.get('default_move_type')

    def get_selected_moves(self):
        active_ids = self.env.context.get('active_ids')
        account_move_ids = self.env['account.move'].browse(active_ids)
        val_lst = []
        for move_id in account_move_ids:
            if self._check_state(move_id):
                val_lst.append(move_id)
        if not len(val_lst):
            raise ValidationError('There is nothing left to create write-offs.')

        return [(0, 0, {'move_id': move_id.id}) for move_id in val_lst]

    move_ids = fields.One2many("multiple.writeoff.wizard.line", "writeoff_wizard_id", default=get_selected_moves)
    move_type = fields.Char(default=_default_move_type)

    def action_write_off(self):

        is_apply = self.env.context.get('create_and_apply', False)

        refund_list = []
        for form in self:
            for wizard_line in form.move_ids:
                inv = wizard_line.move_id
                refund_list.append(write_off(inv, wizard_line, is_apply).id)

        return {
            'name': _('Created Write-offs'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', refund_list)],
        }

    @staticmethod
    def _check_state(move_id):
        return not (move_id.state != 'posted' or float_compare(move_id.amount_residual, 0, precision_rounding=move_id.currency_id.rounding) <= 0)


class MultipleWriteOffWizardLine(models.TransientModel):
    _name = "multiple.writeoff.wizard.line"

    def _default_bad_debt_account_id(self):
        company_id = self.company_id
        return company_id.bad_debt_account_id.id \
            if company_id.bad_debt_account_id and self.move_id.move_type == "out_invoice" else (company_id.bill_bad_debt_account_id.id \
            if company_id.bill_bad_debt_account_id else False)

    writeoff_wizard_id = fields.Many2one("multiple.writeoff.wizard")
    move_id = fields.Many2one("account.move", string="Bill/Invoice", ondelete="cascade")
    name = fields.Char(string='Number', related="move_id.name")
    invoice_origin = fields.Char(string="Source Document", related="move_id.invoice_origin")
    invoice_date = fields.Date(string='Bill/Invoice Date', related="move_id.invoice_date")
    invoice_date_due = fields.Date(string='Due Date', related="move_id.invoice_date_due")
    amount_total = fields.Monetary(string='Total', related="move_id.amount_total",
                                   currency_field='currency_id')
    amount_residual = fields.Monetary(string='Amount Due', related="move_id.amount_residual",
                                      currency_field='currency_id')
    company_id = fields.Many2one('res.company', 'Company', related="move_id.company_id")
    currency_id = fields.Many2one('res.currency', 'Currency', related="move_id.currency_id")
    account_id = fields.Many2one("account.account", string='Write-off Account',
                                         default=_default_bad_debt_account_id,
                                         domain=[('deprecated', '=', False)])
    reason = fields.Char(string='Reason')
    date = fields.Date(string='Write-off Date', default=fields.Date.context_today)
    discount_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Amount Due')
    ], default='fixed', required=True, string='Discount Type')
    value = fields.Float("Value", default=lambda self: self.amount_residual)
    write_off_amount = fields.Monetary("Discount Amount",
                                      currency_field='currency_id', compute='_compute_discount_amount', readonly=True, required=True)

    @api.onchange('discount_type')
    def _onchange_value(self):
        for rec in self:
            rec.value = 100.0 if rec.discount_type == 'percentage' else rec.amount_residual

    @api.depends('value')
    def _compute_discount_amount(self):
        for rec in self:
            amount = rec.amount_residual * rec.value / 100.0 if rec.discount_type == 'percentage' else rec.value
            if rec._check_value(amount, rec.amount_residual, rec.currency_id.rounding):
                rec.write_off_amount = amount
            else:
                raise ValidationError('Discount Amount must be positive and cannot be bigger than Amount Due.')

    @staticmethod
    def _check_value(amount, amount_residual, rounding):
        if float_compare(amount, 0, precision_rounding=rounding) <= 0 or float_compare(amount, amount_residual,
                                                                                       precision_rounding=rounding) > 0:
            result = False
        else:
            result = True
        return result
