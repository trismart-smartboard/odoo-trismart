# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Novobi: Account Tax Settings',
    'summary': 'Novobi: Account Tax Settings',
    'author': 'Novobi',
    'website': 'http://www.odoo-accounting.com',
    'category': 'Accounting',
    'version': '14.0',
    'license': 'OPL-1',
    'depends': [
        'account',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/account_tax_views.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    "application": False,
    "installable": True,
}
