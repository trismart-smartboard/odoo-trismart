from odoo import fields, api, models, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero, float_compare

TIME_DICT = {
    'daily': 'days',
    'weekly': 'weeks',
    'monthly': 'months',
    'yearly': 'years'
}


class RecurringTransaction(models.Model):
    _name = 'recurring.transaction'
    _description = 'Recurring Transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Template field
    name = fields.Char(string='Number', required=True, copy=False, default=lambda self: _('Draft'))
    transaction_type = fields.Selection([('manual_journal_entry', 'Manual Journal Entry'),
                                         ('customer_invoice', 'Customer Invoice'),
                                         ('vendor_bill', 'Vendor Bill'),
                                         ('customer_payment', 'Customer Payment'),
                                         ('bill_payment', 'Bill Payment')], string='Transaction Type',
                                        default='manual_journal_entry', tracking=True)
    create_transaction_as = fields.Selection([('draft', 'Draft'), ('posted', 'Posted')],
                                             string='Create Transaction as', default='draft', tracking=True, required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
    ], string='Status', default='draft', index=True, readonly=True)
    recurring_interval = fields.Integer(string='Period', help="Repeat every (Days/Week/Month/Year)", tracking=True)
    recurring_rule_type = fields.Selection([('daily', 'Days'), ('weekly', 'Weeks'),
                                            ('monthly', 'Months'), ('yearly', 'Years'), ],
                                           string='Recurrence', required=True,
                                           help="Transaction automatically repeat at specified interval",
                                           default='monthly', tracking=True)
    recurring_rule_boundary = fields.Selection([
        ('unlimited', 'Forever'),
        ('limited', 'Fixed')
    ], string='Duration', default='unlimited', tracking=True)
    recurring_rule_count = fields.Integer(string="End After", default=1, required=True, tracking=True)
    start_date = fields.Date('Start Date', default=lambda self: datetime.today(), tracking=True)
    end_date = fields.Date('End Date', compute='_compute_last_transaction_date', store=True)

    next_transaction_date = fields.Date('Next Transaction Date', readonly=True,
                                        compute='_compute_next_transaction_date', store=True)
    # Transaction field
    journal_entry_ids = fields.One2many('account.move', 'recurring_transaction_id', copy=False)
    transaction_count = fields.Integer('Number of transactions created', compute='_compute_created_transactions',
                                       store=True)

    journal_id = fields.Many2one('account.journal', string='Journal', tracking=True, required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', index=True,
        default=lambda self: self.env.company)
    ref = fields.Char('Reference', tracking=True, copy=False)
    line_ids = fields.One2many('recurring.transaction.line', 'move_id', string='Journal Items',
                               states={'draft': [('readonly', False)]}, copy=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,

                                  default=lambda self: self.env.company.currency_id, tracking=True)
    partner_id = fields.Many2one('res.partner', 'Partner')

    # fields for Customer/Vendor Payments
    payment_type = fields.Selection([
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
    ], string='Payment Type', default='inbound', required=True)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], default='customer', required=True)
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method',
                                        domain="[('id', 'in', available_payment_method_ids)]")
    available_payment_method_ids = fields.Many2many('account.payment.method',
                                                    compute='_compute_payment_method_fields')

    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True,
        compute='_compute_destination_account_id',
        domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
        check_company=True)
    amount = fields.Monetary('Amount',currency_field='currency_id')

    ########################################################
    # BUILT_IN METHODS
    ########################################################
    @api.model
    def create(self, vals):
        res = super().create(vals)
        if 'line_ids' in vals:
            res.check_balanced()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'line_ids' in vals:
            self.check_balanced()
        return res

    def unlink(self):
        if any(template.state in ['confirm','done'] for template in self):
            raise UserError(_('You cannot delete confirmed/done recurring transaction templates.'))
        return super().unlink()

    ########################################################
    # ACTION METHODS
    ########################################################
    def action_created_transactions(self):
        action_id = "account.action_account_payments" if self.transaction_type in ['customer_payment','bill_payment'] else "account.action_move_journal_line"
        action = self.env["ir.actions.actions"]._for_xml_id(action_id)
        action['display_name'] = _('Transactions')
        action['context'] = {}
        action['domain'] = [('recurring_transaction_id', '=', self.id)]
        return action

    def action_draft(self):
        self.unlink_created_transactions()
        self.write(
            {'state': 'draft',
             'next_transaction_date': datetime.today()}
        )

    def action_confirm(self):
        self.check_start_date()
        for template in self:
            if template.transaction_type not in ['customer_payment','bill_payment']:
                if len(template.line_ids) == 0:
                    raise ValidationError(_('You need to add a line before posting.'))
            elif float_compare(template.amount, 0, precision_rounding=template.currency_id.rounding) <= 0:
                raise ValidationError(_('Payment Amount must be greater than 0.'))
            if not template.name.startswith("RTT/"):
                template.name = self.env['ir.sequence'].sudo().next_by_code('recurring_transaction')

        self.write(
            {'state': 'confirm'}
        )

    ########################################################
    # CONSTRAINS AND ON_CHANGE METHODS
    ########################################################

    @api.constrains('recurring_interval', 'recurring_rule_count')
    def _check_recurring_interval_or_recurring_rule_count(self):
        for record in self:
            if record.recurring_interval <= 0 or record.recurring_rule_count <= 0:
                validate_field = 'Period' if record.recurring_interval <= 0 else 'Duration'
                raise ValidationError(_(f'{validate_field} must be positive'))

    def unlink_created_transactions(self):
        for record in self:
            if record.journal_entry_ids:
                record.journal_entry_ids = [(6, 0, [])]

    def check_start_date(self):
        for record in self:
            current_date = date.today()
            if record.start_date < current_date:
                raise ValidationError(_('Start date must not be date in the past'))

    def check_balanced(self):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        line_ids = self.line_ids
        credit = sum([line.credit for line in line_ids])
        debit = sum([line.debit for line in line_ids])
        if not float_is_zero(debit - credit, precision_digits=2):
            raise UserError(
                _(f"Cannot create unbalanced journal entry. Differences debit - credit: {debit} - {credit}"))

    ########################################################
    # COMPUTE METHODS
    ########################################################

    @api.depends('journal_entry_ids')
    def _compute_created_transactions(self):
        for template in self:
            template.transaction_count = len(template.journal_entry_ids)

    @api.depends('start_date', 'recurring_rule_type', 'recurring_interval')
    def _compute_next_transaction_date(self):
        for rec in self:
            rec.next_transaction_date = rec.start_date

    @api.depends('start_date', 'recurring_rule_type', 'recurring_interval', 'recurring_rule_count')
    def _compute_last_transaction_date(self):
        for rec in self:
            rec.end_date = rec.start_date + relativedelta(**{
                TIME_DICT[
                    self.recurring_rule_type]: self.recurring_rule_count * self.recurring_interval})


    @api.onchange('recurring_rule_boundary')
    def _onchange_recurring_rule_boundary(self):
        for rec in self:
            rec.recurring_rule_count = 1

    @api.onchange('transaction_type')
    def _onchange_transaction_type(self):
        journal = self.env['account.journal']
        for template in self:
            # clear
            template.partner_id = False
            template.ref = ''
            template.line_ids = [(6, 0, [])]

            if template.transaction_type == 'manual_journal_entry':
                template.journal_id = False
            elif template.transaction_type == 'customer_invoice':
                template.journal_id = journal.search(
                    [('type', '=', 'sale'), ('company_id', '=', template.company_id.id)], limit=1)
            elif template.transaction_type == 'vendor_bill':
                template.journal_id = journal.search(
                    [('type', '=', 'purchase'), ('company_id', '=', template.company_id.id)], limit=1)
            else:
                template.journal_id = journal.search(
                    [('type', 'in',['bank','cash']), ('company_id', '=', template.company_id.id)], limit=1)
                if template.transaction_type == 'customer_payment':
                    template.payment_type = 'inbound'
                    template.partner_type = 'customer'
                else:
                    template.payment_type = 'outbound'
                    template.partner_type = 'supplier'

    @api.onchange('payment_type', 'journal_id')
    def _onchange_payment_method_id(self):
        ''' Compute the 'payment_method_id' field.
        This field is not computed in '_compute_payment_method_fields' because it's a stored editable one.
        '''
        for template in self:
            if template.transaction_type in ['customer_payment','bill_payment']:
                if template.payment_type == 'inbound':
                    available_payment_methods = template.journal_id.inbound_payment_method_ids
                else:
                    available_payment_methods = template.journal_id.outbound_payment_method_ids

                # Select the first available one by default.
                if available_payment_methods:
                    template.payment_method_id = available_payment_methods[0]._origin
                else:
                    template.payment_method_id = False

    @api.depends('payment_type',
                 'journal_id.inbound_payment_method_ids',
                 'journal_id.outbound_payment_method_ids')
    def _compute_payment_method_fields(self):
        for template in self:
            if template.payment_type == 'inbound':
                template.available_payment_method_ids = template.journal_id.inbound_payment_method_ids
            else:
                template.available_payment_method_ids = template.journal_id.outbound_payment_method_ids

    @api.depends('journal_id', 'partner_id', 'partner_type')
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        for template in self:
            if template.transaction_type in ['customer_payment', 'bill_payment']:
                if template.partner_type == 'customer':
                    # Receive money from invoice or send money to refund it.
                    if template.partner_id:
                        template.destination_account_id = template.partner_id.with_company(
                            template.company_id).property_account_receivable_id
                    else:
                        template.destination_account_id = self.env['account.account'].search([
                            ('company_id', '=', template.company_id.id),
                            ('internal_type', '=', 'receivable'),
                        ], limit=1)
                elif template.partner_type == 'supplier':
                    # Send money to pay a bill or receive money to refund it.
                    if template.partner_id:
                        template.destination_account_id = template.partner_id.with_company(template.company_id).property_account_payable_id
                    else:
                        template.destination_account_id = self.env['account.account'].search([
                            ('company_id', '=', template.company_id.id),
                            ('internal_type', '=', 'payable'),
                        ], limit=1)

    ########################################################
    # CRON JOB METHODS
    ########################################################

    @api.model
    def _cron_recurring_create_transaction(self):
        for template in self.search([('state', '=', 'confirm')]):
            current_date = date.today()
            next_transaction_day = template.next_transaction_date
            line_ids = template.line_ids

            if current_date >= next_transaction_day:
                transaction_type = template.transaction_type
                vals = {
                    'company_id': template.company_id.id,
                    'currency_id': template.currency_id.id,
                    'journal_id': template.journal_id.id,
                    'date': current_date,
                    'recurring_transaction_id': template.id,
                }
                if transaction_type == 'manual_journal_entry':
                    vals.update({
                        'ref': template.ref,
                        'move_type': 'entry',
                        'line_ids': list(map(lambda line: (0, 0, {'partner_id': line.partner_id.id,
                                                                     'analytic_account_id': line.analytic_account_id.id,
                                                                     'analytic_tag_ids': line.analytic_tag_ids,
                                                                     'tax_ids': line.tax_ids,
                                                                     'account_id': line.account_id.id,
                                                                     'debit': line.debit,
                                                                     'credit': line.credit,
                                                                     'name': line.name
                                                                     }), line_ids)),
                    })
                    model = 'account.move'

                elif transaction_type in ['customer_invoice', 'vendor_bill']:
                    if transaction_type == 'customer_invoice':
                        payment_term_id = template.partner_id.property_payment_term_id.id
                        extra = _("")
                        move_type = 'out_invoice'
                    else:
                        payment_term_id = template.partner_id.property_supplier_payment_term_id.id
                        extra = _(" (%s, %s)") % (template.name, str(fields.Datetime.now()))
                        move_type = 'in_invoice'
                    vals.update({
                        'ref': (template.ref + extra) if template.ref else None,
                        'invoice_date': current_date,
                        'invoice_payment_term_id': payment_term_id,
                        'partner_id': template.partner_id.id,
                        'move_type': move_type,
                        'invoice_line_ids': list(map(lambda line: (0, 0, {'product_id': line.product_id.id,
                                                                             'analytic_account_id': line.analytic_account_id.id,
                                                                             'analytic_tag_ids': line.analytic_tag_ids,
                                                                             'tax_ids': line.tax_ids,
                                                                             'quantity': line.quantity,
                                                                             'account_id': line.account_id,
                                                                             'price_unit': line.price_unit,
                                                                             'name': line.name,
                                                                             }), line_ids)),
                    })
                    model = 'account.move'
                else:
                    vals.update({
                        'ref': template.ref,
                        'destination_account_id': template.destination_account_id.id,
                        'payment_method_id': template.payment_method_id.id,
                        'payment_type': template.payment_type,
                        'partner_type': template.partner_type,
                        'partner_id': template.partner_id.id,
                        'amount': template.amount,
                    })
                    model = 'account.payment'
                new_account_move = self.env[model].create(vals)
                if template.create_transaction_as == 'posted':
                    new_account_move.write({'state': 'posted'})
                msg = 'This transaction has been created from Recurring Transaction Template ' \
                      '<a href=# data-oe-model=recurring.transaction data-oe-id={}>{}</a>'.format(template.id, template.name)
                new_account_move.message_post(body=msg)
                interval = template.recurring_interval if template.recurring_interval else 0
                recurring_type = template.recurring_rule_type
                timedelta_param = {TIME_DICT[recurring_type]: interval}
                template.next_transaction_date = template.next_transaction_date + relativedelta(**timedelta_param)
                if template.recurring_rule_boundary == 'limited' and template.next_transaction_date >= template.end_date:
                    template.state = 'done'


