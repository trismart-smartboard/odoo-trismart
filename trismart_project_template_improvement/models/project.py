from odoo import api, fields, models, tools

class Project(models.Model):
    _inherit = "project.project"

    default_template_id = fields.Integer(string='Smartboard Lead ID')
