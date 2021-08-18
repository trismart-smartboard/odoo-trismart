# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Novobi US Stock Account',
    'summary': 'Novobi US Stock Account',
    'author': 'Novobi',
    'website': 'https://www.novobi.com/',
    'category': 'Accounting',
    'version': '14.0',
    'license': 'OPL-1',
    'depends': [
        'stock',
    ],

    'data': [
        # ============================== DATA ================================

        # ============================== MENU ================================

        # ============================== WIZARDS =============================

        # ============================== VIEWS ===============================
        'views/product_views.xml',
        'views/stock_location_views.xml',
        # ============================== SECURITY ============================

        # ============================== TEMPLATES ===========================

        # ============================== REPORT ==============================

    ],

    "application": False,
    "installable": True,
}
