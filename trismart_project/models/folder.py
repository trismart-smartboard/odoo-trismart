from odoo import models, fields, api, _


class DocumentFolder(models.Model):
    _inherit = 'documents.folder'

    sb_id = fields.Integer('SmartBoard Id')
