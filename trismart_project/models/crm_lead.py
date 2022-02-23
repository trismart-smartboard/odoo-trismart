import random

from odoo import api, fields, models, _


class LeadImage(models.Model):
    _name = 'crm.lead.image'
    # TODO: Finalize fields
    # image_name = fields.Image('Existing Property Damage')
    # title = fields.Char('Title')
    # ea_email = fields.Char('Energy Advisor')
    # ec_email = fields.Char('Energy Consultant')
    # originator_email = fields.Char('Originator')


class CrmLead(models.Model):
    _inherit = "crm.lead"

    sb_lead_id = fields.Integer('SmartBoard Lead Id')
    association_app_id = fields.Selection([
        ('1', 'Ignite'),
        ('2', 'Solo'),
        ('3', 'Enerflo'),
        ('4', 'Odoo'),
        ('5', 'Salesforce')
    ], string='Proposal Tool')
    lat = fields.Float('Latitude')
    lon = fields.Float('Longitude')
    created = fields.Datetime('Date Created')
    preferred_language = fields.Many2one('preferred.language', string='Preferred Language')
    disposition = fields.Many2one('disposition.type', string='Disposition')
    account = fields.Many2one('res.partner', string='Account')
    market = fields.Many2one('crm.market', string='Market')
    preferred_contact_type = fields.Many2one('contact.type', string='Preferred Contact Type')
    milestone = fields.Many2one('smartboard.project.milestone', string='SmartBoard Milestone')
