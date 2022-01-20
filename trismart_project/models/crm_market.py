from odoo import models, fields, api


class CrmMarket(models.Model):
    _name = 'crm.market'
    _description = 'Crm Market'

    sb_id = fields.Integer('SmartBoard Id')
    name = fields.Char('Market Name')
