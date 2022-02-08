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

    sb_lead_id = fields.Integer('Associated App Id')
    association_app_id = fields.Selection([
        ('1', 'Ignite'),
        ('2', 'Solo'),
        ('3', 'Enerflo'),
        ('4', 'Odoo'),
        ('5', 'Salesforce')
    ], string='Proposal Tool')
    lat = fields.Float('Latitude')
    long = fields.Float('Longitude')
    created = fields.Date('Date Created')
    preferred_language_id = fields.Selection([
        ('1', 'English'),
        ('2', 'Spanish')
    ])
    disposition_id = fields.Many2one('disposition.type', string='Disposition')
    account_id = fields.Many2one('res.partner', string='Account')
    market_id = fields.Many2one('crm.market', string='Market')
    preferred_contact_type_id = fields.Selection([
        ('1', 'Primary Phone'),
        ('2', 'Secondary Phone'),
        ('3', 'SMS'),
        ('4', 'Email')
    ])
    milestone_id = fields.Many2one('project.milestone', string='Milestone')
