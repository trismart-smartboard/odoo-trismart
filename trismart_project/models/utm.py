from odoo import models, fields, api


class UtmSource(models.Model):
    _inherit = 'utm.source'

    sb_id = fields.Integer(string='SmartBoard Id')
