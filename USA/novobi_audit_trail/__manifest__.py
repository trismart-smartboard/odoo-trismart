{
    'name': 'Novobi: Audit Trail',
    'summary': 'Novobi: Audit Trail',
    'author': 'Novobi',
    'website': 'http://www.odoo-accounting.com',
    'category': 'Accounting',
    'version': '14.0',
    'license': 'OPL-1',
    'depends': [
        'base',
        'sale',
        'l10n_us_accounting',
    ],
    'data': [
        # ============================== SECURITY ================================
        'security/ir.model.access.csv',
        # ============================== DATA ================================
        'data/audit_trail_log_sequence.xml',
        'data/default_audit_rules.xml',
        # ============================== VIEW ================================
        'views/audit_trail_rule_views.xml',
        'views/audit_trail_log_views.xml',
    ],
    'application': False,
    'installable': True,
}
