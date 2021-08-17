# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Novobi: Billable Expense - assigned to customer from Vendor Bill',
    'summary': 'Novobi: Billable Expense - assigned to customer from Vendor Bill',
    'author': 'Novobi',
    'website': 'http://www.odoo-accounting.com',
    'category': 'Accounting',
    'version': '14.0',
    'license': 'OPL-1',
    'depends': [
        'l10n_generic_coa',
        'account_reports',
        'l10n_common',
    ],
    'data': [
        # ============================== SECURITY =============================
        'security/ir.model.access.csv',
        # ============================== DATA =============================
        'data/mail_data.xml',
        'data/billable_expense_report_data.xml',
        # ============================== VIEWS =============================
        'views/assets.xml',
        'views/account_move_view.xml',
        'views/billable_expense_view.xml',
        'views/billable_expense_report.xml',

    ],
    'images': ['static/description/main_screenshot.png'],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': False
}
