import random

from odoo import api, fields, models, _


class LeadImage(models.Model):
    _name = 'crm.lead.image'

    image_name = fields.Image('Existing Property Damage')
    title = fields.Char('Title')
    ea_email = fields.Char('Energy Advisor')
    ec_email = fields.Char('Energy Consultant')
    originator_email = fields.Char('Originator')


class CrmLead(models.Model):
    _inherit = "crm.lead"

    association_app_id = fields.Many2one('association.app', string='Proposal Tool')
    lat = fields.Float('Latitude')
    long = fields.Float('Longitude')
    created = fields.Date('Date Created')
    preferred_language_id = fields.Many2one('res.lang', 'Preferred Language')
    disposition_date = fields.Date('Disposition Date')
