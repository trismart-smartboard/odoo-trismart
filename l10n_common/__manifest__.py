# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Novobi: Common Module for Accounting',
    'summary': 'Novobi: Common Module for Accounting',
    'author': 'Novobi',
    'website': 'http://www.odoo-accounting.com',
    'category': 'Web',
    'version': '14.0',
    'license': 'OPL-1',
    'depends': [
        'web',
        'base',
    ],

    'data': [
        'views/assets.xml',
    ],

    'qweb': ['static/src/xml/*.xml'],
    "application": False,
    "installable": True,
}
