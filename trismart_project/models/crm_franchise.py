from odoo import models, fields, api


class CrmFranchise(models.Model):
    _name = 'crm.franchise'
    _description = 'Crm Franchise'

    name = fields.Char('Franchise Name')