class TransactionLine(models.Model):
    _name = "recurring.transaction.line"
    _description = "Recurring Transaction Line"

    name = fields.Char('Label')
    account_id = fields.Many2one('account.account', string='Account', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner')
    move_id = fields.Many2one('recurring.transaction', 'Transaction')
    currency_id = fields.Many2one('res.currency', related='move_id.currency_id')
    company_id = fields.Many2one('res.company', related='move_id.company_id')
    debit = fields.Monetary(string='Debit', default=0.0, currency_field='currency_id')
    credit = fields.Monetary(string='Credit', default=0.0, currency_field='currency_id')
    transaction_type = fields.Selection(related='move_id.transaction_type')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity',
                            default=1.0, digits='Product Unit of Measure')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    tax_ids = fields.Many2many('account.tax', string='Taxes', check_company=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', check_company=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags', check_company=True)
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', digits='Account', store=True)
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], default=False, help="Technical field for UX purpose.")

    @api.onchange('product_id')
    def _onchange_product(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            line.name = line._get_computed_name()
            line.account_id = line._get_computed_account()

    @api.depends('quantity', 'price_unit')
    def _compute_amount(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue
            if float_compare(line.quantity, 0, precision_rounding=line.product_id.uom_id.rounding) <= 0:
                raise ValidationError(_('Quantity must be positive.'))
            if float_compare(line.price_unit, 0, precision_rounding=line.move_id.currency_id.rounding) < 0:
                raise ValidationError(_('Unit Price must not be negative.'))
            line.price_subtotal = line.quantity*line.price_unit

    def _get_computed_name(self):
        self.ensure_one()
        if not self.product_id:
            return ''

        product = self.product_id
        values = []
        if product.partner_ref:
            values.append(product.partner_ref)
        if self.transaction_type == 'customer_invoice' and product.description_sale:
            values.append(product.description_sale)
        elif self.transaction_type == 'vendor_bill' and product.description_purchase:
            values.append(product.description_purchase)
        return '\n'.join(values)

    def _get_computed_account(self):
        self.ensure_one()
        self = self.with_company(self.company_id)
        if not self.product_id:
            return

        accounts = self.product_id.product_tmpl_id.get_product_accounts()
        if self.transaction_type == 'customer_invoice':
            return accounts['income'] or self.account_id
        elif self.transaction_type == 'vendor_bill':
            return accounts['expense'] or self.account_id

