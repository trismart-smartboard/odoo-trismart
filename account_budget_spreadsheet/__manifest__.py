# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'USA: Budget Spreadsheet',
    'summary': 'USA: Budget Spreadsheet',
    'category': 'Accounting',
    'author': "Novobi",
    'website': 'http://www.odoo-accounting.com',
    'version': '14.0',
    'license': 'OPL-1',
    'depends': [
        'documents',
        'documents_spreadsheet',
        'documents_spreadsheet_account',
        'account_budget',
        'account_reports',
    ],
    'data': [
        # ============================== DATA =============================
        'data/budget_spreadsheet_data.xml',
        # ============================== VIEWS =============================
        'views/assets.xml',
        'views/documents_views.xml',
        'views/account_financial_report_view.xml',
        # ============================== WIZARD =============================
        'wizard/account_budget_wizard_view.xml'
    ],
    "application": False,
    'qweb': ['static/src/xml/*.xml'],
    "installable": True,
}
