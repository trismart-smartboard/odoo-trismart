# -*- coding: utf-8 -*-

from ..utils.template_generator import generate_spreadsheet_template
from odoo import fields, models, api, _
from datetime import datetime
import base64
import json

REPORT = {
    'profit_and_loss': 'account_reports.account_financial_report_profitandloss0',
    'balance': 'account_reports.account_financial_report_balancesheet0'
}


class Document(models.Model):
    _inherit = 'documents.document'

    report_type = fields.Selection([('profit_and_loss', 'Profit and Loss'), ('balance', 'Balance Sheet')],
                                   default='profit_and_loss')
    period_type = fields.Selection([('quarter', 'Quarterly'), ('month', 'Monthly')], default='month')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    create_budget_from_last_year = fields.Boolean('Create budget from same period last year\'s actual data')
    _this_year = datetime.today().year
    _year_range = [(str(x), str(x)) for x in range(_this_year - 2, _this_year + 4)]
    year = fields.Selection(_year_range, string="Year", default=str(_this_year + 1))
    is_budget_spreadsheet = fields.Boolean('Is Budget Spreadsheet document?', default=False)

    @api.model
    def create(self, vals):
        if "folder_id" not in vals:
            default_folder = self.env.ref('documents_spreadsheet.documents_spreadsheet_folder',
                                          raise_if_not_found=False)
            vals["folder_id"] = default_folder.id
        return super(Document, self).create(vals)

    ############
    # General Function
    ############
    def is_lowest_level(self, node):
        """
        Define whether node is at lowest level or not
        Lowest level node (leaf): has domain in record and is calculated by querying with domain.
        High level node: calculated by same or lower level node. High level nodes usually have children_ids except for
        Net Profit.
        :return:
        """
        return node.domain

    def depth_first_traverse(self, graph, node, visited):
        """
        Depth First Search Function
        :param graph:
        :param node:
        :param visited:
        :return:

        Workflow:
        User want to generate spreadsheet from report
        -> Get all the lines of report with build_line_hierarchy
        -> Depth First Traverse to get the hierarchy of report.
        """
        if node not in visited:
            if node.hide_in_budget:
                return
            if self.is_lowest_level(node):
                domain = eval(node.domain)
            else:
                domain = [node.formulas.replace(' ', '')]
            item = {
                'name': node.name,
                'domain': domain,
                'code': node.code,
                'sign': 1 if node.formulas == '-sum' else (-1 if node.formulas == 'sum' else 1),
                'is_lowest': self.is_lowest_level(node),
                'green_on_positive': node.green_on_positive
            }
            visited.append(item)
            for id in list(node.children_ids):
                self.depth_first_traverse(graph, id, visited)
        return visited

    def build_line_hierarchy(self, report_type):
        """
        :param report_type: Profit and Loss/ Balance sheet
        :return:
        loss_profit = [
        {'name': 'Income', 'code': 'INC', 'level': 0, 'formula': ['OPINC+OIN'], 'green_on_positive': 1,
         'children': [
             {'name': 'Gross Profit', 'code': 'GRP', 'level': 2, 'formula': ['OPINC-COS'], 'green_on_positive': 1,
              'children': [{'name': 'Operating Income', 'code': 'OPINC', 'level': 3, 'green_on_positive': 1,
                            'domain': [('account_id.user_type_id', '=', 13)], 'children': []},
                           {'name': 'Cost of Revenue', 'code': 'COS', 'level': 3, 'green_on_positive': -1,
                            'domain': [('account_id.user_type_id', '=', 17)], 'children': []}
                           ]},
             {'name': 'Other Income', 'code': 'OIN', 'level': 2, 'green_on_positive': 1,
                 'children': [], 'domain': [('account_id.user_type_id', '=', 14)]},
         ]},
        {'name': 'Expenses', 'code': 'LEX', 'level': 0, 'formula': ['EXP+DEP'], 'green_on_positive': -1,
         'children': [{'name': 'Expense', 'code': 'EXP', 'level': 2, 'green_on_positive': -1,
                       'domain': [('account_id.user_type_id', '=', 15)], 'children': []},
                      {'name': 'Depreciation', 'code': 'DEP', 'level': 2, 'green_on_positive': -1,
                       'domain': [('account_id.user_type_id', '=', 16)], 'children': []}]},
        {'name': 'Net Profit', 'code': 'NEP', 'level': 0, 'formula': ['OPINC+OIN-COS-EXP-DEP'],
         'children': []},
        ]
        Workflow:
        User want to generate spreadsheet from report
        -> Get all the lines of report with build_line_hierarchy function
        """

        report = self.env.ref(REPORT[report_type])
        list_lines = report.mapped('line_ids')
        demo = list(list_lines)
        # Loop in the queue of report line saved in demo variable
        lines_dict = []
        for node in demo:
            self.depth_first_traverse(demo, node, lines_dict)

        return lines_dict

    def create_spreadsheet_from_report(self, period_type, report_type, spreadsheet_name, year, analytic_account,
                                       create_budget_from_last_year):
        """
        :param period_type: quarter/monthly
        :param report_type:profit_loss/balance
        :param spreadsheet_name:
        :param year:
        :param analytic_account:
        :return
        Workflow:
        User want to create spreadsheet from menu accounting/create budget spreadsheet report
        -> Trigger event in JS code in button "Create New Spreadsheet"
        -> JS gets the info including: period_type, report_type, analytic_account to generate spreadsheet
        with python fucntion (this function)
        -> JS uses the return data to create new Documents.document record
        """

        lines_dict = self.build_line_hierarchy(report_type)
        analytic_account_id = self.env['account.analytic.account'].browse(analytic_account)
        currency = self.env.company.currency_id.display_name
        num_of_rows_per_line = int(
            self.env["ir.config_parameter"].sudo().get_param("account_budget_spreadsheet.no_of_lines"))
        data = generate_spreadsheet_template(report_type, period_type, spreadsheet_name, lines_dict, year,
                                             analytic_account_id,
                                             create_budget_from_last_year, currency=currency,
                                             num_of_rows_per_line=num_of_rows_per_line)
        data_json = json.dumps(data).encode('utf-8')
        spreadsheet = self.env['spreadsheet.template'].create({
            'name': spreadsheet_name,
            'data': base64.encodebytes(data_json)
        })
        default_folder = self.env.ref('documents_spreadsheet.documents_spreadsheet_folder', raise_if_not_found=False)

        data = {"spreadsheet_id": spreadsheet.id, "spreadsheet_name": spreadsheet_name,
                "folder_id": default_folder.id,
                "analytic_account_id": analytic_account_id.id
                }
        return data
