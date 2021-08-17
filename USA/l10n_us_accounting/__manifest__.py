# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Novobi US Accounting',
    'summary': 'Novobi US Accounting',
    'author': 'Novobi',
    'website': 'http://www.odoo-accounting.com',
    'category': 'Accounting',
    'version': '14.0',
    'license': 'OPL-1',
    'depends': [
        'account_accountant',
        'l10n_us_reports',
        'contacts',
        'account_batch_payment',
        'l10n_us_check_printing',
        'account_followup',
        'l10n_common',
    ],

    'data': [
        # ============================== DATA ================================
        'data/account_payment_method_data.xml',
        'data/data_account_type.xml',
        'data/account_financial_report_data.xml',
        'data/vendor_1099_report_data.xml',
        'data/usa_bank_reconciliation_data.xml',

        # ============================== MENU ================================

        # ============================== WIZARDS =============================
        'wizard/button_set_to_draft_message_view.xml',
        'wizard/account_invoice_refund_view.xml',
        'wizard/account_invoice_partial_payment_view.xml',
        'wizard/multiple_writeoff_view.xml',
        'wizard/account_bank_reconciliation_difference_view.xml',
        'wizard/account_record_ending_balance_view.xml',

        # ============================== VIEWS ===============================
        'views/assets.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_view.xml',
        'views/account_payment_line_view.xml',
        'views/account_payment_view.xml',
        'views/account_move_view.xml',
        'views/account_batch_payment_view.xml',
        'views/ir_qweb_widget_templates.xml',
        'views/followup_view.xml',
        'views/usa_1099_report.xml',
        'views/account_account_views.xml',
        'views/account_move_line_view.xml',
        'views/account_bank_statement_views.xml',
        'views/account_bank_reconciliation_data_view.xml',
        'views/usa_bank_reconciliation_views.xml',
        'views/account_journal_view.xml',
        'views/account_journal_dashboard_views.xml',
        'views/report_payment_receipt_templates.xml',

        # ============================== SECURITY ============================
        'security/ir.model.access.csv',

        # ============================== TEMPLATES ===========================

        # ============================== REPORT ==============================
        'report/print_check.xml',
        'report/account_followup_report_templates.xml',
        'report/account_batch_payment_report_templates.xml',
        'report/vendor_1099_report_template.xml',
        'report/account_bank_reconciliation_data_report.xml',

    ],

    'qweb': ['static/src/xml/*.xml'],
    "application": False,
    "installable": True,
}
