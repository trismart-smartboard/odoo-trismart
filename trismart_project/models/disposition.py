from odoo import models, fields, api


class DispositionType(models.Model):
    _name = 'disposition.type'
    _description = 'Disposition Type'

    sb_id = fields.Integer('SmartBoard Id')
    name = fields.Char('Disposition Type')
