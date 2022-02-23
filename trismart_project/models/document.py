from odoo import models, fields, api, _


class Document(models.Model):
    _inherit = 'documents.document'

    created = fields.Datetime('Created')
    user_email = fields.Char('Email To')

