from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    user_default_project_template = fields.Many2one(
        'project.project',
        string = 'Default Project Template',
        domain="[('is_template', '=', True)]",
        related="company_id.user_default_project_template",
        readonly = False,
        help='Project Template to use when create new project')

