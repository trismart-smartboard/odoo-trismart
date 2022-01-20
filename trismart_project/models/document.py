from odoo import models, fields, api, _


class Document(models.Model):
    _inherit = 'documents.document'
    # TODO: To be define
    # document_type = fields.Selection([
    #     ('proposal', 'Proposal'),
    #     ('max_layout', 'Max Layout'),
    #     ('monthly_production', 'Monthly Production'),
    #     ('aurora_shade_report', 'Aurora Shade Report'),
    #     ('max_aurora', 'Max Aurora'),
    #     ('installation_agreement', 'Installation Agreement'),
    #     ('installation_cash_agreement', 'Installation Cash Agreement'),
    # ], 'Document Type')
    # document_name = fields.Char('Proposal')
    # document_url = fields.Char('Max Layout')
    # created = fields.Char('Monthly Production')

