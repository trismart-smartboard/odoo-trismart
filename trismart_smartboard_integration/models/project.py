from odoo import api, fields, models, tools, SUPERUSER_ID

class Project(models.Model):
    _inherit = "project.project"

    sb_lead_id = fields.Char(string='Smartboard Lead ID', readonly=True)


