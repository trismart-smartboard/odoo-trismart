# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PaymentDeposit(models.Model):
    _inherit = 'account.payment'

    property_account_customer_deposit_id = fields.Many2one('account.account', company_dependent=True, copy=True,
                                                           string='Customer Deposit Account',
                                                           domain=lambda self: [('user_type_id', 'in', [self.env.ref('account.data_account_type_current_liabilities').id]),
                                                                                ('deprecated', '=', False), ('reconcile', '=', True)])
    property_account_vendor_deposit_id = fields.Many2one('account.account', company_dependent=True, copy=True,
                                                         string='Vendor Deposit Account',
                                                         domain=lambda self: [('user_type_id', 'in', [self.env.ref('account.data_account_type_prepayments').id]),
                                                                              ('deprecated', '=', False), ('reconcile', '=', True)])
    deposit_ids = fields.Many2many('account.move', string='Deposit Entries')
    sale_deposit_id = fields.Many2one('sale.order', 'Sales Order',
                                      help='Is this deposit made for a particular Sale Order?')
    purchase_deposit_id = fields.Many2one('purchase.order', 'Purchase Order',
                                          help='Is this deposit made for a particular Purchase Order?')
    is_deposit = fields.Boolean('Is a Deposit?')

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('partner_id')
    def _update_default_deposit_account(self):
        """
        Change deposit account like deposit account of partner
        """
        if self.partner_id and self.is_deposit:
            if self.partner_id.property_account_customer_deposit_id and self.partner_type == 'customer':
                self.property_account_customer_deposit_id = self.partner_id.property_account_customer_deposit_id.id
            elif self.partner_id.property_account_vendor_deposit_id and self.partner_type == 'supplier':
                self.property_account_vendor_deposit_id = self.partner_id.property_account_vendor_deposit_id.id

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def action_post(self):
        """
        Override
        Check if total amount of deposits of an order has exceeded amount of this order
        """
        for record in self:
            if record.partner_type == 'customer':
                order = record.sale_deposit_id
                msg = 'Total deposit amount cannot exceed sales order amount'
            else:
                order = record.purchase_deposit_id
                msg = 'Total deposit amount cannot exceed purchase order amount'
            if order:
                deposit_total = record.amount_total_signed
                currency_date = record.partner_type == 'customer' and order.date_order or order.date_approve
                deposit_total = order.company_id.currency_id._convert(
                    deposit_total,
                    order.currency_id,
                    order.company_id,
                    currency_date or fields.Date.today()
                )
                if deposit_total > order.remaining_total:
                    raise ValidationError(_(msg))

        return super(PaymentDeposit, self).action_post()

    def action_draft(self):
        """
        Override
        Cancel, remove deposit from invoice and delete deposit moves
        """
        super(PaymentDeposit, self).action_draft()
        moves = self.mapped('deposit_ids')
        moves.filtered(lambda move: move.state == 'posted').button_draft()
        moves.with_context(force_delete=True).unlink()

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    def _onchange_partner_order_id(self, order_field, state):
        """
        Helper method: Get the domain of order field on deposit form according to partner
        """
        if self.partner_id:
            partner_id = self.partner_id.commercial_partner_id.id
            if self[order_field] and self[order_field].partner_id.commercial_partner_id.id != partner_id:
                self[order_field] = False
            return {
                'domain': {
                    order_field: [('partner_id.commercial_partner_id', '=', partner_id), ('state', 'in', state)]
                }
            }
        else:
            self[order_field] = False

    def _validate_order_id(self, order_field, model_name):
        """
        Helper method: Check if commercial partner of deposit is the same as the one of payment
        """
        for payment in self:
            partner_id = payment.partner_id.commercial_partner_id.id
            if payment[order_field] and payment[order_field].partner_id.commercial_partner_id.id != partner_id:
                raise ValidationError(_("The {}'s customer does not match with the deposit's.".format(model_name)))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    @api.model
    def create(self, values):
        """
        Override to add deposit move line like a write-off move line to JE of deposit payment
        """
        if values.get('is_deposit', False):
            account_id = values.get('property_account_customer_deposit_id') \
                         or values.get('property_account_vendor_deposit_id')
            values['write_off_line_vals'] = {
                'account_id': account_id,
                'amount': -values.get('amount', 0.0)
            }

        return super(PaymentDeposit, self).create(values)

    def _synchronize_to_moves(self, changed_fields):
        """
        Override to update move lines of deposit payment JE when changing fields on the deposit payment form
        """
        if self._context.get('skip_account_move_synchronization'):
            return

        deposit_payments = self.with_context(skip_account_move_synchronization=True).filtered(lambda x: x.is_deposit)
        if any(field in changed_fields for field in ['partner_id', 'partner_bank_id', 'date', 'payment_reference', 'amount', 'currency_id']):
            for payment in deposit_payments:
                liquidity_lines, counterpart_lines, other_lines = payment._seek_for_lines()
                other_line_vals = {
                    'name': other_lines[0].name,
                    'amount': -payment.amount,
                    'account_id': other_lines[0].account_id.id
                }
                line_vals_list = payment._prepare_move_line_default_vals(write_off_line_vals=other_line_vals)
                # Update write-off move line of JE of deposit
                line_ids_commands = [
                    (1, liquidity_lines.id, line_vals_list[0]),
                    (1, counterpart_lines.id, line_vals_list[1]),
                    (1, other_lines[0].id, line_vals_list[2]),
                ]
                payment.move_id.write({
                    'partner_id': payment.partner_id.id,
                    'currency_id': payment.currency_id.id,
                    'partner_bank_id': payment.partner_bank_id.id,
                    'line_ids': line_ids_commands
                })
            super(PaymentDeposit, self - deposit_payments)._synchronize_to_moves(changed_fields)
        else:
            super(PaymentDeposit, self)._synchronize_to_moves(changed_fields)
