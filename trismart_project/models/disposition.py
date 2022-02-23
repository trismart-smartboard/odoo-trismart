from odoo import models, fields, api


class DispositionType(models.Model):
    _name = 'disposition.type'
    _description = 'Disposition Type'

    sb_id = fields.Integer('SmartBoard Id')
    name = fields.Char('Disposition Type')


class SmartBoardLanguage(models.Model):
    _name = 'preferred.language'
    _description = 'Preferred Language'

    sb_id = fields.Integer('SmartBoard Id')
    name = fields.Char('Preferred Language')


class SmartBoardContactType(models.Model):
    _name = 'contact.type'
    _description = 'Preferred Contact Type'

    sb_id = fields.Integer('SmartBoard Id')
    name = fields.Char('Preferred Contact Type')
