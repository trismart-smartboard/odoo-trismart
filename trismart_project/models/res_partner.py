from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sb_id = fields.Integer('SmartBoard Id')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    subdivision = fields.Char('Subdivision')
    is_franchise = fields.Boolean('Is SmartBoard Franchise?')
