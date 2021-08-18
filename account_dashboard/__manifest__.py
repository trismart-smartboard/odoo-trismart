# -*- coding: utf-8 -*-
{
    'name': 'Novobi: Account Dashboard',
    'summary': 'Novobi: Account Dashboard',
    'author': 'Novobi',
    'website': 'http://www.odoo-accounting.com',
    'category': 'Accounting',
    'version': '14.0',
    'license': 'OPL-1',
    'depends': [
        'l10n_us_accounting',
        'l10n_custom_dashboard'
    ],
    'data': [
        # ============================== SECURITY =============================
        'security/ir.model.access.csv',
        'security/personalized_kpi_info_security.xml',
        'security/account_dashboard_security.xml',
        # ============================== DATA =============================
        'data/kpi_journal_data.xml',
        'data/usa_journal_data.xml',
        # ============================== VIEW =============================
        'views/assets.xml',
        'views/account_dashboard_views.xml',
        'views/kpi_dashboard_views.xml',
        'views/personalized_kpi_info_views.xml',
        'views/inherited_account_journal_dashboard_views.xml'

    ],
    'demo': [
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': False,
}
