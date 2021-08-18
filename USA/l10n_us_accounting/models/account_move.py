# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMoveUSA(models.Model):
    _inherit = 'account.move'

    ar_in_charge = fields.Many2one(string='AR In Charge', comodel_name='res.users', domain=[('share', '=', False)])
    batch_fund_line_id = fields.Many2one('account.batch.deposit.fund.line', string='Batch Payment - Adjustment line')
    is_line_readonly = fields.Boolean("Readonly Journal Lines?", compute='_compute_is_line_readonly', store=True)
    is_payment_receipt = fields.Boolean('Is Payment Receipt?', related='payment_id.is_payment_receipt')

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @staticmethod
    def _build_invoice_line_item(write_off_amount, account_id, line_ids, reconcile_account_id, reverse_type):
        new_invoice_line_ids = {}
        if line_ids:
            debit_wo, credit_wo = (0, write_off_amount) if reverse_type == 'in_refund' else (write_off_amount, 0)

            new_invoice_line_ids = {
                'name': 'Write Off',
                'display_name': 'Write Off',
                'product_uom_id': False,
                'account_id': account_id,
                'quantity': 1.0,
                'price_unit': write_off_amount,
                'product_id': False,
                'discount': 0.0,
                'debit': debit_wo,
                'credit': credit_wo
            }
        return [(0, 0, new_invoice_line_ids)]

    def _get_reconciled_info_JSON_values(self):
        """
        Override
        Add label of applied transactions to dict values to show in payment widget on invoice form
        """
        reconciled_vals = super(AccountMoveUSA, self)._get_reconciled_info_JSON_values()

        for val in reconciled_vals:
            move_id = self.browse(val.get('move_id'))
            if val.get('account_payment_id'):
                val['trans_label'] = move_id.journal_id.code
            elif move_id.move_type in ['out_refund', 'in_refund']:
                val['trans_label'] = 'Credit Note'

        return reconciled_vals

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('batch_fund_line_id', 'is_payment_receipt')
    def _compute_is_line_readonly(self):
        for record in self:
            if record.batch_fund_line_id or record.is_payment_receipt:
                record.is_line_readonly = True
            else:
                record.is_line_readonly = False

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('partner_id')
    def _onchange_select_customer(self):
        self.ar_in_charge = self.partner_id.ar_in_charge

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def button_draft_usa(self):
        self.ensure_one()
        action = self.env.ref('l10n_us_accounting.action_view_button_set_to_draft_message').read()[0]
        action['context'] = isinstance(action.get('context', {}), dict) or {}
        action['context']['default_move_id'] = self.id
        return action

    def create_refund(self, write_off_amount, company_currency_id, account_id, invoice_date=None, description=None,
                      journal_id=None):
        new_invoices = self.browse()
        for invoice in self:
            # Copy from Odoo
            reverse_type_map = {
                'entry': 'entry',
                'out_invoice': 'out_refund',
                'out_refund': 'entry',
                'in_invoice': 'in_refund',
                'in_refund': 'entry',
                'out_receipt': 'entry',
                'in_receipt': 'entry',
            }
            reconcile_account_id = invoice.partner_id.property_account_receivable_id \
                if invoice.is_sale_document(include_receipts=True) else invoice.partner_id.property_account_payable_id
            reverse_type = reverse_type_map[invoice.move_type]

            default_values = {
                'ref': description,
                'date': invoice_date,
                'invoice_date': invoice_date,
                'invoice_date_due': invoice_date,
                'journal_id': journal_id,
                'invoice_payment_term_id': None,
                'move_type': reverse_type,
                'invoice_origin': invoice.name,
                'state': 'draft'
            }
            values = invoice._reverse_move_vals(default_values, False)

            line_ids = values.pop('line_ids')
            if 'invoice_line_ids' in values:
                values.pop('invoice_line_ids')
            new_invoice_line_ids = self._build_invoice_line_item(abs(write_off_amount), account_id.id, line_ids, reconcile_account_id, reverse_type)

            refund_invoice = self.create(values)
            refund_invoice.write({'invoice_line_ids': new_invoice_line_ids})

            # Create message post
            message = 'This write off was created from ' \
                      '<a href=# data-oe-model=account.move data-oe-id={}>{}</a>'.format(invoice.id, invoice.name)
            refund_invoice.message_post(body=message)

            new_invoices += refund_invoice
        return new_invoices

    def action_open_popup(self):
        return {
            'name': _('Create Write-off'),
            'res_model': 'multiple.writeoff.wizard',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
                'default_move_type': self[0].move_type
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
