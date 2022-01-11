from odoo import models, fields, api, _


class AssociationApp(models.Model):
    _name = 'association.app'
    _description = 'Association App'

    name = fields.Char(string='Name')
