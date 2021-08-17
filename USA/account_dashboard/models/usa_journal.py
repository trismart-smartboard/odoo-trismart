import json
import re
import ast
from odoo import api, fields, models, _
from odoo.osv import expression
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from ...l10n_custom_dashboard.utils.graph_setting import get_chartjs_setting, get_barchart_format, get_info_data, \
    get_chart_json, get_linechart_format
from ..utils.graph_utils import get_json_render, get_json_data_for_selection, get_data_for_graph, \
    append_data_fetch_to_list
from ..utils.time_utils import get_list_period_by_type, get_start_end_date_value, BY_DAY, BY_WEEK, BY_MONTH, BY_QUARTER, \
    BY_FISCAL_YEAR
from ..utils.utils import get_list_companies_child

PRIMARY_GREEN = "#00A09D"
PRIMARY_PURPLE = "#875a7b"
PRIMARY_ORANGE = "#f19848"
PRIMARY_BLUE = "#649ce7"

COLOR_INCOME = PRIMARY_GREEN
COLOR_EXPENSE = PRIMARY_ORANGE
COLOR_VALIDATION_DATA = "#337ab7"
COLOR_BANK = PRIMARY_GREEN
COLOR_BOOK = PRIMARY_ORANGE
COLOR_OPEN_INVOICES = PRIMARY_ORANGE
COLOR_PAID_INVOICE = PRIMARY_GREEN
COLOR_OPEN_BILLS = PRIMARY_PURPLE
COLOR_PAID_BILLS = PRIMARY_BLUE
COLOR_SALE_PAST = PRIMARY_PURPLE
COLOR_SALE_FUTURE = PRIMARY_GREEN
COLOR_CASH_OUT = PRIMARY_ORANGE
COLOR_CASH_IN = PRIMARY_GREEN
COLOR_NET_CASH = PRIMARY_BLUE
COLOR_PROJECTED_CASH_IN = PRIMARY_GREEN
COLOR_PROJECTED_CASH_OUT = PRIMARY_ORANGE
COLOR_PROJECTED_BALANCE = PRIMARY_BLUE

PROFIT_LOSS = 'profit_and_loss'
INVOICE = 'invoice'
CASH = 'cash'
CASH_FORECAST = 'cash_forecast'
BANK = 'bank'
CUSTOMER_INVOICE = 'sale'
VENDOR_BILLS = 'purchase'

GRAPH_CONFIG = {
    PROFIT_LOSS: {'type': 'bar', 'function': 'retrieve_profit_and_loss', 'periods': 'period_by_month',
                  'action': {'action_name': "account_reports.account_financial_html_report_action_1"}},
    INVOICE: {'type': 'line', 'function': 'retrieve_untaxed_total_amount_invoice', 'periods': 'period_by_complex',
              'action': {'action_name': 'account.action_move_out_invoice_type',
                         'domain': [('move_type', '=', 'out_invoice')],
                         'context': {'search_default_posted': 1}}},
    CASH: {'type': 'bar', 'function': 'retrieve_cash', 'periods': 'period_by_complex',
           'action': {'action_name': 'account_reports.action_account_report_cs'}},
    CASH_FORECAST: {'type': 'bar', 'function': 'retrieve_cash_forecast', 'periods': 'period_by_month',
                    'action': None}
}


