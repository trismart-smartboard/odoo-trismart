# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CustomerUSA(models.Model):
    _inherit = 'res.partner'

    ar_in_charge = fields.Many2one(string='AR In Charge', comodel_name='res.users', domain=[('share', '=', False)])
    print_check_as = fields.Boolean('Print on check as',
                                    help='Check this box if you want to use a different name on checks.')
    check_name = fields.Char('Name on Check')
    usa_partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor'), ('both', 'Both')],
                                        string='Partner Type')
    vendor_eligible_1099 = fields.Boolean(string='Vendor Eligible for 1099', default=False)

    # Odoo already has unreconciled_aml_ids in account_followup for AR.
    unreconciled_payable_aml_ids = fields.One2many('account.move.line', 'partner_id',
                                                   domain=[('reconciled', '=', False),
                                                           ('account_id.deprecated', '=', False),
                                                           ('account_id.internal_type', '=', 'payable'),
                                                           ('move_id.state', '=', 'posted')])

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    def _update_usa_partner_type(self):
        if self.ids:
            query = """
            UPDATE res_partner SET usa_partner_type =
                CASE
                    WHEN supplier_rank > 0 AND customer_rank > 0 THEN 'both'
                    WHEN supplier_rank > 0 AND customer_rank <= 0 THEN 'supplier'
                    WHEN supplier_rank <= 0 AND customer_rank > 0 THEN 'customer'
                    ELSE NULL
                END
            WHERE id IN %(partner_ids)s
            """
            self.env.cr.execute(query, {'partner_ids': tuple(self.ids)})

    def _increase_rank(self, field, n=1):
        super(CustomerUSA, self)._increase_rank(field, n)
        self._update_usa_partner_type()

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('print_check_as')
    def _onchange_print_check_as(self):
        for record in self:
            record.check_name = record.name

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        res = super(CustomerUSA, self).create(vals_list)

        # Update usa_partner_type (Customer/Vendor/Both) after super()
        if vals_list and ('customer_rank' in vals_list[0] or 'supplier_rank' in vals_list[0]):
            res._update_usa_partner_type()

        return res

    def write(self, vals):
        res = super(CustomerUSA, self).write(vals)
        if 'ar_in_charge' in vals:
            for partner in self:
                if partner.child_ids:
                    partner.child_ids.write({'ar_in_charge': partner.ar_in_charge})
        return res

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------



