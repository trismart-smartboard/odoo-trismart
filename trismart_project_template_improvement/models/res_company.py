from odoo import api, fields, models

class Company(models.Model):
    _inherit = "res.company"

    user_default_project_template = fields.Many2one(
        'project.project',
        string='Default Project Template',
        domain="[('is_template', '=', True)]")

