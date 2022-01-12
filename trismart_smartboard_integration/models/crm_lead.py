from odoo import api, fields, models, tools

class Lead(models.Model):
    _inherit = "crm.lead"

    sb_lead_id = fields.Char(string='Smartboard Lead ID', readonly=True)


