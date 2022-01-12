from odoo import models, fields, api


class CrmMarket(models.Model):
    _name = 'crm.market'
    _description = 'Crm Market'

    name = fields.Char('Market Name')
