# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Novobi: Partner Deposit US Accounting',
    'summary': 'Novobi: Partner Deposit US Accounting',
    'author': 'Novobi',
    'website': 'http://www.odoo-accounting.com',
    'category': 'Accounting',
    'version': '14.0',
    'license': 'OPL-1',
    'depends': [
        'account_partner_deposit',
        'l10n_us_accounting',
    ],

    'data': [
        # ============================== DATA =================================

        # ============================== SECURITY =============================

        # ============================== VIEWS ================================
        'views/account_payment_deposit_view.xml'

        # ============================== REPORT ===============================

        # ============================== WIZARDS ==============================

    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': False
}
