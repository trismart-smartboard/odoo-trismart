from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    subdivision = fields.Char('Subdivision')
