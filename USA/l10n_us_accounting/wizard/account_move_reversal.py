# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError,ValidationError
from ..utils.writeoff_utils import write_off

class AccountMoveWriteOff(models.TransientModel):
    """
    Account move write-off wizard.
    """
    _name = 'account.invoice.refund.usa'
    _description = 'Write Off An Account'

    def _default_write_off_amount(self):
        inv_obj = self.env['account.move']
        context = dict(self._context or {})
        for inv in inv_obj.browse(context.get('active_ids')):
            self._validate_state(inv.state)
            return inv.amount_residual
        return 0.0

    def _default_bad_debt_account_id(self):
        return self.env.user.company_id.bad_debt_account_id.id \
            if self.env.user.company_id.bad_debt_account_id else False

    write_off_amount = fields.Monetary(string='Write Off Amount', default=_default_write_off_amount,
                                       currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', readonly=True,
                                          default=lambda self: self.env['account.move'].browse(self._context.get('active_id')).currency_id)
    account_id = fields.Many2one("account.account", string='Account', required=True, default=_default_bad_debt_account_id,
                                 domain=[('deprecated', '=', False)])
    company_id = fields.Many2one('res.company', string='Company', change_default=True, readonly=True,
                                 default=lambda self: self.env['res.company']._company_default_get('account.move'))
    reason = fields.Char(string='Reason')
    date = fields.Date(string='Write-off date', default=fields.Date.context_today)
    @api.constrains('write_off_amount')
    def _check_write_off_amount(self):
        for record in self:
            if record.write_off_amount <= 0:
                raise ValidationError(_('Amount must be greater than 0.'))

    def action_write_off(self):
        inv_obj = self.env['account.move']
        context = dict(self._context or {})
        is_apply = self.env.context.get('create_and_apply', False)

        refund_list = []
        for form in self:
            for inv in inv_obj.browse(context.get('active_ids')):
                self._validate_state(inv.state)
                refund_list.append(write_off(inv, form, is_apply))

        return self.view_in_edit_mode(refund_list)

    def view_in_edit_mode(self, refund_list):
        action = self.env.ref('account.action_move_out_refund_type')
        result = action.read()[0]

        if not refund_list:
            return True
        else:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = refund_list[0].id
            result['flags'] = {'mode': 'edit'}
        return result

    @staticmethod
    def _validate_state(state):
        if state in ['draft', 'cancel']:
            raise UserError('Cannot create write off an account for the draft/cancelled invoice.')