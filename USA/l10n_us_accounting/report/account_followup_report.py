# -*- coding: utf-8 -*-
import json
import base64
import lxml

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools import append_content_to_html, config
from odoo.tools.misc import formatLang
from odoo.tools.translate import _


class FollowUpReportUSA(models.AbstractModel):
    _inherit = 'account.followup.report'

    @api.model
    def print_followups(self, records):
        res_ids = records['ids'] if 'ids' in records else records.ids
        for res_id in res_ids:
            self.env['res.partner'].browse(res_id).message_post(body=_('Follow-up letter printed'))
        return self.env.ref('account_followup.action_report_followup').report_action(res_ids)

    def _get_templates(self):
        """
        Override
        Change the header template of followup report
        """
        res = super(FollowUpReportUSA, self)._get_templates()
        res['main_table_header_template'] = 'l10n_us_accounting.usa_main_table_header_followup_report'
        return res

    def _get_columns_name(self, options):
        """
        Override
        Add title to header of first column
        """
        headers = super(FollowUpReportUSA, self)._get_columns_name(options)
        headers[0] = {'name': _('Transaction Name'), 'style': 'text-align:left; white-space:nowrap;'}
        return headers

    def get_html(self, options, line_id=None, additional_context=None):
        """
        Override
        Add overdue periods lines
        """
        if additional_context is None:
            additional_context = {}
        additional_context['summary_lines'] = self._get_summary_lines(options)
        return super(FollowUpReportUSA, self).get_html(options, line_id=line_id, additional_context=additional_context)

    def _get_summary_lines(self, options):
        partner = options.get('partner_id') and self.env['res.partner'].browse(options['partner_id']) or False
        if not partner:
            return []

        res = {}
        today = fields.Date.today()
        lines = []
        line_num = 0

        for l in partner.unreconciled_aml_ids.filtered(lambda l: l.company_id == self.env.company):
            if self.env.context.get('print_mode') and l.blocked:
                continue
            currency = l.currency_id or l.company_id.currency_id
            if currency not in res:
                res[currency] = []
            res[currency].append(l)

        for currency, aml_recs in res.items():
            values = {
                'not_due': [_('Not Due'), 0],
                '1_30': [_('1 - 30 Days Past Due'), 0],
                '31_60': [_('31 - 60 Days Past Due'), 0],
                '61_90': [_('61 - 90 Days Past Due'), 0],
                '91_120': [_('91 - 120 Days Past Due'), 0],
                '120+': [_('120+ Days Past Due'), 0],
                'total': [_('Total Amount'), 0]
            }

            for aml in filter(lambda r: not r.blocked, aml_recs):
                amount = aml.currency_id and aml.amount_residual_currency or aml.amount_residual
                date_maturity = aml.date_maturity or aml.date or today
                number_due_days = (fields.Date.today() - date_maturity).days

                values['total'][1] += amount
                if number_due_days < 1:
                    values['not_due'][1] += amount
                elif 0 < number_due_days < 31:
                    values['1_30'][1] += amount
                elif 30 < number_due_days < 61:
                    values['31_60'][1] += amount
                elif 60 < number_due_days < 91:
                    values['61_90'][1] += amount
                elif 90 < number_due_days < 121:
                    values['91_120'][1] += amount
                elif number_due_days > 120:
                    values['120+'][1] += amount

            values = self.format_values_report(values, currency)
            line_num += 1
            lines.append({
                'id': line_num,
                'name': '',
                'class': 'summary_values',
                'unfoldable': False,
                'level': 0,
                'columns': [values[key][1] for key in values]
            })

            # Add an empty line after the total to make a space between two currencies
            line_num += 1
            lines.append({
                'id': line_num,
                'name': '',
                'class': 'summary_values_empty_line',
                'unfoldable': False,
                'level': 0,
                'columns': ['' for key in values]
            })

        # Remove the last empty line
        if lines:
            lines.pop()

        return lines

    def format_values_report(self, values, currency):
        for key in values:
            values[key][1] = formatLang(self.env, values[key][1], currency_obj=currency)
        return values
