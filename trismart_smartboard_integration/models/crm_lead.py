from odoo import api, fields, models, tools, SUPERUSER_ID

class Lead(models.Model):
    _inherit = "crm.lead"

    sb_lead_id = fields.Char(string='Temp Smartboard Lead ID', readonly=True)