class USAJournal(models.Model):
    _name = "usa.journal"
    _description = "US Accounting journal"

    period_by_month = [{'name': 'This Month', 'delta': 0, 'time': BY_MONTH},
                       {'name': 'This Quarter', 'delta': 0, 'time': BY_QUARTER},
                       {'name': 'This Fiscal Year', 'delta': 0, 'time': BY_FISCAL_YEAR},
                       {'name': 'Last Month', 'delta': -1, 'time': BY_MONTH},
                       {'name': 'Last Quarter', 'delta': -1, 'time': BY_QUARTER},
                       {'name': 'Last Fiscal Year', 'delta': -1, 'time': BY_FISCAL_YEAR}, ]
    default_period_by_month = 'This Fiscal Year'
    period_by_complex = [{'name': 'This Week by Day', 'delta': 0, 'date_separate': BY_DAY, 'time': BY_WEEK},
                         {'name': 'This Month by Week', 'delta': 0, 'date_separate': BY_WEEK, 'time': BY_MONTH},
                         {'name': 'This Quarter by Month', 'delta': 0, 'date_separate': BY_MONTH, 'time': BY_QUARTER},
                         {'name': 'This Fiscal Year by Month', 'delta': 0, 'date_separate': BY_MONTH,
                          'time': BY_FISCAL_YEAR},
                         {'name': 'This Fiscal Year by Quarter', 'delta': 0, 'date_separate': BY_QUARTER,
                          'time': BY_FISCAL_YEAR},
                         {'name': 'Last Week by Day', 'delta': -1, 'date_separate': BY_DAY, 'time': BY_WEEK},
                         {'name': 'Last Month by Week', 'delta': -1, 'date_separate': BY_WEEK, 'time': BY_MONTH},
                         {'name': 'Last Quarter by Month', 'delta': -1, 'date_separate': BY_MONTH, 'time': BY_QUARTER},
                         {'name': 'Last Fiscal Year by Month', 'delta': -1, 'date_separate': BY_MONTH,
                          'time': BY_FISCAL_YEAR},
                         {'name': 'Last Fiscal Year by Quarter', 'delta': -1, 'date_separate': BY_QUARTER,
                          'time': BY_FISCAL_YEAR}, ]
    default_period_by_complex = 'This Fiscal Year by Month'
    type_element = [
        (PROFIT_LOSS, _('Profit and Loss')),
        (INVOICE, _('Invoice')),
        (CASH, _('Cash')),
        (CASH_FORECAST, _('Cashflow Forecast'))
    ]
    code = fields.Char(string='Code', required=True)
    type = fields.Selection(type_element, required=True)
    name = fields.Char('Element Name', required=True)
    account_dashboard_graph_json = fields.Text(compute='compute_account_dashboard_graph')
    extend_data = fields.Boolean(compute='compute_account_dashboard_graph', default=False, store=True)
    color = fields.Integer("Color Index", default=0)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True,
                                 default=lambda self: self.env.company, help="Company related to this journal")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    recurring_cashin = fields.Monetary('Recurring Cash in', default=0)
    recurring_cashout = fields.Monetary('Recurring Cash out', default=0)

    def compute_account_dashboard_graph(self):
        for record in self:
            extend_mode = None
            selection = []
            extra_param = []

            _, graph_data = record.get_general_kanban_section_data()
            if record.type != CASH_FORECAST:
                period_type = GRAPH_CONFIG[record.type]['periods']
                default_period_type = 'default_' + period_type
                get_json_data_for_selection(record, selection, getattr(record, period_type),
                                            getattr(record, default_period_type))

            if graph_data:
                graph_type = GRAPH_CONFIG[record.type].get('type', '')
                function_retrieve = GRAPH_CONFIG[record.type].get('function', '')
                record.account_dashboard_graph_json = json.dumps(
                    get_json_render(graph_type, False, '', graph_data, record.type, selection, function_retrieve,
                                    extra_param))
                record.extend_data = extend_mode

    ########################################################
    # BUTTON EVENT
    ########################################################
    def open_action_label(self):
        # TODO: fix action and complete_empty_list_help
        """ Function return action based on type for related journals

        :return:
        """
        self.ensure_one()
        action_name = self._context.get('action_name', False)
        if not action_name:
            action_name = GRAPH_CONFIG[self.type]['action']['action_name']
            domain = GRAPH_CONFIG[self.type]['action'].get('domain', "")
            context = GRAPH_CONFIG[self.type]['action'].get('context', {})

        [action] = self.env.ref(action_name).read()
        action['domain'] = domain
        action['context'] = context

        return action

    def action_recurring_amount(self):
        self.ensure_one()
        action = self.env.ref('account_dashboard.usa_journal_recurring_payment_view_action').read()[0]
        action['res_id'] = self.id
        return action

    ########################################################
    # INITIAL DATA
    ########################################################
    @api.model
    def init_data_usa_journal(self):
        usa_journal = self.env['usa.journal']
        types = [item[0] for item in self.type_element]
        dict_elem = dict(self.type_element)
        for journal_type in types:
            if journal_type != BANK:
                for com in self.env['res.company'].search([]):
                    usa_journal.create({
                        'type': journal_type,
                        'name': dict_elem[journal_type],
                        'code': journal_type.upper(),
                        'company_id': com.id
                    })

    ########################################################
    # GENERAL FUNCTION
    ########################################################
    def get_general_kanban_section_data(self):
        data = []
        (graph_title, graph_key) = ('', '')
        extend_data = False
        return extend_data, [{
            'values': data,
            'title': graph_title,
            'key': graph_key,
            'color': COLOR_VALIDATION_DATA}]

    ########################################################
    # API
    ########################################################
    def retrieve_income_expense_code_group(self, demo):
        """
        :param demo:
        :return:
        Workflow:
        Company Insight
        -> Render Profit Loss bar chart in View
        -> Retrieve data in python code from Profit Loss report
        -> Filter Code of Income and Expense from Profit and Loss Report (This function)
        Income = ['OINC',..]
        Expense = ['EXP','DEP',..]
        """
        code_group_income = []
        code_group_expenses = []
        while len(demo):
            line = demo.pop(0)
            demo += list(line.children_ids)
            if line.domain and line.green_on_positive:
                code_group_income.append(line.code)
            if line.domain and not line.green_on_positive:
                code_group_expenses.append(line.code)

        return code_group_income, code_group_expenses

    @api.model
    def retrieve_profit_and_loss(self, date_from, date_to, period_type=BY_MONTH):
        """
        :param date_from:
        :param date_to:
        :param period_type:
        :return:
         Workflow:
        Company Insight
        -> Render Profit Loss bar chart in View
        -> Retrieve data in python code from Profit Loss report (This function)
        -> Import data to ChartJS to render graph
        """
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        # Profit and loss record in account reports
        profit_loss_rp = self.env.ref('account_reports.account_financial_report_profitandloss0')
        list_lines = profit_loss_rp.mapped('line_ids')
        demo = list(list_lines)
        code_group_income, code_group_expenses = self.retrieve_income_expense_code_group(demo)

        # Query data based on code group income
        env = self.env['account.financial.html.report.line']
        domain_group_expenses = env.search([('code', 'in', code_group_expenses)]).mapped(
            lambda g: ast.literal_eval(g.domain))
        domain_group_income = env.search([('code', 'in', code_group_income)]).mapped(
            lambda g: ast.literal_eval(g.domain))
        expenses_domain = expression.OR(domain_group_expenses)
        income_domain = expression.OR(domain_group_income)
        tables, query_expenses_clause, where_params = self.env["account.move.line"]._query_get(
            domain=expenses_domain)

        sql_params = [period_type, date_from, date_to]
        sql_params.extend(where_params)

        income_group_data = self.env['account.move.line'].summarize_group_account(date_from, date_to, period_type,
                                                                                  income_domain)
        expense_group_data = self.env['account.move.line'].summarize_group_account(date_from, date_to, period_type,
                                                                                   expenses_domain)
        total_income, income_values, labels = get_data_for_graph(self, date_from, date_to, period_type,
                                                                 income_group_data, ['total_balance'], pos=-1)
        total_expense, expense_values, labels = get_data_for_graph(self, date_from, date_to, period_type,
                                                                   expense_group_data, ['total_balance'])

        # Data for chart js
        graph_data = [
            get_barchart_format(self,income_values[0], _('Income'), COLOR_INCOME),
            get_barchart_format(self,expense_values[0], _('Expenses'), COLOR_EXPENSE),
        ]

        info_data = [
            get_info_data(self, _('Income'), total_income[0]),
            get_info_data(self, _('Expenses'), total_expense[0]),
            get_info_data(self, _('Net Income'), total_income[0] - total_expense[0]),
        ]
        chart_json = get_chart_json(self, graph_data, labels, get_chartjs_setting(chart_type='bar'), info_data)
        return chart_json

    def prepare_data_for_graph(self, dimension, data_fetch, periods, period_type, chart_name, info_data=0):
        """
        :param dimension: Dimension of data to render in chart depends on number of lines(bars) displaying in chart
        :param data_fetch: data dictionary query from SQL query
        :param periods:
        :param period_type: this month by week, this week by day, this financial year by quarter,...
        :param chart_name: Invoice, Cash,..
        :param fill_data: If chart needs to be filled with 0 zero, fill_data will be used with that purpose
        :param info_data: data text displayed on chart
        :return: data_list, graph_label, info_data
        Workflow:
        Company Insight
        -> Render Invoice bar chart in View
        -> Retrieve data in python code from database
        -> Prepare data (data + label) for rendering in chartJS (This function)
        """
        data_list = [[] for _ in range(dimension)]
        graph_label = []
        index = 0
        today = date.today()
        for data in data_fetch:
            while index < len(periods) and not (periods[index][0] <= data['date_in_period'] <= periods[index][1]):
                append_data_fetch_to_list(data_list, graph_label, periods, period_type, index)
                index += 1
            if index < len(periods):
                values = None
                if chart_name == INVOICE:
                    value = data.get('amount_untaxed', False)
                    values = [
                        value if not isinstance(value, bool) and periods[index][0] <= today else 'NaN',
                        value if not isinstance(value, bool) and periods[index][1] >= today else 'NaN'
                    ]
                    info_data += value if value else 0
                elif chart_name == CASH:
                    values = [data['total_debit'], -data['total_credit'], data['total_debit'] - data['total_credit']]
                append_data_fetch_to_list(data_list, graph_label, periods, period_type, index, values=values)
                index += 1

        # Fill values into periods, fill null with 0 if existed
        while index < len(periods):
            fill_data = None
            if chart_name == INVOICE:
                fill_data = [
                    0 if periods[index][0] <= today else 'NaN',
                    0 if periods[index][1] >= today else 'NaN'
                ]
            append_data_fetch_to_list(data_list, graph_label, periods, period_type, index, values=fill_data)
            index += 1
        return data_list, graph_label, info_data

    @api.model
    def retrieve_untaxed_total_amount_invoice(self, date_from, date_to, period_type):
        """ API is used to response untaxed amount of all invoices in system that get
        from account_invoice.
        :param date_from: the start date to summarize data, have type is datetime
        :param date_to: the end date to summarize data, that have type is datetime
        :param period_type: is type of period to summarize data, we have 4 selections are
                ['week', 'month', 'quarter', 'year']
        :return: Json
        Workflow:
        Company Insight
        -> Render Invoice bar chart in View
        -> Retrieve data in python code from posted Invoice data (This function)
        -> Import data to ChartJS to render graph
        """
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        periods = get_list_period_by_type(self, date_from, date_to, period_type)

        currency = """
                SELECT c.id, COALESCE((
                    SELECT r.rate
                    FROM res_currency_rate r
                    WHERE r.currency_id = c.id AND r.name <= %s AND (r.company_id IS NULL OR r.company_id IN %s)
                    ORDER BY r.company_id, r.name DESC
                    LIMIT 1), 1.0) AS rate
                FROM res_currency c
            """

        transferred_currency = """
                SELECT ai.invoice_date, ai.move_type, ai.amount_untaxed/(CASE COALESCE(c.rate, 0) WHEN 0 THEN 1.0 ELSE c.rate END) AS amount_tran, state, company_id
                FROM account_move AS ai
                    LEFT JOIN ({currency_table}) AS c ON ai.currency_id = c.id
            """.format(currency_table=currency)

        query = """
                SELECT date_part('year', aic.invoice_date::DATE) AS year,
                    date_part(%s, aic.invoice_date::DATE) AS period,
                    MIN(aic.invoice_date) AS date_in_period,
                    SUM(aic.amount_tran) AS amount_untaxed
                FROM ({transferred_currency_table}) AS aic
                WHERE invoice_date >= %s AND
                    invoice_date <= %s AND
                    aic.state = 'posted' AND
                    aic.move_type = 'out_invoice' AND
                    aic.company_id IN %s
                GROUP BY year, period
                ORDER BY year, date_in_period;
            """.format(transferred_currency_table=transferred_currency)

        company_ids = get_list_companies_child(self.env.company)
        name = fields.Date.today()
        self.env.cr.execute(query, (period_type, name, tuple(company_ids), date_from, date_to, tuple(company_ids),))
        data_fetch = self.env.cr.dictfetchall()
        # Prepare data for drawing graph with chartJS
        data_list, graph_label, total_sales = self.prepare_data_for_graph(dimension=2, data_fetch=data_fetch,
                                                                          periods=periods,
                                                                          period_type=period_type,
                                                                          chart_name=INVOICE)
        graph_data = [
            get_linechart_format(self,data=data_list[0], label=_('Sales'), color=COLOR_SALE_PAST),
            get_linechart_format(self,data=data_list[1], label=_('Future'), color=COLOR_SALE_FUTURE),
        ]

        info_data = [get_info_data(self, _('Total Untaxed Amount'), total_sales)]

        return get_chart_json(self, graph_data, graph_label, get_chartjs_setting(chart_type='line'), info_data)

    @api.model
    def retrieve_cash(self, date_from, date_to, period_type):
        """ API is used to response total amount of cash in/out base on
        account move in system. That is the account move of account have
        name is 'Bank and Cash' in the system beside that, also return
        any info relate to show in "Cash" kanban section.

        :param date_from: the start date to summarize data, have type is datetime
        :param date_to: the end date to summarize data, that have type is datetime
        :param period_type: is type of period to summarize data, we have 4 selections are
                ['week', 'month', 'quarter', 'year']
        :return: Json
        Workflow:
        Company Insight
        -> Render Cash bar and line chart in View
        -> Retrieve data in python code from Journal Entry data (This function)
        + Cash In = alue in Debit column (get from Journal Items with account type
        is Bank & Cash, NOT include Credit Card )
        + Cash out: value in Credit column (show negative)
        + Net cash: Cash in + Cash out
        -> Import data to ChartJS to render graph
        """
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        periods = get_list_period_by_type(self, date_from, date_to, period_type)
        type_account_id = self.env.ref('account.data_account_type_liquidity').id
        query = """
                SELECT date_part('year', aml.date::DATE) AS year,
                    date_part(%s, aml.date::DATE) AS period,
                    MIN(aml.date) AS date_in_period,
                    SUM(aml.debit) AS total_debit,
                    SUM(aml.credit) AS total_credit
                FROM account_move_line AS aml
                    INNER JOIN account_move AS am ON aml.move_id = am.id
                    INNER JOIN account_account AS aa ON aml.account_id = aa.id
                    INNER JOIN account_account_type AS aat ON aa.user_type_id = aat.id
                WHERE aml.date >= %s AND 
                    aml.date <= %s AND
                    am.state = 'posted' AND
                    aat.id = %s AND 
                    aml.company_id IN %s
                GROUP BY year, period
                ORDER BY year, date_in_period;
            """
        company_ids = get_list_companies_child(self.env.company)
        self.env.cr.execute(query, (period_type, date_from, date_to, type_account_id, tuple(company_ids),))
        data_fetch = self.env.cr.dictfetchall()

        # Prepare data for drawing graph with chartJS
        data_list, graph_label, total_sales = self.prepare_data_for_graph(dimension=3, data_fetch=data_fetch,
                                                                          periods=periods,
                                                                          period_type=period_type,
                                                                          chart_name=CASH)
        # Create chart data
        # Line chart must be on top of bar chart, so put it first and reverse the order of chart's legend
        graph_data = [
            get_linechart_format(self,data_list[2], _('Net cash'), COLOR_NET_CASH),
            get_barchart_format(self,data_list[1], _('Cash out'), COLOR_CASH_OUT, order=1),
            get_barchart_format(self,data_list[0], _('Cash in'), COLOR_CASH_IN, order=2),
        ]

        # Create info to show in head of chart
        info_data = [
            get_info_data(self, _('Cash in'), sum(data_list[0])),
            get_info_data(self, _('Cash out'), sum(data_list[1])),
            get_info_data(self, _('Net cash'), sum(data_list[0] + data_list[1])),
        ]

        return get_chart_json(self, graph_data, graph_label,
                              get_chartjs_setting(chart_type='bar', mode='index', stacked=True, reverse=True),
                              info_data)

    @api.model
    def retrieve_cash_forecast(self, date_from, date_to, period_type):
        """
        This function is fully implemented in Cash flow Projection Module
        Workflow:
        Company Insight
        -> Render Cash flow bar and line chart in View
        -> Retrieve data in python code from journal entry data (This function)
        -> Import data to ChartJS to render graph
        """

        data_list = [[0], [0], [0]]
        graph_label = [0]

        graph_data = [
            get_linechart_format(self,data_list[2], _('Balance'), COLOR_PROJECTED_BALANCE, order=2),
            get_barchart_format(self,data_list[1], _('Projected Cash out'), COLOR_PROJECTED_CASH_OUT),
            get_barchart_format(self,data_list[0], _('Projected Cash in'), COLOR_PROJECTED_CASH_IN, order=1),
        ]

        info_data = [
            get_info_data(self, _('Projected Cash in'), sum(data_list[0])),
            get_info_data(self, _('Projected Cash out'), sum(data_list[1])),
            get_info_data(self, _('Balance'), sum(data_list[0] + data_list[1])),
        ]

        return get_chart_json(self, graph_data, graph_label,
                              get_chartjs_setting(chart_type='bar', mode='index', stacked=True, reverse=True),
                              info_data)
