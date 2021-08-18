# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import numbers
import base64
from datetime import datetime
import logging

from odoo import api, models, fields, tools, modules, _
from odoo.addons.account_reports.models.formula import FormulaSolver
from odoo.tools.safe_eval import safe_eval
from odoo.tools.float_utils import float_compare

from ..utils.utils import format_percentage, get_eval_context, get_short_currency_amount, format_currency
from ..utils.time_utils import BY_DAY, BY_WEEK, BY_MONTH, BY_QUARTER, BY_YEAR, BY_YTD, \
    get_start_end_date_value_with_delta

_logger = logging.getLogger(__name__)

DEFAULT_SYMBOL = '-'

PERCENTAGE = 'percentage'
CURRENCY = 'currency'

periods_type = [
    (BY_DAY, 'Daily'),
    (BY_WEEK, 'Weekly'),
    (BY_MONTH, 'Monthly'),
    (BY_QUARTER, 'Quarterly'),
    (BY_YEAR, 'Yearly'),
    (BY_YTD, 'Year To Date')
]

units_type = [
    (PERCENTAGE, 'Percentage'),
    (CURRENCY, 'Currency'),
]


class KPIJournal(models.Model):
    _name = "kpi.journal"
    _description = "KPI journal"

    def _get_default_image(self, module, path, name):
        image_path = modules.get_module_resource(module, path, name)
        return tools.image_process(base64.b64encode(open(image_path, 'rb').read()), size=(1024, 1024))

    name = fields.Char('KPI Name')
    selected = fields.Boolean('KPI will appear', default=False)
    data = fields.Char('Json render', default='')
    order = fields.Integer('Order position', default=-1)
    color = fields.Char(default='#9fc5f8')
    icon_kpi = fields.Binary('Icon KPI', attachment=True,
                             default=lambda self: self._get_default_image('account_dashboard', 'static/src/img',
                                                                          'default_icon.png'))
    period_type = fields.Selection(periods_type, default=BY_YTD)
    code_compute = fields.Char(default="result = 0")
    unit = fields.Selection(units_type, default=CURRENCY)
    default_kpi = fields.Boolean("Is Default KPI", default=False)
    green_on_positive = fields.Boolean(string='Is growth good when positive?', default=True)

    ########################################################
    # GENERAL FUNCTION
    ########################################################
    @api.model
    def kpi_render(self, kpis_info):
        """ Function get the Json to render the kpi header with each kpi was
        showed at head and the data will render to setting kpi view
        :param kpis_info: type "personalized.kpi.info"
        :return:

        Workflow:
        User click on Company Insight to see personalized KPI views
        -> Load demo data of personalized KPI in JS code (loadDemo() method in kpi_header.js)
        -> kpi_header_render() in personalized KPI model -> kpi_render()
        """
        kpi_data = {}
        kpi_content = self.get_kpi_content_render(kpis_info)
        kpi_info = self.get_kpi_info(kpis_info)
        kpi_data['kpi_data'] = kpi_content
        kpi_data['kpi_info'] = kpi_info

        return kpi_data

    def get_kpi_content_render(self, kpis_info):
        """ Function return the JSON to render the kpi header content
        :return:

        Workflow:
        User click on Company Insight to see personalized KPI views
        -> Load demo data of personalized KPI in JS code (loadDemo() method in kpi_header.js)
        -> kpi_header_render() in personalized KPI model -> kpi_render() in general KPI
        -> render content of kpi (this)
        """
        kpi_render = []
        # Select all kpi have been chosen and render it to header
        kpis = kpis_info.filtered('selected').sorted('order')
        dict_context = get_eval_context(self, 'kpi.journal')

        # Dictionary have structure with key is the range time and the value is the normal
        # dict_line defined in FormularLine class. dict_line is a dictionary with key is
        # code of a group and value is tuple value (balance, credit, debit)
        dict_lines_data = {}

        for kpi in kpis:
            kpi_value = self.get_data_kpi_render(kpi, dict_context, dict_lines_data)
            if kpi_value:
                kpi_render.append(kpi_value)
        return kpi_render

    def get_kpi_info(self, kpis_info):
        """
        This function gets kpi_info including list of kpi to select to check or uncheck
        to render in kpi manage settings.
        :param kpis_info:
        :return: dictionary of list of KPIs and shown KPIs.
        Workflow:
        User click on Company Insight to see personalized KPI views
        -> Load demo data of personalized KPI in JS code (loadDemo() method in kpi_header.js)
        -> kpi_header_render() in personalized KPI model -> kpi_render() in general KPI
        -> render info of kpi -> _render_kpi_manage in js to update kpi manage in dashboard
        """
        kpi_selections = []
        selected_kpis_name = []
        sorted_kpis = kpis_info.sorted('order')
        for kpi in sorted_kpis:
            kpi_selections.append({'name': kpi.kpi_id.name, 'selected': kpi.selected})
            if kpi.selected:
                selected_kpis_name.append(kpi.kpi_id.name)
        return {'kpi_selections': kpi_selections,
                'kpi_selected': selected_kpis_name}

    ########################################################
    # KPI GENERATOR
    ########################################################
    def get_data_kpi_render(self, info, dict_context, dict_lines_data):
        """ Function support return the dictionary is the data to render a kpi item
        that contain the data in 'info' variable
        :param dict_lines_data:
        :param dict_context:
        :param info:
        :return:

         Workflow:
        User click on Company Insight to see personalized KPI views
        -> Load demo data of personalized KPI in JS code (loadDemo() method in kpi_header.js)
        -> kpi_header_render() in personalized KPI model -> kpi_render() in general KPI
        -> render content of kpi -> get_data_kpi_render
        """

        kpi_info_detail = info.kpi_id

        # append current time range to dict_context
        self.append_data_follow_range_time(dict_context, kpi_info_detail.period_type, delta_periods=0,
                                           lines_dict=dict_lines_data)
        comparison = ''
        comparison_title = ''
        trend = ''

        try:
            safe_eval(kpi_info_detail.code_compute, dict_context, mode="exec", nocopy=True)
            value = dict_context.get('result', DEFAULT_SYMBOL) + 0

            formatted_value, short_title = self.format_number_type(value, kpi_info_detail.unit)

            # PROGRESS FOR PREVIOUS PERIOD
            # append range time of previous period
            self.append_data_follow_range_time(dict_context, kpi_info_detail.period_type, delta_periods=-1,
                                               lines_dict=dict_lines_data)

            # compute result for previous period
            safe_eval(kpi_info_detail.code_compute, dict_context, mode="exec", nocopy=True)
            previous_period_value = dict_context.get('result', DEFAULT_SYMBOL) + 0
            if isinstance(previous_period_value, numbers.Number):
                minus_value = value - previous_period_value
                formatted_minus_value, short_minus_title = self.format_number_type(minus_value, kpi_info_detail.unit)
                comparison += short_minus_title + _(' vs prior period')
                comparison_title += formatted_minus_value + _(' vs prior period')

                if float_compare(minus_value, 0, precision_rounding=2) > 0:
                    icon = kpi_info_detail.green_on_positive and 'up_green' or 'up_red'
                elif float_compare(minus_value, 0, precision_rounding=2) < 0:
                    icon = kpi_info_detail.green_on_positive and 'down_red' or 'down_green'
                else:
                    icon = 'no_change'

                trend = '/account_dashboard/static/src/img/{}.png'.format(icon)
        except:
            formatted_value = '-'
            short_title = '-'
            _logger.warning("Parse Fail!")

        kpi_data_render = {
            'label': kpi_info_detail.name,
            'color': info.color,
            'value': formatted_value,
            'short_title': short_title,
            'comparison': comparison,
            'comparison_title': comparison_title,
            'period_type': info.period_type.upper(),
            'trend': trend,
            'icon': 'web/image?model={model}&field=icon_kpi&id={id}&unique='.format(model=info._name, id=info.id)
        }

        return kpi_data_render

    ########################################################
    # GENERAL FUNCTION
    ########################################################
    def get_group_in_period(self, group_id, report_id, date_from=None, date_to=None, lines_dict={}):
        """
        :param lines_dict:
        :param group_name: name of group show in the report
            Ex: Net Profit, Expenses
        :param report_name: name the report containing the group above
            Ex: Profit and Loss, Cash Flow
        :param date_from: the start point to summarize data for the group
        :param date_to: the end point to summarize data for the group
        :return:
        Workflow:
        User click on Company Insight to see personalized KPI views
        -> Load demo data of personalized KPI in JS code (loadDemo() method in kpi_header.js)
        -> kpi_header_render() in personalized KPI model -> kpi_render() in general KPI
        -> render content of kpi -> get_data_kpi_render
        -> query and group data with period in get_group_in_period
        """
        financial_report = self.env.ref(report_id)
        balance = 0

        if len(financial_report) == 1:
            cur_group = self.env.ref(group_id)
            if len(cur_group) > 1:
                result_group = []
                # loop each group when it return multiple group have same name
                for idx, group in enumerate(cur_group):
                    while group.parent_id:
                        group = group.parent_id
                    if group.financial_report_id and group.financial_report_id.id == financial_report.id:
                        result_group = cur_group[idx]
                cur_group = result_group

            if len(cur_group) == 1:
                options = {
                    "unfolded_lines": [],
                    "date": {
                        "period_type": "fiscalyear",
                        "mode": "range",
                        "strict_range": False,
                        "date_from": date_from,
                        "date_to": date_to,
                        "filter": "this_year",
                    },
                    "comparison": {
                        "filter": "no_comparison",
                        "number_period": 1,
                        "date_from": "",
                        "date_to": "",
                        "periods": [],
                    },
                    "all_entries": False,
                }
                options_list = financial_report._get_options_periods_list(options)
                formula_solver = FormulaSolver(options_list, financial_report)
                formula_solver.fetch_lines(cur_group)

                results = formula_solver.get_results(cur_group)['formula']
                balance = results.get((0,), 0.0)
        return balance

    def append_data_follow_range_time(self, dict_context, type_period, delta_periods=0, lines_dict={}, company_id=None):
        """ Function change data in the dict_context variable base on range time
        :param lines_dict:
        :param dict_context:
        :param type_period:
        :param delta_periods:
        :return:
        """
        if company_id:
            old_comp_id = self.env.company.id
            self.env.company = company_id
        from_date, to_date = get_start_end_date_value_with_delta(self, datetime.now(), type_period, delta_periods)

        # Change range time data
        dict_context['date_from'] = str(from_date.date())
        dict_context['date_to'] = str(to_date.date())

        # change lines_dict of dict_context
        dict_context['lines_dict'] = lines_dict.setdefault((dict_context['date_from'], dict_context['date_to']), {})

        if company_id:
            self.env.company = old_comp_id

    def format_number_type(self, value, unit_type):
        """ Function is the middle layer between layout and utils. It will receive value
        and unit_type, and then return a string is value have been formatted
        :param value:
        :param unit_type:
        :return:
        """
        formatted_value = short_title = ''
        if unit_type == CURRENCY:
            formatted_value = format_currency(self, value)
            short_title = get_short_currency_amount(value, self.env.company.currency_id)

        elif unit_type == PERCENTAGE:
            formatted_value = format_percentage(value)
            short_title = formatted_value

        return formatted_value, short_title
